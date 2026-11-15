"""Almacenamiento en SQLite (stdlib, funciona igual en Google Colab)."""
from __future__ import annotations

import re
import sqlite3
from typing import Iterable, List, Optional

import pandas as pd

PRICE_COLS = ["open", "high", "low", "close", "adj_close", "volume"]
KEYS = ["symbol", "interval", "date"]
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class StockDB:
    """Dos tablas: `prices` (OHLCV) e `indicators` (columnas dinámicas).

    Ambas con clave primaria (symbol, interval, date). Pensado para usarse
    como context manager o llamando a `close()`.
    """

    def __init__(self, path: str = "stocks.db"):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self.conn.close()

    def _create(self):
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS prices (
                symbol TEXT NOT NULL, interval TEXT NOT NULL, date TEXT NOT NULL,
                open REAL, high REAL, low REAL, close REAL, adj_close REAL, volume REAL,
                PRIMARY KEY (symbol, interval, date))"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS indicators (
                symbol TEXT NOT NULL, interval TEXT NOT NULL, date TEXT NOT NULL,
                PRIMARY KEY (symbol, interval, date))"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS symbol_info (
                symbol TEXT PRIMARY KEY, category TEXT NOT NULL, description TEXT)"""
        )
        self.conn.commit()
        self._market_cache: Optional[pd.DataFrame] = None

    # ---------- helpers ----------
    @staticmethod
    def _prep(df: pd.DataFrame, interval: str) -> pd.DataFrame:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        df["interval"] = interval
        return df

    def _columns(self, table: str) -> List[str]:
        return [r[1] for r in self.conn.execute(f"PRAGMA table_info({table})")]

    def _upsert(self, table: str, df: pd.DataFrame, cols: List[str]):
        cols = KEYS + [c for c in cols if c not in KEYS]
        updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c not in KEYS)
        sql = (f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))}) "
               f"ON CONFLICT(symbol, interval, date) DO UPDATE SET {updates}")
        data = df[cols].astype(object).where(df[cols].notna(), None)
        with self.conn:
            self.conn.executemany(sql, data.itertuples(index=False, name=None))

    # ---------- escritura ----------
    def save_prices(self, df: pd.DataFrame, interval: str = "1d") -> int:
        if df.empty:
            return 0
        df = self._prep(df, interval)
        self._upsert("prices", df, PRICE_COLS)
        return len(df)

    def save_indicators(self, df: pd.DataFrame, interval: str = "1d") -> int:
        """Guarda las columnas que no son OHLCV como indicadores."""
        if df.empty:
            return 0
        df = self._prep(df, interval)
        ind_cols = [c for c in df.columns if c not in KEYS + PRICE_COLS]
        if not ind_cols:
            return 0
        for c in ind_cols:
            if not _IDENT.match(c):
                raise ValueError(f"Nombre de columna no válido: {c!r}")
        existing = set(self._columns("indicators"))
        with self.conn:
            for c in ind_cols:
                if c not in existing:
                    self.conn.execute(f"ALTER TABLE indicators ADD COLUMN {c} REAL")
        self._upsert("indicators", df, ind_cols)
        return len(df)

    # ---------- lectura ----------
    def last_date(self, symbol: str, interval: str = "1d") -> Optional[pd.Timestamp]:
        row = self.conn.execute(
            "SELECT MAX(date) FROM prices WHERE symbol=? AND interval=?",
            (symbol.upper(), interval)).fetchone()
        return pd.Timestamp(row[0]) if row and row[0] else None

    def first_date(self, symbol: str, interval: str = "1d") -> Optional[pd.Timestamp]:
        row = self.conn.execute(
            "SELECT MIN(date) FROM prices WHERE symbol=? AND interval=?",
            (symbol.upper(), interval)).fetchone()
        return pd.Timestamp(row[0]) if row and row[0] else None

    def register_symbols(self, rows: Iterable[tuple]) -> None:
        """Registra (símbolo, categoría, descripción). Las categorías de mercado (índices, ETFs...)
        quedan fuera de `symbols()`, que es el universo de acciones."""
        with self.conn:
            self.conn.executemany(
                "INSERT INTO symbol_info (symbol, category, description) VALUES (?, ?, ?) "
                "ON CONFLICT(symbol) DO UPDATE SET category=excluded.category, description=excluded.description",
                [(s.upper(), c, d) for s, c, d in rows])
        self._market_cache = None

    def symbols(self, include_market: bool = False) -> List[str]:
        """Símbolos con precios. Por defecto solo acciones (excluye índices/ETFs registrados)."""
        sql = "SELECT DISTINCT symbol FROM prices"
        if not include_market:
            sql += " WHERE symbol NOT IN (SELECT symbol FROM symbol_info WHERE category != 'stock')"
        return [r[0] for r in self.conn.execute(sql + " ORDER BY 1")]

    def market_symbols(self, category: Optional[str] = None) -> List[str]:
        sql, params = "SELECT symbol FROM symbol_info WHERE category != 'stock'", []
        if category:
            sql += " AND category = ?"; params.append(category)
        have = {r[0] for r in self.conn.execute("SELECT DISTINCT symbol FROM prices")}
        return [r[0] for r in self.conn.execute(sql + " ORDER BY category, symbol", params) if r[0] in have]

    def has_market(self) -> bool:
        return bool(self.market_symbols())

    def market_features(self, refresh: bool = False) -> pd.DataFrame:
        """Variables `mkt_*` (ver ticker2db.market). Se calculan una vez y se guardan en memoria."""
        if self._market_cache is None or refresh:
            from .market import market_features
            self._market_cache = market_features(self)
        return self._market_cache

    def load(
        self,
        symbols: Optional[Iterable[str]] = None,
        interval: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
        with_indicators: bool = True,
        with_market: bool = False,
    ) -> pd.DataFrame:
        """Devuelve precios (+ indicadores) como DataFrame con `date` datetime.

        `with_market=True` añade las columnas `mkt_*` (VIX, DXY, tasas, S&P 500, crédito...) con el
        valor del mismo día o, si ese día no hubo dato, el último disponible (máx. 5 días).
        """
        sql = "SELECT p.*"
        if with_indicators:
            ind = [c for c in self._columns("indicators") if c not in KEYS]
            if ind:
                sql += ", " + ", ".join(f"i.{c}" for c in ind)
        sql += " FROM prices p"
        if with_indicators:
            sql += (" LEFT JOIN indicators i ON i.symbol=p.symbol "
                    "AND i.interval=p.interval AND i.date=p.date")
        where, params = ["p.interval=?"], [interval]
        if symbols is not None:
            syms = [s.upper() for s in ([symbols] if isinstance(symbols, str) else symbols)]
            where.append(f"p.symbol IN ({', '.join('?' * len(syms))})")
            params += syms
        if start:
            where.append("p.date>=?"); params.append(pd.Timestamp(start).strftime("%Y-%m-%d %H:%M:%S"))
        if end:
            where.append("p.date<=?"); params.append(pd.Timestamp(end).strftime("%Y-%m-%d %H:%M:%S"))
        sql += " WHERE " + " AND ".join(where) + " ORDER BY p.symbol, p.date"
        df = pd.read_sql_query(sql, self.conn, params=params)
        df["date"] = pd.to_datetime(df["date"])
        if with_market and not df.empty:
            mf = self.market_features()
            if not mf.empty:
                idx = mf.index.union(pd.DatetimeIndex(df["date"].unique()))
                aligned = mf.reindex(idx).ffill(limit=5).reindex(pd.DatetimeIndex(df["date"]))
                aligned.index = df.index
                df = pd.concat([df, aligned], axis=1)
        return df
