"""Métrica y estadística para comparar algoritmos.

Problema de la métrica anterior (CAGR − ½·drawdown): premiaba NO operar, porque el efectivo valía 0 y casi toda
estrategia valía menos. La métrica actual es el **alpha de timing** de cada prueba:

    alpha = CAGR de la estrategia − [exposición × CAGR de la acción + (1 − exposición) × tasa libre de riesgo]

Es decir, cuánto rinde de más que una cartera con la misma exposición pero sin elegir cuándo estar dentro.
Estar siempre en efectivo da alpha ≈ 0 (el efectivo rinde la letra a 13 semanas); solo suma quien acierta cuándo
invertir. Se acompaña de intervalos de confianza (bootstrap), p-valores y corrección por múltiples comparaciones.
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

import numpy as np
import pandas as pd


def bootstrap_ci(x: Sequence[float], n_boot: int = 2000, level: float = 0.95, seed: int = 0):
    """Intervalo de confianza (percentiles) de la media por bootstrap."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = rng.choice(x, size=(n_boot, len(x)), replace=True).mean(axis=1)
    lo, hi = np.percentile(means, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    return float(lo), float(hi)


def mean_pvalue(x: Sequence[float]) -> float:
    """p-valor unilateral de H0: media <= 0 (aproximación normal; n grande). Muestras independientes."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 2 or x.std(ddof=1) == 0:
        return 1.0 if n < 2 or x.mean() <= 0 else 0.0
    z = x.mean() / (x.std(ddof=1) / math.sqrt(n))
    return 0.5 * math.erfc(z / math.sqrt(2))


def bh_adjust(p: Sequence[float]) -> np.ndarray:
    """Ajuste de Benjamini-Hochberg (control de la tasa de falsos descubrimientos) para varios p-valores."""
    p = np.asarray(p, float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / (np.arange(n) + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(adj, 1.0)
    return out


def summarize_tests(tests: pd.DataFrame, value: str = "alpha", group: str = "algorithm",
                    n_boot: int = 2000, fdr: float = 0.05, seed: int = 0) -> pd.DataFrame:
    """Por algoritmo: media del alpha por prueba, IC 95%, % de pruebas con alpha > 0, p-valor ajustado (BH).

    `tests`: una fila por (algoritmo, prueba) con la columna `value`. `significativo` = el p-valor ajustado de
    que el alpha medio sea > 0 es menor a `fdr`.
    """
    rows = []
    for name, g in tests.groupby(group, sort=False):
        x = g[value].to_numpy(float)
        lo, hi = bootstrap_ci(x, n_boot, seed=seed)
        rows.append({group: name, "pruebas": len(x), "alpha_medio": float(np.nanmean(x)), "alpha_ic_inf": lo,
                     "alpha_ic_sup": hi, "pct_alpha_pos": float(np.nanmean(x > 0) * 100), "p_valor": mean_pvalue(x)})
    out = pd.DataFrame(rows).set_index(group)
    out["p_ajustado"] = bh_adjust(out["p_valor"].to_numpy())
    out["significativo"] = out["p_ajustado"] < fdr
    return out
