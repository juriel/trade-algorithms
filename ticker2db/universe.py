"""Composición del S&P 500 con pesos.

Fuente principal: holdings diarios del ETF SPY (State Street), archivo oficial
de descarga libre. Alternativa: slickcharts.com (bloquea peticiones automáticas).
"""
from __future__ import annotations

import io
from typing import Optional

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
