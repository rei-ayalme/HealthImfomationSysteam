#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
duplicate_detector.py  v2.1
============================
SHA-256 + file-size dual-factor physical duplicate detection.
Business-key (region + year) logical duplicate detection.

Outputs:
  audit/duplicate_report.csv
  audit/dedup_mapping.csv
  audit/gbd_dbd_comparison.csv

Usage:
  python audit/duplicate_detector.py
"""

import os, hashlib, csv, json
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
AUDIT_DIR = BASE_DIR / "audit"
AUDIT_DIR.mkdir(exist_ok=True)

SCAN_EXTENSIONS = {".csv",".xlsx",".xls",".json",".parquet",".db",".sqlite"}
SKIP_DIRS = {".mypy_cache","node_modules",".git","osmnx_cache",
             "geojson","__pycache__",".venv","venv","env"}

# ── 1. Physical duplicates ─────────────────────────────────────
def sha256_file(path: Path, chunk: int = 65536) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while buf := f.read(chunk):
                h.update(buf)
    except OSError:
        return "ERROR"
    return h.hexdigest()

def scan_files(root: Path) -> list:
    out = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            fp = Path(dp) / fn
            if fp.suffix.lower() not in SCAN_EXTENSIONS:
                continue
            try:
                st = fp.stat()
                out.append({"path": str(fp), "filename": fn,
                             "extension": fp.suffix.lower(),
                             "size": st.st_size,
                             "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                             "ctime": datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S")})
            except OSError:
                continue
    return out

def detect_physical_duplicates(file_list: list) -> tuple:
    key_map = defaultdict(list)
    total = len(file_list)
    print(f"[INFO] Computing SHA-256 for {total} files ...")
    for i, e in enumerate(file_list):
        if i % 20 == 0:
            print(f"  {i}/{total}")
        key_map[(sha256_file(Path(e["path"])), e["size"])].append(e)
    dup_rows, map_rows, gid = [], [], 1
    for (digest, size), members in key_map.items():
        if len(members) < 2:
            continue
        ms = sorted(members, key=lambda x: x["mtime"])
        retained = ms[0]
        for idx, m in enumerate(ms):
            keep = idx == 0
            dup_rows.append({"duplicate_group_id": f"PHY-{gid:04d}",
                             "file_path": m["path"], "duplicate_type": "physical",
                             "sha256": digest, "file_size_bytes": size,
                             "mtime": m["mtime"], "first_occurrence_time": retained["mtime"],
                             "duplicate_rows": "N/A",
                             "retention_recommendation": "keep" if keep else "delete",
                             "retention_reason": "earliest mtime" if keep else f"identical to {retained['path']}"})
            if not keep:
                map_rows.append({"duplicate_group_id": f"PHY-{gid:04d}",
                                 "retained_file": retained["path"],
                                 "discarded_file": m["path"],
                                 "duplicate_type": "physical",
                                 "sha256": digest, "file_size_bytes": size,
                                 "retention_reason": "earliest mtime wins"})
        gid += 1
    return dup_rows, map_rows

# ── 2. Logical duplicates (region + year) ─────────────────────
LOGICAL_TARGETS = [
    Path("data/processed/cleaned_health_data.xlsx"),
    Path("data/raw/GBD.csv"),
    Path("data/raw/DBD.csv"),
    Path("data/raw/NBS.csv"),
    Path("data/raw/WDI.csv"),
    Path("frontend/assets/data/cn_health.json"),
    Path("frontend/assets/data/cleaned_health_data.json"),
]
REGION_KEYS = ["region_name","region","location_name","location","area"]
YEAR_KEYS   = ["year"]

def _find_col(df, candidates):
    lm = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in df.columns: return c
        if c.lower() in lm: return lm[c.lower()]
    return None

def _load_file(fp: Path):
    if not fp.exists():
        return None
    try:
        if fp.suffix in (".xlsx",".xls"):
            return pd.read_excel(fp)
        if fp.suffix == ".csv":
            for enc in ("utf-8","utf-8-sig","gbk","gb2312"):
                try: return pd.read_csv(fp, encoding=enc, on_bad_lines="skip")
                except Exception: continue
        if fp.suffix == ".json":
            data = json.loads(fp.read_text(encoding="utf-8"))
            if isinstance(data, list): return pd.DataFrame(data)
            for v in data.values():
                if isinstance(v, list): return pd.DataFrame(v)
    except Exception as e:
        print(f"[WARN] {fp}: {e}")
    return None

def detect_logical_duplicates(targets: list) -> tuple:
    dup_rows, map_rows, gid = [], [], 1
    for rel in targets:
        fp = BASE_DIR / rel if not Path(rel).is_absolute() else Path(rel)
        df = _load_file(fp)
        if df is None or df.empty: continue
        rc = _find_col(df, REGION_KEYS)
        yc = _find_col(df, YEAR_KEYS)
        if not rc or not yc:
            print(f"[INFO] {fp.name}: no region/year col, skip")
            continue
        mask = df.duplicated(subset=[rc, yc], keep=False)
        if not mask.any():
            print(f"[OK] {fp.name}: no logical duplicates")
            continue
        fs = fp.stat().st_size
        mt = datetime.fromtimestamp(fp.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        for key, grp in df[mask].groupby([rc, yc]):
            ri = grp.index[0]
            di = list(grp.index[1:])
            dup_rows.append({"duplicate_group_id": f"LOG-{gid:04d}",
                             "file_path": str(fp), "duplicate_type": "logical",
                             "sha256": "N/A", "file_size_bytes": fs, "mtime": mt,
                             "first_occurrence_time": str(ri),
                             "duplicate_rows": len(grp),
                             "retention_recommendation": f"keep row {ri}, drop {di}",
                             "retention_reason": f"{rc}={key[0]}, {yc}={key[1]} x{len(grp)}"})
            for d in di:
                map_rows.append({"duplicate_group_id": f"LOG-{gid:04d}",
                                 "retained_file": f"{fp}::row_{ri}",
                                 "discarded_file": f"{fp}::row_{d}",
                                 "duplicate_type": "logical",
                                 "sha256": "N/A", "file_size_bytes": fs,
                                 "retention_reason": f"keep first occurrence ({rc}={key[0]},{yc}={key[1]})"})
            gid += 1
        print(f"[WARN] {fp.name}: {int(mask.sum())} logical duplicate rows")
    return dup_rows, map_rows

# ── 3. GBD vs DBD comparison ──────────────────────────────────
def compare_gbd_dbd() -> list:
    gbd = DATA_DIR / "raw" / "GBD.csv"
    dbd = DATA_DIR / "raw" / "DBD.csv"
    if not (gbd.exists() and dbd.exists()): return []
    gh, dh = sha256_file(gbd), sha256_file(dbd)
    gs, ds = gbd.stat().st_size, dbd.stat().st_size
    identical = gh == dh and gs == ds
    print(f"[INFO] GBD vs DBD: {'IDENTICAL' if identical else 'DIFFERENT'} | size diff {abs(gs-ds)} bytes")
    return [{"comparison": "GBD.csv vs DBD.csv",
             "gbd_sha256": gh, "dbd_sha256": dh,
             "gbd_size_bytes": gs, "dbd_size_bytes": ds,
             "physically_identical": identical, "size_diff_bytes": abs(gs-ds),
             "recommendation": "keep GBD.csv, archive DBD.csv" if identical else "manual review required"}]

# ── 4. CSV writer ──────────────────────────────────────────────
def _write_csv(path: Path, rows: list, fields: list) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    print(f"[OUT] {path}  ({len(rows)} rows)")

# ── 5. Main ────────────────────────────────────────────────────
def main() -> dict:
    print("=" * 60)
    print("Duplicate Detection Audit Tool  v2.1")
    print(f"Scan root: {DATA_DIR}")
    print("=" * 60)

    print("\n[Step 1] Scanning files ...")
    fl = scan_files(DATA_DIR)
    fl += scan_files(BASE_DIR / "frontend" / "assets" / "data")
    fl += scan_files(BASE_DIR / "deepanalyze")
    print(f"  {len(fl)} files found")

    pd_rows, pm_rows = detect_physical_duplicates(fl)
    pg = len(set(r["duplicate_group_id"] for r in pd_rows))
    print(f"  Physical duplicate groups: {pg}")

    print("\n[Step 2] Logical duplicate detection ...")
    ld_rows, lm_rows = detect_logical_duplicates(LOGICAL_TARGETS)
    print(f"  Logical duplicate records: {len(ld_rows)}")

    print("\n[Step 3] GBD vs DBD comparison ...")
    cmp = compare_gbd_dbd()

    all_dup = pd_rows + ld_rows
    all_map = pm_rows + lm_rows

    _write_csv(AUDIT_DIR / "duplicate_report.csv", all_dup,
               ["duplicate_group_id","file_path","duplicate_type","sha256",
                "file_size_bytes","mtime","first_occurrence_time",
                "duplicate_rows","retention_recommendation","retention_reason"])
    _write_csv(AUDIT_DIR / "dedup_mapping.csv", all_map,
               ["duplicate_group_id","retained_file","discarded_file",
                "duplicate_type","sha256","file_size_bytes","retention_reason"])
    if cmp:
        _write_csv(AUDIT_DIR / "gbd_dbd_comparison.csv", cmp,
                   ["comparison","gbd_sha256","dbd_sha256","gbd_size_bytes",
                    "dbd_size_bytes","physically_identical","size_diff_bytes","recommendation"])

    summary = {"total_files_scanned": len(fl), "physical_dup_groups": pg,
               "physical_dup_records": len(pd_rows), "logical_dup_records": len(ld_rows),
               "dedup_mapping_entries": len(all_map)}
    print("\n" + "=" * 60 + "\nDone")
    for k, v in summary.items(): print(f"  {k}: {v}")
    return summary

if __name__ == "__main__":
    main()
