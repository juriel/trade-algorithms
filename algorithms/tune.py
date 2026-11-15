"""Afina el `variables.cfg` de cada algoritmo haciendo competir configuraciones.

Para cada algoritmo:
  1. ENTRENAMIENTO: el algoritmo genético busca variables sobre `train_samples` acciones de la
     mitad "análisis" y periodos de 300-600 barras que terminan antes de `train_end`.
  2. SELECCIÓN: el candidato compite contra las variables actuales (`variables.cfg`) en
     `select_rounds` rondas de 50 acciones de la mitad "validación" (otras acciones) y mismo
     rango de fechas. Solo se adopta si gana la mediana del fitness, gana en la mayoría de las
     rondas y no sigue penalizado por pocas operaciones; si no, se conservan las variables actuales (evita el sobreajuste de una sola muestra).
  3. Si se adopta, se reescriben los valores en `variables.cfg` conservando sus comentarios.
El periodo posterior a `test_start` no se toca: queda para el torneo final fuera de tiempo
(`python -m algorithms.compete --group validation --period test`).

Uso:  python -m algorithms.tune [algoritmos...] [--workers 5] [--dry-run] [--set population=20]
"""
from __future__ import annotations

import argparse
import ast
import functools
import json
import random
import re
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Dict, List

import numpy as np

from ticker2db import StockDB

from .analyze import split_symbols
from .compete import discover_all
from .genetic import PENALTY, GAConfig, loader, evolve, fitness, load_ga_config, make_algo, sample_windows

HERE = Path(__file__).parent


def fmt(v) -> str:
    return repr(round(v, 4) if isinstance(v, float) else v)


def update_cfg_values(path: Path, genome: dict) -> None:
    """Cambia solo los valores de `variables.cfg`, conservando comentarios y orden."""
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)([A-Za-z_]\w*)(\s*=\s*)([^#\n]*?)(\s*)(#.*)?$", line)
        if m and m.group(2) in genome:
            pad = max(len(m.group(4)) + len(m.group(5)), len(fmt(genome[m.group(2)])) + 2)
            val = fmt(genome[m.group(2)]).ljust(pad)
            lines[i] = f"{m.group(1)}{m.group(2)}{m.group(3)}{val}{m.group(6) or ''}".rstrip()
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tune_one(name: str, cfgd: dict, dry_run: bool) -> dict:
    cfg = GAConfig(**cfgd)
    seed = cfg.seed if cfg.seed is not None else random.randrange(2**31)
    rng = random.Random(f"{seed}-tune-{name}")
    t0 = time.time()
    logs: List[str] = []
    analysis, validation = split_symbols(_symbols(cfg))
    with StockDB(cfg.db_path) as db:
        cache: Dict[str, object] = {}
        _load = loader(db, [name])
        def load(s):
            if s not in cache:
                cache[s] = _load(s)
            return cache[s]
        train = sample_windows(analysis, load, cfg, rng, date_max=cfg.train_end, n=cfg.train_samples)
        rounds = [sample_windows(validation, load, cfg, rng, date_max=cfg.train_end)
                  for _ in range(cfg.select_rounds)]
        cache.clear()
    best, best_fit, current, current_fit, hist = evolve(name, train, cfg, rng, logs.append)
    cur = [fitness(name, current, r, cfg) for r in rounds]
    cand = [fitness(name, best, r, cfg) for r in rounds]
    wins = int(sum(c > k for c, k in zip(cand, cur)))
    adopt = (best != current and np.median(cand) > np.median(cur) and wins > len(rounds) / 2
             and np.median(cand) > PENALTY / 2)   # el candidato no puede seguir penalizado por pocas operaciones
    if adopt and not dry_run:
        update_cfg_values(HERE / name / "variables.cfg", best)
    return {"algorithm": name, "adopted": bool(adopt), "seed": seed,
            "train_fitness_current": current_fit, "train_fitness_candidate": best_fit,
            "select_median_current": float(np.median(cur)), "select_median_candidate": float(np.median(cand)),
            "select_wins": wins, "rounds": len(rounds), "current": current, "candidate": best,
            "seconds": round(time.time() - t0, 1)}


@functools.lru_cache(maxsize=1)
def _symbols_cached(db_path: str):
    with StockDB(db_path) as db:
        return tuple(db.symbols())


def _symbols(cfg: GAConfig) -> List[str]:
    return list(_symbols_cached(cfg.db_path))


def _run(args):
    return tune_one(*args)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("algorithms", nargs="*", help="por defecto, todos")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true", help="no modifica variables.cfg")
    ap.add_argument("--set", nargs="*", default=[], metavar="clave=valor", help="sobrescribe genetic.cfg")
    a = ap.parse_args()
    cfg = load_ga_config(**{k: ast.literal_eval(v) for k, v in (s.split("=", 1) for s in a.set)})
    names = a.algorithms or discover_all()
    cfgd = dict(vars(cfg))
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        results = []
        for r in ex.map(_run, [(n, cfgd, a.dry_run) for n in names]):
            results.append(r)
            tag = "ADOPTADO " if r["adopted"] else "se conserva"
            print(f"{r['algorithm']:<17} {tag}  selección (mediana): actual {r['select_median_current']:6.2f} -> "
                  f"candidato {r['select_median_candidate']:6.2f}  (gana {r['select_wins']}/{r['rounds']})  "
                  f"[{r['seconds']} s]", flush=True)
    out = Path("output"); out.mkdir(exist_ok=True)
    (out / "tune_results.json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\n{sum(r['adopted'] for r in results)}/{len(results)} adoptados. "
          f"Detalle en output/tune_results.json  [{time.time() - t0:.0f} s]")


if __name__ == "__main__":
    main()
