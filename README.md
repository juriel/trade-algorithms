# trade-algorithms

Descarga de acciones con **yfinance**, cálculo de indicadores técnicos con **TA-Lib**, almacenamiento en
**SQLite** (portable a Google Colab) y un banco de pruebas para **algoritmos de inversión** con backtest,
torneo entre algoritmos, optimización genética y análisis de operaciones.

> Proyecto de investigación y aprendizaje. Nada de lo que contiene es asesoría financiera ni garantiza
> rentabilidad: en las pruebas realizadas **ningún algoritmo supera a comprar y mantener** (ver [Resultados](#resultados-y-límites)).

## Estructura

```
ticker2db/        librería de datos: descarga, indicadores, SQLite, S&P 500 y datos de mercado
algorithms/       motor de backtest y algoritmos (una carpeta por algoritmo, con su variables.cfg)
  engine.py         motor de backtest
  compete.py        torneo entre algoritmos
  genetic.py        algoritmo genético para optimizar variables
  tune.py           afinado de variables.cfg con selección fuera de muestra
  analyze.py        análisis de operaciones (motivos de salida, año, indicadores)
  features.py       indicadores auxiliares (IBS, RSI(2), régimen de ATR, ...)
  ANALISIS*.md      análisis e investigación (leer para entender el porqué de cada versión)
tests/            pruebas (sin red)
output/           resultados generados (torneos, afinado, sp500.xlsx)
data/stocks.db    base de datos (NO está en el repositorio: es demasiado grande, ver más abajo)
```

## Instalación

Requiere Python ≥ 3.9. TA-Lib ≥ 0.6 trae binarios en PyPI.

```bash
git clone git@github.com:juriel/trade-algorithms.git && cd trade-algorithms
pip install -e . pytest
pytest                      # pruebas offline
```

Los comandos `python -m algorithms.*` se ejecutan desde la raíz del repositorio (el paquete `algorithms`
no se instala con `pip`). En Colab: clonar el repo, `pip install -e .` y trabajar desde esa carpeta;
guarda la base de datos en Drive para que persista entre sesiones (no he probado esto en Colab).

## `ticker2db`: datos

```python
from ticker2db import update_symbols, StockDB, get_sp500_weights, update_market, update_candles

# 1) Acciones: descarga incremental + indicadores + SQLite
update_symbols(["AAPL", "NVDA", "GOOGL"], db_path="data/stocks.db", start="1900-01-01")

# 2) Leer precios + indicadores (con variables de mercado opcionales)
with StockDB("data/stocks.db") as db:
    df = db.load("AAPL", start="2020-01-01", with_market=True)

# 3) Componentes del S&P 500 con su peso (holdings diarios de SPY, State Street)
sp = get_sp500_weights()            # company, symbol, weight (%), yf_symbol

# 4) Índices, VIX, DXY, tasas y ETFs
update_market("data/stocks.db")

# 5) Patrones de velas de TA-Lib (61 patrones CDL*), calculados sobre los precios ya guardados
update_candles("data/stocks.db")                       # o patterns=COMMON_PATTERNS para un subconjunto
with StockDB("data/stocks.db") as db:
    df = db.load("AAPL", with_candles=True)            # columnas cdl_engulfing, cdl_hammer, ...
```

- `update_symbols` solo descarga lo posterior a la última fecha guardada; si `start` es anterior al primer dato
  guardado, vuelve a descargar todo. `start="1900-01-01"` trae todo el histórico que ofrece Yahoo.
- **Indicadores por defecto:** SMA 20/50/200, EMA 12/26, RSI, MACD, Bollinger, ATR, ADX, Stoch, CCI, OBV, MFI
  (personalizables: lista de `("FUNCION_TALIB", {params})`). En series sin volumen (VIX) se omiten OBV y MFI.
- **Tablas SQLite:** `prices` (OHLCV), `indicators` (columnas dinámicas), `candles` (patrones de velas, opcional) y
  `symbol_info` (registro de símbolos de mercado). Clave `(symbol, interval, date)`. `StockDB.symbols()` devuelve solo acciones;
  `symbols(include_market=True)` incluye índices y ETFs.
- **`get_sp500_weights`** usa los holdings de SPY (descarga libre; los pesos suman ~99,9%). La versión de slickcharts
  (`get_sp500_weights_slickcharts(path=...)`) necesita un HTML guardado a mano: el sitio bloquea peticiones automáticas.
- **Datos de mercado** (`ticker2db/market.py`): ~60 símbolos (^VIX y variantes, DX-Y.NYB, ^GSPC/^NDX/^RUT, tasas
  ^IRX/^TNX, oro, petróleo, ETFs de sectores, bonos y regiones). `with_market=True` añade columnas `mkt_*`
  (VIX, VIX/VIX3M, DXY, curva de tasas, S&P 500 sobre SMA200, drawdown, crédito HYG/LQD, defensivos vs. cíclicos,
  amplitud del mercado). Ver `ticker2db.FEATURE_DOC`. Están calculadas con datos hasta el cierre de cada día.

- **Patrones de velas** (`ticker2db/candles.py`): cada patrón vale `+100` (alcista), `-100` (bajista) o `0`
  (algunos usan `±200`); los doji y similares (`NEUTRAL_PATTERNS`) valen siempre `+100` aunque sean de indecisión, no
  alcistas; columnas `cdl_<nombre>` (p.ej. `cdl_engulfing`, `cdl_3whitesoldiers`). Solo usan velas
  hasta ese día. `add_candle_patterns(df, ["ENGULFING", "HAMMER"])` los calcula sobre un DataFrame sin base de datos;
  `candle_summary(df)` resume cuántos patrones alcistas/bajistas hay por día; `pattern_info()` lista los 61 con su
  nombre; `COMMON_PATTERNS` es un subconjunto de 26 populares. Se guardan en la tabla `candles` (opcional,
  `update_candles`, o `update_symbols(..., candles=True)`); `load(with_candles=True)` los une a precios.
  Un algoritmo los usa añadiendo la columna (p.ej. `"cdl_hammer"`) a `requires`: los cargadores solo los cargan si algún
  algoritmo los pide.

### Generar `data/stocks.db`

La base (cientos de MB con 200 acciones desde 1900) no se versiona. Para recrearla:

```python
from ticker2db import get_sp500_weights, update_symbols, update_market, update_candles
syms = get_sp500_weights().head(200)["yf_symbol"].tolist()
update_symbols(syms, db_path="data/stocks.db", start="1900-01-01")   # ~8 min
update_market("data/stocks.db")
update_candles("data/stocks.db")                                      # opcional: patrones de velas
```

## `algorithms`: backtest

**Reglas del mercado simulado** (largos, un símbolo, una posición a la vez):

- **Compra:** solo a la apertura del día, condicionada por datos del día anterior.
- **Venta:** a la apertura (por señal, por `max_hold_days` o por `stop_pct`/stop en ATR cuando el cierre de ayer
  cayó bajo el nivel) o al cumplir la meta (`target_pct` o múltiplo del ATR), que se ejecuta como orden límite.
- Sin lookahead: las señales calculadas al cierre del día *t* se ejecutan en la apertura de *t+1*.
- Costos configurables (`commission_pct`, `slippage_pct`).

```bash
python -m algorithms.run algorithm03c AAPL --start 2010-01-01
python -m algorithms.run algorithm02_v1 NVDA --set target_pct=0.2 adx_min=25
```

### Variables en `variables.cfg`

Cada algoritmo tiene su carpeta `algorithms/<nombre>/` con `algorithm.py` (reglas) y `variables.cfg` (variables
editables, formato INI con comentarios; valores numéricos, `True/False` o `None`). Prioridad: argumentos >
`variables.cfg` > valores de respaldo del dataclass. Una clave desconocida da error.

### Algoritmos

| Familia | Idea | Variantes |
|---|---|---|
| `01` | Rebote por sobreventa (RSI) | `01`, `01a`, `01b`, `01c` |
| `02` | Seguimiento de tendencia | `02`, `02a` (EMAs), `02b` (ruptura), `02c` (retroceso) y `_v1`, `_v2` |
| `03` | Retorno a la media con Bollinger | `03`, `03a` (RSI), `03b` (CCI), `03c` (MFI) y `_v1`, `_v2` |
| `_r1`, `_r2` | Variaciones basadas en investigación en Internet | sobre los 6 mejores |
| `_m1`, `_m2` | Filtros con variables de mercado (VIX, amplitud, S&P 500, crédito, curva de tasas) | sobre los 6 mejores |

`_v1`/`_v2` son mejoras derivadas del análisis de operaciones; `_r1`/`_r2` incorporan ideas de la literatura
(RSI(2) de Connors, IBS, confirmación de giro, filtros de régimen, stops de tiempo/ATR).
Detalle y resultados: [`algorithms/ANALISIS.md`](algorithms/ANALISIS.md) y
[`algorithms/ANALISIS_INVESTIGACION.md`](algorithms/ANALISIS_INVESTIGACION.md) y
[`algorithms/ANALISIS_MERCADO.md`](algorithms/ANALISIS_MERCADO.md).

### Herramientas

```bash
python -m algorithms.compete --rounds 12 --seed 5 --group validation --period test   # torneo
python -m algorithms.analyze algorithm03c                                            # análisis de operaciones
python -m algorithms.genetic algorithm03 --set population=30 generations=20          # algoritmo genético
python -m algorithms.tune --dry-run                                                  # afinado (no escribe cfg)
```

- **Torneo:** todos los algoritmos y un benchmark *buy & hold* sobre las mismas acciones y periodos al azar
  (50 acciones × periodos de 300-600 barras, ver `algorithms/genetic.cfg`). Ranking por puesto medio entre rondas;
  se informan fitness (CAGR − ½·drawdown), CAGR, drawdown, exposición y `calmar`. `--group analysis|validation`
  usa mitades disjuntas de las acciones; `--period train|test` separa antes/después de 2020 (`genetic.cfg`).
- **Genético / afinado:** `tune` entrena el genético en un grupo de acciones, hace competir al candidato contra el
  `variables.cfg` actual en otras acciones y solo lo adopta si gana; reescribe los valores conservando comentarios.
  Los espacios de búsqueda están en `algorithms/gene_ranges.cfg` (o `genes.cfg` por algoritmo).
- Usar variables de mercado en un algoritmo: añadir la columna a `requires` y leer `df["mkt_vix"]` etc. (ver `features.stress_score`, `stress_expansion`, `healthy_bull`). `compete --since 1996-01-01` evita periodos sin datos de mercado.

### Resultados y límites

- Ninguno de los algoritmos supera a comprar y mantener en las pruebas; los de retorno a la media operan muy poco
  (≈1-3 % del tiempo en el mercado) y los de tendencia ganan con pocas operaciones grandes.
- La métrica de torneo actual (CAGR − ½·drawdown) **premia no operar**; por eso el afinado automático mejoró el
  fitness reduciendo exposición sin mejorar el CAGR. Considerar Calmar u otra métrica antes de reoptimizar.
- Las acciones son las 200 mayores del S&P 500 **de hoy** (sesgo de supervivencia) y la historia de mercado es la
  misma en validación y entrenamiento, aunque las acciones/periodos sean distintos.
- El motor simula una acción a la vez; un portafolio real invertiría en muchas simultáneamente.

## Pruebas

```bash
pytest          # 19 pruebas, todas offline (datos sintéticos)
```
