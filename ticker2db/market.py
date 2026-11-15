"""Datos de contexto de mercado: índices, VIX, DXY, tasas, ETFs y variables derivadas (`mkt_*`).

Los símbolos se descargan con `update_market()` y se guardan en la misma base de datos que las
acciones, registrados en la tabla `symbol_info` para que `StockDB.symbols()` (el universo de
acciones) no los mezcle. `market_features(db)` calcula las variables de régimen que se pueden
unir a cualquier acción con `StockDB.load(..., with_market=True)`.

Todas las variables se calculan con datos hasta el cierre de cada día (sin mirar al futuro).
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import talib

# categoría -> {símbolo de Yahoo Finance: descripción}
MARKET_SYMBOLS: Dict[str, Dict[str, str]] = {
    "indices": {
        "^GSPC": "S&P 500", "^NDX": "Nasdaq 100", "^DJI": "Dow Jones", "^RUT": "Russell 2000",
        "^IXIC": "Nasdaq Composite", "^NYA": "NYSE Composite",
    },
    "volatilidad": {
        "^VIX": "VIX (volatilidad implícita 30 días)", "^VIX9D": "VIX a 9 días", "^VIX3M": "VIX a 3 meses",
        "^VIX6M": "VIX a 6 meses", "^VVIX": "Volatilidad del VIX", "^VXN": "VIX del Nasdaq 100",
        "^SKEW": "Índice SKEW (riesgo de cola)",
    },
    "tasas": {
        "^IRX": "Letra del Tesoro 13 semanas", "^FVX": "Bono EE.UU. 5 años",
        "^TNX": "Bono EE.UU. 10 años", "^TYX": "Bono EE.UU. 30 años",
    },
    "divisas_materias": {
        "DX-Y.NYB": "Índice del dólar (DXY)", "EURUSD=X": "EUR/USD", "JPY=X": "USD/JPY",
        "GC=F": "Oro (futuro)", "CL=F": "Petróleo WTI (futuro)",
    },
    "indices_mundo": {
        "^STOXX50E": "Euro Stoxx 50", "^N225": "Nikkei 225", "^FTSE": "FTSE 100",
        "^GDAXI": "DAX", "^HSI": "Hang Seng",
    },
    "etf_indices": {
        "SPY": "SPDR S&P 500", "QQQ": "Invesco Nasdaq 100", "DIA": "SPDR Dow Jones",
        "IWM": "iShares Russell 2000", "MDY": "SPDR S&P 400 Mid Cap",
    },
    "etf_sectores": {
        "XLK": "Tecnología", "XLF": "Financiero", "XLE": "Energía", "XLV": "Salud",
        "XLY": "Consumo discrecional", "XLP": "Consumo básico", "XLI": "Industriales",
        "XLB": "Materiales", "XLU": "Servicios públicos", "XLRE": "Inmobiliario", "XLC": "Comunicaciones",
        "SMH": "Semiconductores", "IBB": "Biotecnología", "XBI": "Biotecnología (equiponderado)",
        "KRE": "Bancos regionales", "XRT": "Comercio minorista", "XHB": "Construcción de viviendas",
    },
    "etf_bonos": {
        "TLT": "Bonos Tesoro 20+ años", "IEF": "Bonos Tesoro 7-10 años", "SHY": "Bonos Tesoro 1-3 años",
        "HYG": "Bonos corporativos high yield", "LQD": "Bonos corporativos grado inversión",
        "TIP": "Bonos ligados a inflación",
    },
    "etf_materias_divisas": {
        "GLD": "Oro", "SLV": "Plata", "USO": "Petróleo", "UUP": "Dólar (Invesco DB)",
    },
    "etf_internacional": {
        "EFA": "Mercados desarrollados ex-EE.UU.", "EEM": "Mercados emergentes", "VNQ": "REIT EE.UU.",
    },
}


def market_symbols(categories: Optional[Iterable[str]] = None) -> List[Tuple[str, str, str]]:
    """Lista de (símbolo, categoría, descripción) de las categorías pedidas (por defecto, todas)."""
    cats = list(categories) if categories else list(MARKET_SYMBOLS)
    unknown = [c for c in cats if c not in MARKET_SYMBOLS]
    if unknown:
        raise ValueError(f"Categorías desconocidas: {unknown}. Disponibles: {list(MARKET_SYMBOLS)}")
    return [(s, c, d) for c in cats for s, d in MARKET_SYMBOLS[c].items()]


FEATURE_DOC = {
    "mkt_vix": "VIX (cierre)",
    "mkt_vix_chg5": "variación % del VIX en 5 días",
    "mkt_vix_ratio50": "VIX / su media de 50 días (>1,3 = estrés creciente)",
    "mkt_vix_pctrank": "percentil del VIX en el último año (0-100)",
    "mkt_vix_term": "VIX / VIX3M (>1 = backwardation, estrés agudo)",
    "mkt_dxy": "índice del dólar (cierre)",
    "mkt_dxy_ret20": "variación % del DXY en 20 días",
    "mkt_dxy_above_sma50": "1 si el DXY está sobre su media de 50 días",
    "mkt_tnx": "rendimiento del bono a 10 años (%)",
    "mkt_curve": "pendiente de la curva: 10 años - 13 semanas (puntos porcentuales)",
    "mkt_spx_ret20": "variación % del S&P 500 en 20 días",
    "mkt_spx_above_sma200": "1 si el S&P 500 está sobre su SMA200",
    "mkt_spx_dd252": "caída % del S&P 500 desde su máximo de 252 días",
    "mkt_spx_rsi14": "RSI(14) del S&P 500",
    "mkt_rut_rel20": "Russell 2000 menos S&P 500, variación % a 20 días (apetito por riesgo)",
    "mkt_credit_ret20": "variación % a 20 días de HYG/LQD (crédito riesgoso vs seguro)",
    "mkt_gold_ret20": "variación % del oro en 20 días",
    "mkt_oil_ret20": "variación % del petróleo en 20 días",
    "mkt_def_cyc_ret20": "sectores defensivos (XLP, XLU, XLV) menos cíclicos (XLK, XLY, XLF), % a 20 días",
    "mkt_breadth200": "% de las acciones de la base sobre su SMA200",
}


def _close(db, symbol: str) -> Optional[pd.Series]:
    df = db.load(symbol, with_indicators=False)
    if df.empty:
        return None
    return df.set_index("date")["close"].astype(float).replace(0, np.nan).dropna()


def _ret(s: pd.Series, n: int) -> pd.Series:
    return (s / s.shift(n) - 1) * 100


def _breadth(db) -> Optional[pd.Series]:
    syms = db.symbols()  # solo acciones
    if not syms or "sma_200" not in [r[1] for r in db.conn.execute("PRAGMA table_info(indicators)")]:
        return None
    q = ("SELECT p.date, AVG(CASE WHEN p.close > i.sma_200 THEN 100.0 ELSE 0 END) AS b, COUNT(*) AS n "
         "FROM prices p JOIN indicators i USING (symbol, interval, date) "
         f"WHERE p.interval='1d' AND i.sma_200 IS NOT NULL AND p.symbol IN ({','.join('?' * len(syms))}) "
         "GROUP BY p.date HAVING n >= 20 ORDER BY p.date")
    df = pd.read_sql_query(q, db.conn, params=syms)
    return None if df.empty else pd.Series(df["b"].to_numpy(), index=pd.to_datetime(df["date"]))


def market_features(db, breadth: bool = True) -> pd.DataFrame:
    """Variables `mkt_*` indexadas por fecha, según los símbolos de mercado disponibles en la BD."""
    c = {s: _close(db, s) for s in ("^VIX", "^VIX3M", "DX-Y.NYB", "^TNX", "^IRX", "^GSPC", "^RUT",
                                    "HYG", "LQD", "GC=F", "CL=F", "XLP", "XLU", "XLV", "XLK", "XLY", "XLF")}
    f: Dict[str, pd.Series] = {}
    vix = c["^VIX"]
    if vix is not None:
        f["mkt_vix"] = vix
        f["mkt_vix_chg5"] = _ret(vix, 5)
        f["mkt_vix_ratio50"] = vix / vix.rolling(50).mean()
        f["mkt_vix_pctrank"] = vix.rolling(252).apply(lambda x: (x <= x[-1]).mean() * 100, raw=True)
        if c["^VIX3M"] is not None:
            f["mkt_vix_term"] = vix / c["^VIX3M"].reindex(vix.index).ffill(limit=5)
    dxy = c["DX-Y.NYB"]
    if dxy is not None:
        f["mkt_dxy"] = dxy
        f["mkt_dxy_ret20"] = _ret(dxy, 20)
        f["mkt_dxy_above_sma50"] = (dxy > dxy.rolling(50).mean()).astype(float).where(dxy.rolling(50).mean().notna())
    if c["^TNX"] is not None:
        f["mkt_tnx"] = c["^TNX"]
        if c["^IRX"] is not None:
            f["mkt_curve"] = c["^TNX"] - c["^IRX"].reindex(c["^TNX"].index).ffill(limit=5)
    spx = c["^GSPC"]
    if spx is not None:
        sma200 = spx.rolling(200).mean()
        f["mkt_spx_ret20"] = _ret(spx, 20)
        f["mkt_spx_above_sma200"] = (spx > sma200).astype(float).where(sma200.notna())
        f["mkt_spx_dd252"] = (spx / spx.rolling(252, min_periods=20).max() - 1) * 100
        f["mkt_spx_rsi14"] = pd.Series(talib.RSI(spx.to_numpy(float), 14), index=spx.index)
        if c["^RUT"] is not None:
            f["mkt_rut_rel20"] = _ret(c["^RUT"], 20) - _ret(spx, 20).reindex(c["^RUT"].index)
    if c["HYG"] is not None and c["LQD"] is not None:
        ratio = (c["HYG"] / c["LQD"]).dropna()
        f["mkt_credit_ret20"] = _ret(ratio, 20)
    if c["GC=F"] is not None:
        f["mkt_gold_ret20"] = _ret(c["GC=F"], 20)
    if c["CL=F"] is not None:
        f["mkt_oil_ret20"] = _ret(c["CL=F"], 20)
    dfn, cyc = [c[s] for s in ("XLP", "XLU", "XLV")], [c[s] for s in ("XLK", "XLY", "XLF")]
    if all(x is not None for x in dfn + cyc):
        d = pd.concat([_ret(x, 20) for x in dfn], axis=1).mean(axis=1)
        y = pd.concat([_ret(x, 20) for x in cyc], axis=1).mean(axis=1)
        f["mkt_def_cyc_ret20"] = d - y
    if breadth:
        b = _breadth(db)
        if b is not None:
            f["mkt_breadth200"] = b
    if not f:
        return pd.DataFrame()
    out = pd.concat(f, axis=1).sort_index()
    out.index.name = "date"
    return out.replace([np.inf, -np.inf], np.nan)
