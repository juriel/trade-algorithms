"""Composición del S&P 500 con pesos.

Fuente principal: holdings diarios del ETF SPY (State Street), archivo oficial
de descarga libre. Alternativa: slickcharts.com (bloquea peticiones automáticas).
"""
from __future__ import annotations

import io
from typing import Iterable, List, Optional

import pandas as pd
import requests

SLICKCHARTS_URL = "https://www.slickcharts.com/sp500"
SPY_HOLDINGS_URL = ("https://www.ssga.com/us/en/intermediary/etfs/library-content/"
                    "products/fund-data/etfs/us/holdings-daily-us-en-spy.xlsx")


def parse_sp500_html(html: str) -> pd.DataFrame:
    """Extrae la tabla de componentes de la página de slickcharts."""
    for table in pd.read_html(io.StringIO(html)):
        cols = {str(c).strip().lower(): c for c in table.columns}
        if {"company", "symbol", "weight"} <= cols.keys():
            df = table[[cols["company"], cols["symbol"], cols["weight"]]].copy()
            df.columns = ["company", "symbol", "weight"]
            df["weight"] = pd.to_numeric(
                df["weight"].astype(str).str.replace("%", "", regex=False).str.strip(),
                errors="coerce")
            df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
            # yfinance usa guion en vez de punto (BRK.B -> BRK-B)
            df["yf_symbol"] = df["symbol"].str.replace(".", "-", regex=False)
            return df.dropna(subset=["weight"]).reset_index(drop=True)
    raise ValueError("No se encontró la tabla de componentes en el HTML")


def get_sp500_weights_slickcharts(html: Optional[str] = None, path: Optional[str] = None,
                      timeout: int = 30) -> pd.DataFrame:
    """Devuelve los componentes del S&P 500 con su peso (%).

    Columnas: company, symbol, weight (porcentaje), yf_symbol (para yfinance).
    Si se pasa `html` o `path` (página guardada desde el navegador) no se hace
    ninguna petición. slickcharts suele responder 403 a peticiones automáticas;
    en ese caso lanza `requests.HTTPError`.
    """
    if html is None and path is not None:
        with open(path, encoding="utf-8") as f:
            html = f.read()
    if html is None:
        resp = requests.get(SLICKCHARTS_URL, timeout=timeout)
        resp.raise_for_status()
        html = resp.text
    return parse_sp500_html(html)


def get_sp500_weights(path: Optional[str] = None, timeout: int = 60) -> pd.DataFrame:
    """Componentes del S&P 500 con su peso (%), según los holdings diarios de SPY.

    Columnas: company, symbol, weight (porcentaje), yf_symbol (para yfinance).
    `df.attrs["as_of"]` guarda la fecha de los datos. Si se pasa `path` se lee
    un .xlsx ya descargado en vez de bajarlo.
    """
    if path is None:
        resp = requests.get(SPY_HOLDINGS_URL, timeout=timeout)
        resp.raise_for_status()
        source = io.BytesIO(resp.content)
    else:
        source = path
    raw = pd.read_excel(source, header=None)

    as_of = None
    hdr = None
    for i, row in raw.iterrows():
        first = str(row[0]).strip()
        if first.lower() == "holdings:":
            as_of = pd.to_datetime(str(row[1]).replace("As of", "").strip(), errors="coerce")
        if first == "Name":
            hdr = i
            break
    if hdr is None:
        raise ValueError("No se encontró la cabecera de la tabla de holdings")

    df = raw.iloc[hdr + 1:, :].copy()
    df.columns = [str(c).strip() for c in raw.iloc[hdr]]
    df = df[["Name", "Ticker", "Weight"]]
    df.columns = ["company", "symbol", "weight"]
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
    # fuera efectivo/filas vacías o de pie de página
    df = df[df["weight"].notna() & ~df["symbol"].isin(["", "-", "NAN", "USD"])]
    df["yf_symbol"] = df["symbol"].str.replace(".", "-", regex=False)
    df = df.reset_index(drop=True)
    df.attrs["as_of"] = as_of
    return df


# ----------------------------- ampliar el universo -----------------------------
import re
import random

import numpy as np

_TICKER = re.compile(r"^[A-Z]{1,4}$")   # 4 letras máx.: evita preferentes/series (p.ej. SLMBP)
_FUND_NAME = re.compile(r"\b(fund|trust|etf|income|strategy|portfolio|enhanced|tax-managed|buy-write|floating|preferred|series)\b", re.I)


def total_returns(prices: pd.DataFrame, min_obs: int) -> pd.Series:
    """Retorno total (último / primer precio - 1) por columna; descarta las de menos de `min_obs` datos."""
    out = {}
    for c in prices.columns:
        s = prices[c].dropna()
        if len(s) >= min_obs:
            out[c] = float(s.iloc[-1] / s.iloc[0] - 1)
    return pd.Series(out, dtype=float)


def _download_close(symbols: List[str], **kwargs) -> pd.DataFrame:
    import yfinance as yf
    raw = yf.download(symbols, auto_adjust=True, progress=False, threads=True, **kwargs)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]].rename(columns={"Close": symbols[0]})
    return close


def worst_performers(symbols: Iterable[str], n: int = 100, years: int = 5, batch: int = 100) -> pd.DataFrame:
    """Las `n` acciones de peor retorno total (con dividendos) en los últimos `years` años.

    Descarga solo precios de cierre para ordenar (no toca la base de datos). Se descartan las que no tienen
    al menos ~90% de las jornadas del periodo (spin-offs recientes, símbolos inválidos).
    Devuelve symbol, retorno_pct y jornadas, de peor a mejor.
    """
    symbols = list(dict.fromkeys(symbols))
    parts = []
    for i in range(0, len(symbols), batch):
        parts.append(_download_close(symbols[i:i + batch], period=f"{years}y", interval="1d"))
    prices = pd.concat(parts, axis=1)
    min_obs = int(252 * years * 0.9)
    r = total_returns(prices, min_obs).sort_values()
    out = pd.DataFrame({"symbol": r.index, "retorno_pct": (r.values * 100).round(2)})
    out["jornadas"] = [int(prices[s].notna().sum()) for s in out["symbol"]]
    return out.head(n).reset_index(drop=True)


def russell_proxy(n: int = 20, seed: int = 0, min_cap: float = 3e8, max_cap: float = 5e9,
                  min_bars: int = 1000) -> pd.DataFrame:
    """~`n` acciones de pequeña capitalización de EE.UU. como APROXIMACIÓN del Russell 2000.

    No es la lista oficial del Russell (iShares/FTSE Russell no ofrecen descarga libre): se usa el screener de
    Yahoo Finance con acciones de NYSE/Nasdaq y capitalización entre `min_cap` y `max_cap`, se sortean con `seed`
    y se exigen `min_bars` jornadas de historia (para poder sortear periodos de 300-600 jornadas).
    Devuelve symbol, name, market_cap y exchange. OJO: el screener cambia entre llamadas (las capitalizaciones se
    mueven), así que la lista NO es reproducible con la misma semilla; guarda el resultado (p.ej. en un CSV).
    """
    import yfinance as yf
    q = yf.EquityQuery("and", [yf.EquityQuery("eq", ["region", "us"]),
                               yf.EquityQuery("is-in", ["exchange", "NMS", "NYQ"]),
                               yf.EquityQuery("btwn", ["intradaymarketcap", min_cap, max_cap])])
    quotes, offset = [], 0
    while True:
        page = yf.screen(q, offset=offset, size=250, sortField="intradaymarketcap", sortAsc=False)["quotes"]
        quotes += page
        if len(page) < 250 or offset > 4000:
            break
        offset += 250
    cands = [x for x in quotes if _TICKER.match(x.get("symbol", "")) and x.get("quoteType") == "EQUITY"
             and x.get("shortName") and not _FUND_NAME.search(x["shortName"])]   # sin fondos cerrados (sin nombre / "Fund", "Trust"...)
    random.Random(seed).shuffle(cands)
    chosen = []
    for i in range(0, len(cands), 40):
        grp = cands[i:i + 40]
        close = _download_close([x["symbol"] for x in grp], period="max", interval="1d")
        for x in grp:
            if x["symbol"] in close and close[x["symbol"]].notna().sum() >= min_bars:
                chosen.append(x)
                if len(chosen) == n:
                    break
        if len(chosen) == n:
            break
    return pd.DataFrame({"symbol": [x["symbol"] for x in chosen], "name": [x.get("shortName") for x in chosen],
                         "market_cap": [x.get("marketCap") for x in chosen],
                         "exchange": [x.get("fullExchangeName") for x in chosen]})
