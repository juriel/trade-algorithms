"""Meta-etiquetado con gradient boosting: un modelo decide si tomar cada señal de un algoritmo base.

Idea (López de Prado, "meta-labeling"): el algoritmo base ya tiene una ventaja; el modelo solo filtra sus señales, estimando
la probabilidad de que la operación gane (retorno > 0) con las variables del día de la señal (indicadores, volumen, caída,
variables de mercado `mkt_*`). Así hay mucho menos espacio para sobreajustar que buscando señales desde cero.

Protocolo SIN FILTRACIÓN DE INFORMACIÓN FUTURA:
  * Reentrenamiento anual: el modelo del año Y se entrena solo con operaciones que TERMINARON antes del 1 de enero de Y.
  * Se entrena con la mitad "análisis" de las acciones y se evalúa en la mitad "validación" (acciones distintas).
  * Un modelo pequeño y fijo (árboles de profundidad 3, regularizados) y un umbral relativo (tasa de acierto histórica
    del entrenamiento + `margin`), sin optimizar por búsqueda.

CLI:  python -m algorithms.ml build <base>      # operaciones + variables del grupo análisis y validación
      python -m algorithms.ml train <base>      # modelos anuales (2006..)
      python -m algorithms.ml lift  <base>      # ¿el modelo ordena las operaciones fuera de muestra?
"""
from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ticker2db import FEATURE_DOC, StockDB

from .analyze import EXTRA, FEATURES, add_features, collect_trades, split_symbols
from .genetic import load_ga_config
from .metrics import bootstrap_ci

HERE = Path(__file__).parent
DATA_DIR = Path("output/ai_data")      # no se versiona
MODEL_DIR = Path("output/ai_models")   # no se versiona
FIRST_YEAR = 2006
MIN_TRAIN_TRADES = 400
LAST_DATA = "2023-12-31"               # lo posterior (2024+) queda reservado

MKT_COLS = [c for c in FEATURE_DOC if c.startswith("mkt_")]
MODEL_FEATURES = [f for f in FEATURES + EXTRA if f not in ("dow", "cdl_net")] + MKT_COLS
# columnas "crudas" que `add_features` necesita sobre el DataFrame de la acción
RAW_COLS = ["open", "high", "low", "close", "volume", "rsi_14", "stoch_k", "adx_14", "cci_14", "mfi_14", "atr_14",
            "sma_20", "sma_50", "sma_200", "bb_upper", "bb_lower", "bb_middle", "macd_hist"] + MKT_COLS


def _newmodel():
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=120, min_samples_leaf=40,
                                          l2_regularization=1.0, random_state=0)


def dataset_path(base: str, group: str) -> Path:
    return DATA_DIR / f"{base}_{group}.csv"


def build_dataset(base: str, group: str) -> pd.DataFrame:
    """Operaciones del algoritmo base (una acción a la vez) con las variables del día de la señal."""
    cfg = load_ga_config()
    with StockDB(cfg.db_path) as db:
        syms = db.symbols()
    an, va = split_symbols(syms)
    t = collect_trades(base, an if group == "analysis" else va, cfg.db_path, since="1996-01-01", until=LAST_DATA)
    keep = ["symbol", "entry_date", "exit_date", "return_pct", "days_held", "reason"] + [c for c in MODEL_FEATURES if c in t.columns]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    t[keep].to_csv(dataset_path(base, group), index=False)
    return t[keep]


def load_dataset(base: str, group: str) -> pd.DataFrame:
    p = dataset_path(base, group)
    if not p.exists():
        raise FileNotFoundError(f"Falta {p}: ejecuta `python -m algorithms.ml build {base}`")
    return pd.read_csv(p, parse_dates=["entry_date", "exit_date"])


def train_year(base: str, year: int) -> Optional[Tuple[object, float, int, List[str]]]:
    """Modelo del año `year`: solo operaciones del grupo análisis que terminaron antes del 1 de enero de `year`."""
    d = load_dataset(base, "analysis")
    d = d[d["exit_date"] < pd.Timestamp(f"{year}-01-01")].dropna(subset=["return_pct"])
    if len(d) < MIN_TRAIN_TRADES:
        return None
    y = (d["return_pct"] > 0).astype(int).to_numpy()
    # variables que existen en el periodo de entrenamiento (p.ej. el crédito HYG/LQD no existe antes de 2007)
    feats = [c for c in MODEL_FEATURES if d[c].nunique(dropna=True) >= 2]
    model = _newmodel().fit(d[feats], y)
    return model, float(y.mean()), len(d), feats


def get_model(base: str, year: int):
    """Modelo anual desde disco (lo entrena y guarda si no existe). Devuelve (modelo, tasa de acierto, n, variables) o None."""
    import joblib
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    p = MODEL_DIR / f"{base}_{year}.joblib"
    if p.exists():
        return joblib.load(p)
    res = train_year(base, year)
    if res is not None:
        fd, tmp = tempfile.mkstemp(dir=MODEL_DIR, suffix=".tmp")
        os.close(fd)
        joblib.dump(res, tmp)
        os.replace(tmp, p)            # escritura atómica: varios procesos pueden pedirlo a la vez
    return res


class MetaGate:
    """Filtro: `gate(df, base_signal)` deja pasar la señal si el modelo del año estima P(ganar) >= tasa histórica + margin."""

    def __init__(self, base: str, margin: float = 0.0):
        self.base, self.margin = base, margin

    def gate(self, df: pd.DataFrame, base_signal: pd.Series, margin: Optional[float] = None) -> pd.Series:
        m = self.margin if margin is None else margin
        out = pd.Series(False, index=df.index)
        idx = np.flatnonzero(base_signal.to_numpy(bool))
        if len(idx) == 0:
            return out
        feats = add_features(df)[MODEL_FEATURES]
        years = pd.to_datetime(df["date"]).dt.year.to_numpy()
        for yr in np.unique(years[idx]):
            res = get_model(self.base, int(max(yr, FIRST_YEAR))) if yr >= FIRST_YEAR else None
            if res is None:
                continue                                    # sin modelo (antes de FIRST_YEAR): no se opera
            model, rate, _, cols = res
            rows = idx[years[idx] == yr]
            p = model.predict_proba(feats.iloc[rows][cols])[:, 1]
            out.iloc[rows[p >= rate + m]] = True
        return out


# ----------------------------- diagnóstico fuera de muestra -----------------------------
def lift(base: str, margin: float = 0.0, verbose: bool = True) -> dict:
    """Aplica los modelos anuales a las operaciones del grupo VALIDACIÓN (acciones no vistas) desde FIRST_YEAR."""
    from sklearn.metrics import roc_auc_score
    v = load_dataset(base, "validation")
    v = v[v["entry_date"] >= pd.Timestamp(f"{FIRST_YEAR}-01-01")].dropna(subset=["return_pct"]).copy()
    v["p"] = np.nan
    v["keep"] = False
    for yr, g in v.groupby(v["entry_date"].dt.year):
        res = get_model(base, int(yr))
        if res is None:
            continue
        model, rate, _, cols = res
        p = model.predict_proba(g[cols])[:, 1]
        v.loc[g.index, "p"] = p
        v.loc[g.index, "keep"] = p >= rate + margin
    v = v.dropna(subset=["p"])
    win = (v["return_pct"] > 0).astype(int)
    auc = roc_auc_score(win, v["p"]) if win.nunique() > 1 else np.nan
    tert = pd.qcut(v["p"], 3, labels=["bajo", "medio", "alto"])
    r = v["return_pct"] * 100
    kept, dropped = r[v["keep"]], r[~v["keep"]]
    rng = np.random.default_rng(0)
    diff = rng.choice(kept.to_numpy(), (2000, len(kept))).mean(1) - rng.choice(dropped.to_numpy(), (2000, len(dropped))).mean(1)
    res = {"n": len(v), "auc": auc, "ret_todas": r.mean(), "ret_kept": kept.mean(), "ret_dropped": dropped.mean(),
           "pct_kept": v["keep"].mean() * 100, "dif_kept_dropped": diff.mean(), "dif_ic": tuple(np.percentile(diff, [2.5, 97.5])),
           "ret_por_tercil": {k: float(r[tert == k].mean()) for k in ["bajo", "medio", "alto"]},
           "acierto_por_tercil": {k: float(win[tert == k].mean() * 100) for k in ["bajo", "medio", "alto"]}}
    if verbose:
        print(f"\n### {base}: {res['n']} operaciones fuera de muestra (acciones de validación, {FIRST_YEAR}-2023)")
        print(f"AUC (acierto vs. probabilidad del modelo): {auc:.3f}  (0,5 = azar)")
        print(f"retorno medio por operación: todas {res['ret_todas']:.2f}% | el modelo deja pasar {res['pct_kept']:.0f}% -> {res['ret_kept']:.2f}% | "
              f"descarta -> {res['ret_dropped']:.2f}%  (dif. {res['dif_kept_dropped']:+.2f}, IC {res['dif_ic'][0]:+.2f}..{res['dif_ic'][1]:+.2f})")
        print("por tercil de probabilidad (bajo/medio/alto): retorno medio % " +
              " / ".join(f"{res['ret_por_tercil'][k]:.2f}" for k in ["bajo", "medio", "alto"]) + " | acierto % " +
              " / ".join(f"{res['acierto_por_tercil'][k]:.1f}" for k in ["bajo", "medio", "alto"]))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("command", choices=["build", "train", "lift"])
    ap.add_argument("bases", nargs="+")
    ap.add_argument("--margin", type=float, default=0.0)
    a = ap.parse_args()
    for base in a.bases:
        if a.command == "build":
            for g in ("analysis", "validation"):
                d = build_dataset(base, g)
                print(f"{base} {g}: {len(d)} operaciones, {len(MODEL_FEATURES)} variables")
        elif a.command == "train":
            for yr in range(FIRST_YEAR, int(LAST_DATA[:4]) + 2):
                r = get_model(base, yr)
                print(f"{base} {yr}: " + ("sin datos suficientes" if r is None else f"{r[2]} operaciones de entrenamiento, acierto histórico {r[1]*100:.1f}%"))
        else:
            lift(base, a.margin)


if __name__ == "__main__":
    main()


def random_gate(df: pd.DataFrame, base_signal: pd.Series, keep_frac: float) -> pd.Series:
    """CONTROL: deja pasar cada señal con probabilidad `keep_frac` de forma pseudoaleatoria y determinista (según fecha y precio)."""
    d = (pd.to_datetime(df["date"]).astype("int64") // 86_400_000_000_000).to_numpy()
    c = np.round(df["close"].to_numpy(float) * 100).astype("int64")
    h = ((d * 2654435761) ^ (c * 40503)) % 1000
    return base_signal & pd.Series(h < keep_frac * 1000, index=df.index)
