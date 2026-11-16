"""Estudio de eventos del volumen: ¿el volumen del día de la señal predice el retorno de la operación?

Para cada algoritmo se juntan sus operaciones (una acción a la vez, ver analyze.py) con las variables de volumen de la
jornada de la señal. Los puntos de corte (terciles) se fijan en el conjunto de DESCUBRIMIENTO (mitad "análisis" de las
acciones, entradas 1996-2019) y se aplican SIN CAMBIOS a los de CONFIRMACIÓN: (a) la otra mitad de acciones antes de 2020 y
(b) la otra mitad de acciones en 2020-2023. Se informa la diferencia de retorno medio por operación (tercil bajo - tercil alto)
con IC 95% (bootstrap simple; las operaciones de un mismo día no son independientes, el IC es optimista).

Uso:  python -m algorithms.volume_study algorithm03a_v1 algorithm01b ...
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from ticker2db import StockDB

from .analyze import collect_trades, split_symbols
from .genetic import load_ga_config
from .metrics import bootstrap_ci

VOL_FEATURES = ["vol_ratio", "vol_ratio3", "vol_dryup", "cmf20", "obv_flow20"]
DOC = {"vol_ratio": "volumen del día / media 20d previa", "vol_ratio3": "volumen medio 3d / media 20d previa",
       "vol_dryup": "volumen medio 5d / media 20d anterior", "cmf20": "flujo de dinero Chaikin 20d",
       "obv_flow20": "cambio del OBV 20d (acumulación)"}


def diff_ci(t: pd.DataFrame, feat: str, lo_cut: float, hi_cut: float, seed: int = 0):
    lo = t.loc[t[feat] <= lo_cut, "return_pct"].to_numpy() * 100
    hi = t.loc[t[feat] >= hi_cut, "return_pct"].to_numpy() * 100
    if len(lo) < 30 or len(hi) < 30:
        return np.nan, np.nan, np.nan, len(lo), len(hi)
    rng = np.random.default_rng(seed)
    d = (rng.choice(lo, (2000, len(lo))).mean(axis=1) - rng.choice(hi, (2000, len(hi))).mean(axis=1))
    a, b = np.percentile(d, [2.5, 97.5])
    return lo.mean() - hi.mean(), a, b, len(lo), len(hi)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("algorithms", nargs="+")
    a = ap.parse_args()
    cfg = load_ga_config()
    with StockDB(cfg.db_path) as db:
        syms = db.symbols()
    an, va = split_symbols(syms)
    for name in a.algorithms:
        disc = collect_trades(name, an, cfg.db_path, since="1996-01-01", until="2019-12-31")
        c1 = collect_trades(name, va, cfg.db_path, since="1996-01-01", until="2019-12-31")
        c2 = collect_trades(name, va, cfg.db_path, since="2020-01-01", until="2023-12-31")
        print(f"\n### {name}: operaciones descubrimiento {len(disc)} | confirmación 1996-2019 {len(c1)} | 2020-2023 {len(c2)} "
              f"| retorno medio por operación {disc.return_pct.mean()*100:.2f}% / {c1.return_pct.mean()*100:.2f}% / {c2.return_pct.mean()*100:.2f}%")
        print(f"{'variable':<11}{'cortes (bajo/alto)':<22}{'DESCUBRIMIENTO':<30}{'CONFIRM. 1996-2019':<30}{'CONFIRM. 2020-2023'}")
        for f in VOL_FEATURES:
            x = disc[f].dropna()
            lo, hi = x.quantile(1 / 3), x.quantile(2 / 3)
            cells = []
            for t in (disc, c1, c2):
                d, a_, b_, nl, nh = diff_ci(t, f, lo, hi)
                cells.append(f"{d:+.2f} ({a_:+.2f}..{b_:+.2f})" if not np.isnan(d) else "n/d")
            print(f"{f:<11}{lo:>8.2f}/{hi:<12.2f} {cells[0]:<29}{cells[1]:<30}{cells[2]}")
    print("\nDiferencia = retorno medio por operación en % del tercil de volumen BAJO menos el ALTO. + = mejor con volumen bajo.")


if __name__ == "__main__":
    main()
