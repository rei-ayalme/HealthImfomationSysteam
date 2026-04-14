import json
import time
import tracemalloc
from pathlib import Path

import numpy as np

from modules.core.spatial_engine import (
    baseline_2sfca,
    optimized_2sfca,
    make_synthetic_dataset,
)


def _measure(fn, *args, repeat=3, **kwargs):
    costs = []
    peaks = []
    result = None
    for _ in range(repeat):
        tracemalloc.start()
        t0 = time.perf_counter()
        result = fn(*args, **kwargs)
        dt = time.perf_counter() - t0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        costs.append(dt)
        peaks.append(peak / (1024 * 1024))
    return result, float(np.mean(costs)), float(np.mean(peaks))


def test_benchmark_speed_and_memory_targets():
    sizes = [10_000, 100_000, 1_000_000]
    rows = []
    for size in sizes:
        d, dem, sup = make_synthetic_dataset(size, seed=42 + size // 1000)
        base_res, base_t, base_mem = _measure(
            baseline_2sfca,
            d,
            dem,
            sup,
            catchment=30.0,
            decay="uniform",
            repeat=3,
        )
        opt_res, opt_t, opt_mem = _measure(
            optimized_2sfca,
            d,
            dem,
            sup,
            catchment=30.0,
            decay="uniform",
            repeat=3,
        )

        assert np.allclose(base_res.accessibility, opt_res.accessibility, atol=1e-6)

        speedup = (base_t - opt_t) / base_t
        mem_reduction = (base_mem - opt_mem) / base_mem if base_mem > 0 else 0.0

        assert speedup >= 0.30
        assert mem_reduction >= 0.20

        rows.append(
            {
                "size_pairs": size,
                "baseline_time_s": round(base_t, 6),
                "optimized_time_s": round(opt_t, 6),
                "speedup_ratio": round(speedup, 6),
                "baseline_peak_mem_mb": round(base_mem, 6),
                "optimized_peak_mem_mb": round(opt_mem, 6),
                "memory_reduction_ratio": round(mem_reduction, 6),
            }
        )

    report_dir = Path("reports/deepanalyze")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / "spatial_access_benchmark.json"
    report_file.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
