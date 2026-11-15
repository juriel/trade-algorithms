import random

import numpy as np
import pandas as pd

from algorithms.genetic import GAConfig, Gene, load_genes, mutate, sample_windows


def _frames(n_sym=60, n=1200):
    return {f"S{i}": pd.DataFrame({"date": pd.bdate_range("2015-01-01", periods=n),
                                   "close": np.arange(n, dtype=float)}) for i in range(n_sym)}


def test_sample_windows_bounds():
    fr = _frames()
    cfg = GAConfig()
    s = sample_windows(list(fr), lambda x: fr[x], cfg, random.Random(1))
    assert len(s) == 50 and len({sym for sym, _ in s}) == 50
    assert all(300 <= len(df) <= 600 for _, df in s)
    assert all(df["date"].iloc[0] >= fr["S0"]["date"].iloc[cfg.warmup_bars] for _, df in s)


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
