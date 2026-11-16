# trade-algorithms

Descarga de acciones con **yfinance**, cálculo de indicadores técnicos y patrones de velas con **TA-Lib**, almacenamiento en
**SQLite** (portable a Google Colab) y un banco de pruebas para **algoritmos de inversión**: backtest de una acción y de
carteras, torneos con estadística (alpha, intervalos de confianza, corrección por múltiples comparaciones), optimización
walk-forward, análisis de operaciones, señales para la próxima apertura y un filtro con aprendizaje automático (en desarrollo).

> Proyecto de investigación y aprendizaje. Nada de lo que contiene es asesoría financiera ni garantiza
> rentabilidad: en las pruebas realizadas **ningún algoritmo supera a comprar y mantener en CAGR** (ver [Resultados](#resultados-y-límites)).

## Estructura

```
ticker2db/          librería de datos: descarga, indicadores, velas, SQLite, S&P 500, universo y datos de mercado
algorithms/         motor de backtest y algoritmos (una carpeta por algoritmo, con su variables.cfg)
  engine.py           backtest de UNA acción (efectivo con interés, metas, stops, alpha de timing)
  portfolio.py        backtest de CARTERA: 20 acciones con capital compartido (portfolio.cfg)
  compete.py          torneo, una acción por prueba
  pcompete.py         torneo de carteras (el principal)
  metrics.py          alpha de timing, bootstrap, p-valores, Benjamini-Hochberg
  walkforward.py      optimización robusta de variables (walk-forward, meseta, Optuna; walkforward.cfg)
  genetic.py / tune.py   algoritmo genético y afinado (históricos; ver Resultados)
  analyze.py          análisis de operaciones por motivo de salida, año, indicadores y variables de la señal
  volume_study.py     estudio de eventos del volumen con descubrimiento y confirmación
  ml.py               meta-etiquetado con gradient boosting (en desarrollo)
  signals.py          señales de compra para la próxima apertura sobre todo el S&P 500
  features.py        indicadores auxiliares (IBS, RSI(2), volumen, régimen de ATR, filtros de mercado...)
  ANALISIS*.md        análisis e investigación (leer para entender el porqué de cada versión)
tests/              pruebas (sin red)
output/             resultados generados (torneos, afinado, señales, sp500.xlsx)
data/               stocks.db y sp500_extra.db: NO están en el repositorio (demasiado grandes, ver más abajo)
```

## Instalación

Requiere Python ≥ 3.9. TA-Lib ≥ 0.6 trae binarios en PyPI.

```bash
git clone git@github.com:juriel/trade-algorithms.git && cd trade-algorithms
pip install -e ".[ml]" pytest       # [ml] = scikit-learn, joblib, optuna (walk-forward y meta-etiquetado)
pytest                              # 36 pruebas offline
```

Los comandos `python -m algorithms.*` se ejecutan desde la raíz del repositorio (el paquete `algorithms`
no se instala con `pip`). En Colab: clonar el repo, `pip install -e .` y trabajar desde esa carpeta;
guarda la base de datos en Drive para que persista entre sesiones (no he probado esto en Colab).

## `ticker2db`: datos

```python
from ticker2db import (update_symbols, StockDB, get_sp500_weights, update_market, update_candles,
                       worst_performers, russell_proxy)

# 1) Acciones: descarga incremental + indicadores + SQLite
update_symbols(["AAPL", "NVDA", "GOOGL"], db_path="data/stocks.db", start="1900-01-01")

# 2) Leer precios + indicadores (con variables de mercado y velas opcionales)
with StockDB("data/stocks.db") as db:
    df = db.load("AAPL", start="2020-01-01", with_market=True, with_candles=True)

# 3) Componentes del S&P 500 con su peso (holdings diarios de SPY, State Street)
sp = get_sp500_weights()            # company, symbol, weight (%), yf_symbol

# 4) Índices, VIX, DXY, tasas y ETFs
update_market("data/stocks.db")

# 5) Patrones de velas de TA-Lib (61 patrones CDL*), calculados sobre los precios ya guardados
update_candles("data/stocks.db")                       # o patterns=COMMON_PATTERNS para un subconjunto
```

- `update_symbols` solo descarga lo posterior a la última fecha guardada; si `start` es anterior al primer dato
  guardado, vuelve a descargar todo. `start="1900-01-01"` trae todo el histórico que ofrece Yahoo.
- **Indicadores por defecto:** SMA 20/50/200, EMA 12/26, RSI, MACD, Bollinger, ATR, ADX, Stoch, CCI, OBV, MFI
  (personalizables: lista de `("FUNCION_TALIB", {params})`). En series sin volumen (VIX) se omiten OBV y MFI.
- **Tablas SQLite:** `prices` (OHLCV), `indicators` (columnas dinámicas), `candles` (patrones de velas, opcional) y
  `symbol_info` (registro de símbolos). Clave `(symbol, interval, date)`. `StockDB.symbols()` devuelve solo acciones;
  `symbols(include_market=True)` incluye índices y ETFs.
- **`get_sp500_weights`** usa los holdings de SPY (descarga libre; los pesos suman ~99,9%). La versión de slickcharts
  (`get_sp500_weights_slickcharts(path=...)`) necesita un HTML guardado a mano: el sitio bloquea peticiones automáticas.
- **Datos de mercado** (`ticker2db/market.py`): 62 símbolos (^VIX y variantes, DX-Y.NYB, ^GSPC/^NDX/^RUT, tasas
  ^IRX/^TNX, oro, petróleo, ETFs de sectores, bonos y regiones). `with_market=True` añade las columnas `mkt_*` (VIX, DXY,
  curva de tasas, S&P 500 sobre SMA200, drawdown, crédito HYG/LQD, defensivos vs. cíclicos, amplitud del mercado,
  tasa libre de riesgo `mkt_irx`). Ver `ticker2db.FEATURE_DOC`. Calculadas con datos hasta el cierre de cada día.
- **Patrones de velas** (`ticker2db/candles.py`): cada patrón vale `+100` (alcista), `-100` (bajista) o `0`; los doji y
  similares (`NEUTRAL_PATTERNS`) valen siempre `+100` aunque sean de indecisión, no alcistas. Columnas `cdl_<nombre>`.
  `add_candle_patterns`, `candle_summary`, `pattern_info`, `COMMON_PATTERNS`. Un algoritmo los usa añadiendo la columna
  (p.ej. `"cdl_hammer"`) a `requires`; los cargadores solo los cargan si algún algoritmo los pide.
- **Universo** (`ticker2db/universe.py`): `worst_performers(símbolos, n, años)` (peor retorno total) y `russell_proxy(n)`
  (small caps de EE.UU. del screener de Yahoo; **no es la lista oficial del Russell 2000**, el screener cambia entre llamadas).

### Generar `data/stocks.db`

La base (≈1,6 GB, 514 acciones desde 1900 + 62 símbolos de mercado + velas) no se versiona. Para recrearla:

```python
from ticker2db import get_sp500_weights, update_symbols, update_market, update_candles, worst_performers
sp = get_sp500_weights()
top = sp.head(200)["yf_symbol"].tolist()                                    # 200 de mayor peso
worst = worst_performers(sp.iloc[200:]["yf_symbol"].tolist(), n=100, years=5)["symbol"].tolist()   # 100 de peor rendimiento
update_symbols(top + worst, db_path="data/stocks.db", start="1900-01-01")   # ~15 min
update_market("data/stocks.db")
update_candles("data/stocks.db")                                            # opcional: patrones de velas
```

La lista de las 20 small caps (proxy del Russell), las 100 peores y 194 small caps del Russell aportadas por el usuario (grupo
`russell_usuario`; `AVTE` sin datos en Yahoo) quedó fijada en `output/universe_extra.csv`. El reparto análisis/validación está
congelado en `algorithms/split_assignment.csv`: añadir acciones no mueve las existentes de grupo (las nuevas se asignan por crc32 del símbolo).

## `algorithms`: backtest

**Reglas del mercado simulado** (largos; una posición por acción):

- **Compra:** solo a la apertura del día, condicionada por datos del día anterior.
- **Venta:** a la apertura (por señal, por `max_hold_days` o por `stop_pct`/stop en ATR cuando el cierre de ayer
  cayó bajo el nivel) o al cumplir la meta (`target_pct` o múltiplo del ATR), que se ejecuta como orden límite.
- **Tamaño** (solo carteras): `Algorithm.size_series` da un multiplicador por señal.
- **Efectivo:** rinde la letra a 13 semanas (`mkt_irx` de ayer) si la base tiene datos de mercado.
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

| Familia | Idea |
|---|---|
| `01`, `01a`-`01c` | Rebote por sobreventa (RSI, Estocástico, MACD) |
| `02`, `02a`-`02c` (+ `_v1`, `_v2`) | Seguimiento de tendencia (medias, EMAs, ruptura, retroceso) |
| `03`, `03a`-`03c` (+ `_v1`, `_v2`) | Retorno a la media con Bollinger (RSI, CCI, MFI) |
| `_r1`, `_r2` | Variaciones basadas en investigación en Internet (RSI(2), IBS, confirmación, régimen) |
| `_m1`, `_m2` | Filtros con variables de mercado (VIX, amplitud, S&P 500, crédito, curva) |
| `creative01`…`06` | Ideas nuevas: clímax vendedor, giro del VIX, compresión y ruptura, líderes en retroceso, interruptor macro, fin de mes |
| `_i1`, `_i2` | Mejoras de los 5 mejores: filtro de caída profunda / tamaño de posición por profundidad |
| `_vol1`, `_vol2` | Filtros de volumen sobre los 3 mejores (no mejoraron) |

Detalle y resultados: [`ANALISIS.md`](algorithms/ANALISIS.md), [`ANALISIS_INVESTIGACION.md`](algorithms/ANALISIS_INVESTIGACION.md),
[`ANALISIS_MERCADO.md`](algorithms/ANALISIS_MERCADO.md), [`ANALISIS_CREATIVOS.md`](algorithms/ANALISIS_CREATIVOS.md),
[`ANALISIS_CARTERAS.md`](algorithms/ANALISIS_CARTERAS.md), [`ANALISIS_WALKFORWARD.md`](algorithms/ANALISIS_WALKFORWARD.md),
[`ANALISIS_MEJORAS.md`](algorithms/ANALISIS_MEJORAS.md) y [`ANALISIS_VOLUMEN.md`](algorithms/ANALISIS_VOLUMEN.md).

### Métrica: alpha de timing

El fitness antiguo (CAGR − ½·drawdown) premiaba no operar. La métrica vigente es el **alpha de timing** por prueba:

> CAGR de la estrategia − [exposición × CAGR de la acción (o cartera) + (1 − exposición) × tasa libre de riesgo]

Quedarse en efectivo da ≈ 0; solo suma quien acierta cuándo invertir. Los torneos informan el alpha medio con IC 95% (bootstrap),
% de pruebas con alpha > 0, p-valor ajustado (Benjamini-Hochberg, FDR 5%) y una bandera `significativo`.

### Torneos y herramientas

```bash
# Carteras: cada prueba = periodo al azar (300-600 jornadas) + 20 acciones al azar con datos en ese periodo
python -m algorithms.pcompete --tests 150 --seed 2026 --tag v1
python -m algorithms.pcompete algorithm03a algorithm02_v1 --set max_positions=5
python -m algorithms.pcompete A B --group validation --date-min 2020-01-01 --date-max 2023-12-31   # evaluar con acciones/fechas no vistas
python -m algorithms.portfolio algorithm03a --tests 5                       # una prueba de cartera por línea

# Una acción por prueba
python -m algorithms.compete --rounds 12 --seed 5 --tag x
python -m algorithms.analyze algorithm03c --since 1996-01-01 --until 2019-12-31   # análisis de operaciones
python -m algorithms.volume_study algorithm03a_v1 algorithm01b                      # estudio de eventos del volumen

# Optimizar variables con validación fuera de muestra
python -m algorithms.walkforward algorithm03a_v1 --set radius=0.3

# Señales de compra para la próxima apertura, sobre todo el S&P 500
python -m algorithms.signals --refresh --tag 2026-11-16
```

- **Cartera:** hasta `max_positions` posiciones con capital compartido (1/`max_positions` del capital cada una); si hay más
  señales que posiciones se elige al azar. Benchmark: las mismas acciones a partes iguales.
- **`--group analysis|validation`** divide las acciones en dos mitades disjuntas (las variaciones se diseñan con "análisis" y se
  evalúan con "validación"). El periodo desde 2024 está **reservado** (ya se usó una vez como confirmación del walk-forward).
- **Walk-forward** (`walkforward.py`): ventanas móviles de 10 años de entrenamiento y 3 de prueba; búsqueda bayesiana (Optuna); elige
  la "meseta" de parámetros (con vecinos ±10%) en vez del pico; compara contra la configuración actual en carteras nuevas.
- **Señales** (`signals.py`): evalúa los componentes del S&P 500 con los 3 mejores algoritmos con los datos hasta el último cierre; las
  acciones que no están en la base principal se bajan a `data/sp500_extra.db`.
- **Genético / afinado** (`genetic.py`, `tune.py`): históricos; el afinado con una sola muestra sobreajustaba (ver Resultados).
- Usar variables de mercado en un algoritmo: añadir la columna a `requires` y leer `df["mkt_vix"]` etc. (ver `features.stress_score`,
  `stress_expansion`, `healthy_bull`).

### Meta-etiquetado con IA

`algorithms/ml.py`: un modelo de gradient boosting pequeño y fijo (scikit-learn, extra `pip install .[ml]`) estima la probabilidad de que
cada operación de un algoritmo base gane y deja pasar la señal si supera la tasa histórica de acierto. Protocolo sin filtración:
reentrenamiento anual con operaciones que **terminaron antes del 1 de enero** del año a evaluar, entrenamiento con la mitad "análisis" de
acciones y evaluación con la mitad "validación".

```bash
python -m algorithms.ml build algorithm03a_v2_r2_i2     # operaciones + variables del día de la señal
python -m algorithms.ml train algorithm03a_v2_r2_i2     # modelos anuales
python -m algorithms.ml lift  algorithm03a_v2_r2_i2     # ¿ordena las operaciones fuera de muestra? (AUC, retorno por tercil)
```

Algoritmos `algorithmai01..03` (filtran `01b_i2`, `03a_v1_i2`, `03a_v2_r2_i2`) y `algorithmaictl01..03` (control: filtran al azar la misma
fracción de señales). Resultado en 150 carteras de acciones no vistas (2006-2023; comprar y mantener: 14,2% anual):

| Algoritmo | IA − base (IC 95%) | IA − control (IC 95%) |
|---|---|---|
| `ai01` | **+0,67 (0,33 a 0,99)** | **+1,07 (0,51 a 1,67)** |
| `ai02` | −0,50 (−1,00 a −0,08) | −0,69 (−1,27 a −0,16) |
| `ai03` | −0,07 (−0,43 a 0,26) | +0,99 (0,41 a 1,61) |

Solo `ai01` mejora de forma significativa a su base y al control, pero su CAGR (3,4%) sigue muy por debajo de comprar y mantener. El periodo
desde 2024-01-01 sigue reservado (una sola evaluación). Los IC son optimistas porque las carteras se solapan.

### Resultados y límites

- **Ninguno supera a comprar y mantener en CAGR.** En el torneo de carteras (acciones a partes iguales: CAGR ≈ 17%) el mejor
  algoritmo en exceso de CAGR queda unos 4 puntos por debajo.
- **Alpha de timing significativo:** 20 de 52 algoritmos, todos de retorno a la media (Bollinger / RSI); los de tendencia tienen alpha
  ≤ 0. Los mejores usan pocas veces el capital (exposición de 2% a 17%).
- **Mejoras que se sostuvieron fuera de muestra:** dimensionar la posición según la profundidad de la caída (`_i2`).
  **No ayudaron:** filtros de caída profunda (`_i1`), filtros de volumen (`_vol1/_vol2`), clímax de volumen (`creative01`), efecto fin de mes.
- **Optimizar variables casi nunca mejora fuera de muestra:** de 6 algoritmos, solo `02a_v2` mejoró de forma fiable (y sigue con alpha negativo).
- **Sesgo de supervivencia:** el universo son acciones que hoy están en el S&P 500 (200 mayores + 100 de peor rendimiento) y 20 small caps de
  un proxy del Russell; favorece sobre todo a los rebotes de caídas profundas.
- **Muestras que se solapan:** las carteras de una misma ventana comparten el mismo mercado; los IC dentro de un periodo corto (p.ej.
  2020-2023) están subestimados.

## Pruebas

```bash
pytest          # 36 pruebas, todas offline (datos sintéticos)
```
