#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_cleaner_pipeline.py
========================
Full data-cleaning pipeline.

Steps:
  1. Load source file
  2. Dedup (full-row + business-key)
  3. Format standardisation
  4. Missing-value imputation
  5. Anomaly detection & correction (3-sigma + IQR + business bounds)
  6. Schema compliance validation
  7. Output cleaned table + change log + anomaly log

Outputs (audit/):
  dedup_mapping.csv
  change_log.csv
  anomaly_correction_log.csv
  blocking_issues.txt
  cleaned_output.xlsx

Usage:
  python audit/data_cleaner_pipeline.py
  python audit/data_cleaner_pipeline.py --input data/processed/cleaned_health_data.xlsx
"""

import sys
import csv
import uuid
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR  = Path(__file__).resolve().parent.parent
AUDIT_DIR = BASE_DIR / "audit"
DATA_DIR  = BASE_DIR / "data"
AUDIT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("cleaner")

# ---------------------------------------------------------------------------
# Task ID
# ---------------------------------------------------------------------------
TASK_ID = f"CLN-{datetime.now().strftime('%Y%m%d%H%M%S')}"

# ---------------------------------------------------------------------------
# Business bounds  {field: (lo, hi)}
# ---------------------------------------------------------------------------
BUSINESS_BOUNDS: dict = {
    "physicians_per_1000":    (0.0,  15.0),
    "nurses_per_1000":        (0.0,  20.0),
    "hospital_beds_per_1000":(0.0,  30.0),
    "population":             (0.0,  200_000.0),
    "physicians":             (0.0,  5_000_000.0),
    "nurses":                 (0.0,  8_000_000.0),
    "hospital_beds":          (0.0, 10_000_000.0),
    "paf":                    (0.0,  1.0),
    "dea_efficiency":         (0.0,  1.0),
    "val":                    (0.0,  1_000_000.0),
    "year":                   (1990, 2025),
    "elderly_ratio":          (0.0,  1.0),
    "eti":                    (0.0,  1.0),
    "spatial_accessibility":  (0.0,  1.0),
}

REQUIRED_FIELDS = [
    "region_name", "year",
    "physicians_per_1000", "nurses_per_1000", "hospital_beds_per_1000",
]

DATE_KEYWORDS = ["date", "time", "created_at", "updated_at"]
BOOL_KEYWORDS = ["status", "is_", "flag", "enabled", "active"]

# Full-width -> ASCII translation table
_FW_IN  = ''.join(chr(0xFF01 + i) for i in range(94))
_FW_OUT = ''.join(chr(0x21   + i) for i in range(94))
FULLWIDTH = str.maketrans(_FW_IN, _FW_OUT)

# ---------------------------------------------------------------------------
# Audit collectors
# ---------------------------------------------------------------------------
change_log:  list[dict] = []
anomaly_log: list[dict] = []


def _log_change(row_id, ctype: str, field: str, old, new, reason: str):
    change_log.append({
        "row_id": row_id, "change_type": ctype, "field": field,
        "old_value": old, "new_value": new,
        "reason": reason, "task_id": TASK_ID,
        "timestamp": datetime.now().isoformat(),
    })


def _log_anomaly(row_id, field: str, old, new, method: str, reason: str):
    anomaly_log.append({
        "row_id": row_id, "field": field,
        "original_value": old, "corrected_value": new,
        "detection_method": method, "correction_reason": reason,
        "task_id": TASK_ID, "timestamp": datetime.now().isoformat(),
    })


# ---------------------------------------------------------------------------
# Step 1 – Load
# ---------------------------------------------------------------------------
def load_data(file_path) -> pd.DataFrame:
    fp = Path(file_path)
    logger.info(f"Loading: {fp.name}  ({fp.stat().st_size / 1024:.1f} KB)")
    if not fp.exists():
        raise FileNotFoundError(fp)
    if fp.suffix in (".xlsx", ".xls"):
        return pd.read_excel(fp)
    if fp.suffix == ".csv":
        for enc in ("utf-8", "utf-8-sig", "gbk", "gb2312"):
            try:
                return pd.read_csv(fp, encoding=enc, on_bad_lines="skip")
            except Exception:
                continue
    raise ValueError(f"Unsupported format: {fp.suffix}")


# ---------------------------------------------------------------------------
# Step 2 – Dedup
# ---------------------------------------------------------------------------
def dedup(
    df: pd.DataFrame,
    source_file: str,
    business_keys: Optional[list] = None,
) -> tuple:
    """Returns (deduped_df, mapping_rows)."""
    mapping_rows: list[dict] = []
    n0 = len(df)

    # Full-row duplicates
    mask = df.duplicated(keep="first")
    for idx in df[mask].index:
        gid = f"FULL-{uuid.uuid4().hex[:8]}"
        mapping_rows.append({
            "duplicate_group_id": gid,
            "retained_file": source_file,
            "discarded_file": f"{source_file}::row_{idx}",
            "retention_reason": "full-row duplicate, keep first occurrence",
        })
        _log_change(idx, "dedup", "*", "duplicate row", "deleted", "full-row duplicate")
    df = df[~mask].copy()
    logger.info(f"  Full-row dedup: removed {n0 - len(df)}, remaining {len(df)}")

    # Business-key duplicates
    if business_keys:
        valid = [k for k in business_keys if k in df.columns]
        if valid:
            n1 = len(df)
            biz = df.duplicated(subset=valid, keep="first")
            for idx in df[biz].index:
                vals = {k: df.at[idx, k] for k in valid}
                gid = f"BIZ-{uuid.uuid4().hex[:8]}"
                mapping_rows.append({
                    "duplicate_group_id": gid,
                    "retained_file": source_file,
                    "discarded_file": f"{source_file}::row_{idx}",
                    "retention_reason": f"business-key duplicate {vals}",
                })
                _log_change(idx, "dedup", str(valid), str(vals), "deleted", "business-key duplicate")
            df = df[~biz].copy()
            logger.info(f"  Business-key dedup {valid}: removed {n1 - len(df)}, remaining {len(df)}")

    return df, mapping_rows


# ---------------------------------------------------------------------------
# Step 3 – Format standardisation
# ---------------------------------------------------------------------------
def _is_date(col: str) -> bool:
    return any(k in col.lower() for k in DATE_KEYWORDS)


def _is_bool(col: str) -> bool:
    return any(col.lower().startswith(k) or k in col.lower() for k in BOOL_KEYWORDS)


def standardize_formats(df: pd.DataFrame) -> pd.DataFrame:
    BOOL_MAP = {
        "true": 1, "false": 0, "yes": 1, "no": 0,
        "1": 1, "0": 0,
    }
    for col in df.columns:
        if _is_date(col):
            try:
                converted = pd.to_datetime(df[col], errors="coerce")
                ok = converted.notna() & df[col].notna()
                for idx in df[ok].index:
                    old = df.at[idx, col]
                    new = converted[idx].strftime("%Y-%m-%dT%H:%M:%S")
                    if str(old) != new:
                        _log_change(idx, "fmt", col, old, new, "ISO-8601 date")
                df[col] = converted.dt.strftime("%Y-%m-%dT%H:%M:%S").where(ok, df[col])
            except Exception:
                pass
        elif _is_bool(col) and df[col].dtype == object:
            for idx in df.index:
                old = df.at[idx, col]
                mapped = BOOL_MAP.get(str(old).strip().lower())
                if mapped is not None and old != mapped:
                    _log_change(idx, "fmt", col, old, mapped, "bool -> 0/1")
                    df.at[idx, col] = mapped
        elif df[col].dtype == object:
            def _clean(v):
                if not isinstance(v, str):
                    return v
                return v.strip().translate(FULLWIDTH)
            df[col] = df[col].map(_clean)
    logger.info("  Format standardisation done")
    return df


# ---------------------------------------------------------------------------
# Step 4 – Missing-value imputation
# ---------------------------------------------------------------------------
def handle_missing(
    df: pd.DataFrame,
    blocking: Optional[list] = None,
) -> pd.DataFrame:
    blocking = blocking or REQUIRED_FIELDS
    issues: list[str] = []

    for col in df.columns:
        nmiss = int(df[col].isna().sum())
        if nmiss == 0:
            continue
        if col in blocking:
            issues.append(f"BLOCKING: '{col}' has {nmiss} missing values – requires back-fill")
            logger.warning(f"  [BLOCKING] {col}: {nmiss} missing")
        if _is_date(col):
            fv, reason = "1990-01-01T00:00:00", "date field: business min date"
        elif pd.api.types.is_numeric_dtype(df[col]):
            med = df[col].median()
            fv  = 0 if pd.isna(med) else med
            reason = f"numeric: median={fv:.4g}"
        else:
            fv, reason = "Unknown", "categorical: Unknown"
        for idx in df[df[col].isna()].index:
            _log_change(idx, "impute", col, None, fv, reason)
        df[col] = df[col].fillna(fv)
        logger.info(f"  Impute '{col}': {nmiss} values -> {fv!r}")

    if issues:
        out = AUDIT_DIR / "blocking_issues.txt"
        out.write_text(f"Task: {TASK_ID}\n{datetime.now().isoformat()}\n\n" + "\n".join(issues), encoding="utf-8")
        logger.warning(f"  Blocking issues written: {out}")
    return df


# ---------------------------------------------------------------------------
# Step 5 – Anomaly detection & correction
# ---------------------------------------------------------------------------
def detect_and_correct_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """3-sigma + IQR + business bounds triple detection."""
    for col in df.select_dtypes(include=[np.number]).columns:
        s = df[col].dropna()
        if len(s) < 4:
            continue
        mu, sigma = s.mean(), s.std(ddof=1)
        q1, q3    = s.quantile(0.25), s.quantile(0.75)
        iqr       = q3 - q1
        lo3, hi3  = (mu - 3*sigma, mu + 3*sigma) if sigma > 0 else (-np.inf, np.inf)
        loI, hiI  = q1 - 1.5*iqr, q3 + 1.5*iqr
        loB, hiB  = BUSINESS_BOUNDS.get(col, (-np.inf, np.inf))
        lo = max(lo3, loI, loB)
        hi = min(hi3, hiI, hiB)
        if lo >= hi:
            lo, hi = loB, hiB
        anom = df[col].notna() & ((df[col] < lo) | (df[col] > hi))
        n_anom = int(anom.sum())
        if n_anom == 0:
            continue
        for idx in df[anom].index:
            old = df.at[idx, col]
            new = float(np.clip(old, lo, hi))
            methods = []
            if old < lo3 or old > hi3: methods.append("3sigma")
            if old < loI or old > hiI: methods.append("IQR")
            if old < loB or old > hiB: methods.append("business")
            reason = f"value {old:.4g} outside [{lo:.4g},{hi:.4g}]"
            _log_anomaly(idx, col, old, new, "+".join(methods), reason)
            _log_change(idx, "anomaly", col, old, new, reason)
            df.at[idx, col] = new
        logger.info(f"  Anomaly '{col}': corrected {n_anom} values")
    return df


# ---------------------------------------------------------------------------
# Step 6 – Schema validation
# ---------------------------------------------------------------------------
ENUM_FIELDS: dict = {
    "source":            {"WHO","Local","OWID","GBD","SEARCH"},
    "disease_category":  {"传染","非传染","伤害"},
    "gap_severity":      {"配置充足","合理","轻度短缺","严重短缺"},
    "role":              {"user","admin"},
}


def validate_schema(df: pd.DataFrame) -> dict:
    report = {"task_id": TASK_ID, "timestamp": datetime.now().isoformat(), "checks": []}
    n = len(df)

    # Uniqueness (year + region_name)
    region_col = next((c for c in df.columns if c in ("region_name","region")), None)
    year_col   = next((c for c in df.columns if c == "year"), None)
    if region_col and year_col:
        dup_rate = df.duplicated(subset=[region_col, year_col]).sum() / max(n, 1)
        report["checks"].append({"check": "uniqueness", "field": f"{region_col}+{year_col}",
                                  "value": f"{dup_rate:.4%}",
                                  "pass": dup_rate == 0})

    # Completeness: required fields missing rate <= 0.5%
    for col in REQUIRED_FIELDS:
        if col not in df.columns:
            report["checks"].append({"check": "completeness", "field": col,
                                      "value": "COLUMN MISSING", "pass": False})
            continue
        miss_rate = df[col].isna().sum() / max(n, 1)
        report["checks"].append({"check": "completeness", "field": col,
                                  "value": f"{miss_rate:.4%}",
                                  "pass": miss_rate <= 0.005})

    # Enum validity
    for col, valid_set in ENUM_FIELDS.items():
        if col not in df.columns:
            continue
        invalid_rate = (~df[col].isin(valid_set) & df[col].notna()).sum() / max(n, 1)
        report["checks"].append({"check": "enum_validity", "field": col,
                                  "value": f"{invalid_rate:.4%}",
                                  "pass": invalid_rate == 0})

    passed = sum(1 for c in report["checks"] if c.get("pass"))
    total  = len(report["checks"])
    report["summary"] = f"{passed}/{total} checks passed"
    report["overall_pass"] = passed == total
    logger.info(f"  Schema validation: {report['summary']}")
    return report


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------
def _write_csv(path: Path, rows: list, fields: list) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    logger.info(f"  Written: {path}  ({len(rows)} rows)")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
DEFAULT_INPUT = DATA_DIR / "processed" / "cleaned_health_data.xlsx"
DEFAULT_KEYS  = ["region_name", "year"]


def run_pipeline(input_path=None, business_keys=None) -> dict:
    fp   = Path(input_path) if input_path else DEFAULT_INPUT
    keys = business_keys or DEFAULT_KEYS

    logger.info(f"{'='*60}")
    logger.info(f"Data Cleaner Pipeline  Task={TASK_ID}")
    logger.info(f"Input : {fp}")
    logger.info(f"{'='*60}")

    # 1. Load
    if not fp.exists():
        logger.error(f"Input file not found: {fp}")
        return {"error": "input not found"}
    df = load_data(fp)
    n_input = len(df)
    logger.info(f"  Loaded {n_input} rows x {len(df.columns)} columns")

    # 2. Dedup
    df, map_rows = dedup(df, str(fp), keys)

    # 3. Format
    df = standardize_formats(df)

    # 4. Missing
    df = handle_missing(df)

    # 5. Anomaly
    df = detect_and_correct_anomalies(df)

    # 6. Validate
    val_report = validate_schema(df)

    # 7. Write outputs
    out_xlsx = AUDIT_DIR / "cleaned_output.xlsx"
    df.to_excel(out_xlsx, index=False)
    logger.info(f"  Cleaned data: {out_xlsx}  ({len(df)} rows)")

    _write_csv(AUDIT_DIR / "dedup_mapping.csv", map_rows,
               ["duplicate_group_id","retained_file","discarded_file","retention_reason"])
    _write_csv(AUDIT_DIR / "change_log.csv", change_log,
               ["row_id","change_type","field","old_value","new_value",
                "reason","task_id","timestamp"])
    _write_csv(AUDIT_DIR / "anomaly_correction_log.csv", anomaly_log,
               ["row_id","field","original_value","corrected_value",
                "detection_method","correction_reason","task_id","timestamp"])

    # Validation report JSON
    import json
    val_path = AUDIT_DIR / "schema_validation_report.json"
    val_path.write_text(json.dumps(val_report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"  Validation report: {val_path}")

    summary = {
        "task_id":          TASK_ID,
        "input_rows":       n_input,
        "output_rows":      len(df),
        "rows_removed":     n_input - len(df),
        "change_log_rows":  len(change_log),
        "anomaly_rows":     len(anomaly_log),
        "dedup_map_rows":   len(map_rows),
        "validation":       val_report["summary"],
        "overall_pass":     val_report["overall_pass"],
    }
    logger.info(f"{'='*60}")
    logger.info("Pipeline complete")
    for k, v in summary.items():
        logger.info(f"  {k}: {v}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Data Cleaner Pipeline")
    parser.add_argument("--input",  default=None, help="Input file path")
    parser.add_argument("--keys",   default=None, help="Business keys (comma-separated)")
    args = parser.parse_args()
    keys = args.keys.split(",") if args.keys else None
    run_pipeline(args.input, keys)


if __name__ == "__main__":
    main()