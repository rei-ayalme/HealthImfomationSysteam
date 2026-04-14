import numpy as np

from modules.core.spatial_engine import (
    baseline_2sfca,
    optimized_2sfca,
    gini_coefficient,
    make_synthetic_dataset,
)


def test_baseline_and_optimized_numerical_equivalence():
    d, dem, sup = make_synthetic_dataset(10_000, seed=7)
    base = baseline_2sfca(d, dem, sup, catchment=30.0, decay="uniform")
    opt = optimized_2sfca(d, dem, sup, catchment=30.0, decay="uniform")
    assert np.allclose(base.accessibility, opt.accessibility, atol=1e-6)
    assert np.allclose(base.supply_ratio, opt.supply_ratio, atol=1e-6)


def test_inverse_power_equivalence():
    d, dem, sup = make_synthetic_dataset(10_000, seed=11)
    base = baseline_2sfca(d, dem, sup, catchment=35.0, decay="inverse_power", beta=1.5)
    opt = optimized_2sfca(d, dem, sup, catchment=35.0, decay="inverse_power", beta=1.5)
    assert np.allclose(base.accessibility, opt.accessibility, atol=1e-6)
    assert np.allclose(base.supply_ratio, opt.supply_ratio, atol=1e-6)


def test_gini_coefficient_range():
    x = np.array([0.2, 0.4, 0.8, 1.2, 2.0], dtype=np.float64)
    g = gini_coefficient(x)
    assert 0.0 <= g <= 1.0
