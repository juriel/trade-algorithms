"""Ejecuta un algoritmo sobre un símbolo de la base de datos.

Uso (desde la raíz del proyecto):
    python -m algorithms.run algorithm01 AAPL
    python -m algorithms.run algorithm02 NVDA --start 2015-01-01 --set target_pct=0.2 adx_min=25
"""
import argparse
import ast
import importlib

from ticker2db import StockDB

from .engine import backtest


def load_algorithm(name: str, **overrides):
    return importlib.import_module(f"algorithms.{name}").Algorithm(**overrides)


def run(name: str, symbol: str, db_path: str = "data/stocks.db",
        start=None, end=None, **overrides):
    algo = load_algorithm(name, **overrides)
    with StockDB(db_path) as db:
        df = db.load(symbol, start=start, end=end, with_market=db.has_market())
    if df.empty:
        raise SystemExit(f"{symbol} no está en {db_path}")
    return algo, backtest(algo, df)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("algorithm")
    ap.add_argument("symbol")
    ap.add_argument("--db", default="data/stocks.db")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--cfg", help="ruta a otro variables.cfg")
    ap.add_argument("--set", nargs="*", default=[], metavar="clave=valor",
                    help="sobrescribe variables de variables.cfg")
    a = ap.parse_args()
    over = {k: ast.literal_eval(v) for k, v in (s.split("=", 1) for s in a.set)}
    algo, res = run(a.algorithm, a.symbol.upper(), a.db, a.start, a.end, **({"cfg": a.cfg} if a.cfg else {}), **over)
    print(f"{algo.name}: {algo.description}\nParámetros: {algo.p}\n")
    print(res.summary())


if __name__ == "__main__":
    main()
