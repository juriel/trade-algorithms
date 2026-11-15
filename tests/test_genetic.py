import random

import numpy as np
import pandas as pd

from algorithms.genetic import GAConfig, Gene, load_genes, mutate, sample_windows


def _frames(n_sym=60, n=1200):
    return {f"S{i}": pd.DataFrame({"date": pd.bdate_range("2015-01-01", periods=n),
                                   "close": np.arange(n, dtype=float)}) for i in range(n_sym)}


def test_sample_windows_independent_random_tests():
    fr = _frames()
    cfg = GAConfig()
    s = sample_windows(list(fr), lambda x: fr[x], cfg, random.Random(1))
    assert len(s) == 50
    assert all(300 <= len(df) <= 600 for _, df in s)
    assert all(df["date"].iloc[0] >= fr["S0"]["date"].iloc[cfg.warmup_bars] for _, df in s)
    starts = {df["date"].iloc[0] for _, df in s}
    assert len(starts) > 25                                   # fechas de inicio distintas, no una fija
    assert len({len(df) for _, df in s}) > 20                 # largos distintos
    # con reposición: una acción puede aparecer varias veces con periodos distintos
    few = {f"S{i}": fr[f"S{i}"] for i in range(3)}
    s3 = sample_windows(list(few), lambda x: few[x], cfg, random.Random(2))
    assert len(s3) == 50 and len({sym for sym, _ in s3}) == 3
    # unique=True impide repetir
    s_u = sample_windows(list(fr), lambda x: fr[x], cfg, random.Random(3), unique=True)
    assert len({sym for sym, _ in s_u}) == 50


def test_sample_windows_respects_optional_date_range():
    fr = _frames()
    s = sample_windows(list(fr), lambda x: fr[x], GAConfig(), random.Random(4), date_min="2018-01-01", date_max="2019-12-31")
    assert s and all(d["date"].iloc[0] >= pd.Timestamp("2018-01-01") and d["date"].iloc[-1] <= pd.Timestamp("2019-12-31")
                     for _, d in s)


def test_genes_random_and_mutate_in_range():
    rng = random.Random(0)
    for name in ("algorithm01", "algorithm02", "algorithm03"):
        genes = load_genes(name)
        g = {x.name: x.random(rng) for x in genes}
        for _ in range(200):
            g = mutate(g, genes, 1.0, rng)
            for x in genes:
                v = g[x.name]
                if x.type == "bool":
                    assert isinstance(v, bool)
                elif v is not None:
                    assert x.min <= v <= x.max
                else:
                    assert x.allow_none
