# Investigación en Internet y variaciones de los 6 mejores algoritmos

## Selección
Ranking combinado (puesto medio normalizado en el torneo de historial completo y en el de 2020+, **con los
`variables.cfg` previos al afinado**): `03c_v2`, `03c_v1`, `03a_v2`, `03c`, `03a_v1`, `02_v1`.
Cinco de los seis son de retorno a la media sobre Bollinger.

## Qué dice la investigación (calidad de las fuentes: práctica de traders, no estudios revisados por pares)
| Idea | Resumen | Fuente |
|---|---|---|
| RSI(2) de Connors + tendencia | RSI de 2 periodos muy bajo, compra solo sobre la SMA200, sale al superar la media de 5 días | [StockCharts](https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/rsi-2) |
| IBS | Internal Bar Strength = (cierre-mínimo)/(máximo-mínimo); IBS bajo (≤0,25) = agotamiento; salida a pocos días | [GuruFinance](https://ayratmurtazin.beehiiv.com/p/building-a-production-ready-mean-reversion-strategy), [TradingView](https://fr.tradingview.com/script/2KH3h0AC-S4-IBS-Mean-Rev-3candleExit) |
| Salidas por tiempo y stops | La mayoría de las reversiones se resuelve en 3-5 días; pasado ese plazo la hipótesis suele ser errónea; stop de 1-2 ATR | [Algomatic](https://algomatictrading.substack.com/p/how-to-create-winning-mean-reversion), [arXiv 1411.5062](https://arxiv.org/pdf/1411.5062) |
| Confirmación de giro | Esperar una vela alcista / cierre de vuelta dentro de la banda en vez de comprar el cierre fuera | [FMZ](https://www.fmz.com/lang/en/strategy/504546), [TradingView](https://www.tradingview.com/script/XRPeqEdA/) |
| Filtro de régimen | Un filtro tipo VIX deja fuera de regímenes inestables donde "lo sobrevendido sigue sobrevendido"; advierte contra sobreajustar filtros | [Alpha Algo](https://algotr.substack.com/p/this-simple-mean-reversion-strategy) |
| MFI vs RSI | Si el MFI cae mucho más que el RSI hay salida de dinero real: sobreventa con respaldo de volumen | [NexusFi](https://nexusfi.com/a/indicators/money-flow-index-mfi) |
| Chandelier | Trailing de LeBeau/Elder: máximo más alto menos k×ATR; más ancho en acciones más volátiles | [LuxAlgo](https://www.luxalgo.com/library/concept/chandelier-stop.md), [IncredibleCharts](https://www.incrediblecharts.com/indicators/chandelier_exits.php) |

No verifiqué las cifras de rentabilidad que citan esas páginas y no las uso; solo tomé las **ideas** y sus
parámetros típicos (RSI2 < 10, IBS ≤ 0,25, tiempo máximo 5 días, stop 2 ATR, SMA de 5 para salir).
El filtro VIX real no es posible: la BD no tiene el índice; se sustituyó por la volatilidad propia de la acción
(`ATR% / su media de 100 días`, `algorithms/features.py`).

## Observaciones propias (del análisis de operaciones anterior, `ANALISIS.md`)
- Las salidas por tiempo son la mayor fuente de pérdidas (-2% a -7% de media) → plazos más cortos y stops.
- Mayor ATR% y bandas más anchas = mayor retorno por operación → se mantienen los filtros de volatilidad.
- La tendencia gana por pocas operaciones grandes → no recortarlas con metas fijas, trailing amplio.
- **Cuidado con la métrica:** el fitness (CAGR − ½·drawdown) premia no operar. Aquí se muestran también el
  `calmar` (CAGR/drawdown) y la exposición; casi todos los algoritmos de retorno a la media invierten ~1-3% del tiempo.

## Variaciones (`_r1`, `_r2`; valores por defecto de la literatura, **sin optimizar**)
| Base | r1 | r2 |
|---|---|---|
| 03c_v2 | reingreso dentro de la banda tras cierre fuera con MFI bajo | + IBS ≤ 0,25 |
| 03c_v1 | + filtro de régimen de volatilidad | MFI ≥5 puntos bajo el RSI; límite de 6 días |
| 03a_v2 | RSI(2) < 10 y salida sobre SMA5 (Connors) | + IBS, límite de 5 días, stop/meta en ATR |
| 03c | RSI(2) + sobre SMA200 + salida SMA5 + stop 6% | MFI+RSI(14) + régimen de volatilidad + stop 2 ATR |
| 03a_v1 | vela alcista de confirmación | + IBS + régimen + límite de 5 días |
| 02_v1 | Chandelier clásico (máximos) + stop inicial 4 ATR | + bandas anchas + Chandelier que se ensancha con la volatilidad |

## Resultados (100 acciones de validación, 12 rondas × 50 acciones; puesto medio, menor = mejor; Calmar entre paréntesis)
| Base | Original 2020+ | r1 2020+ | r2 2020+ | Original hist. | r1 hist. | r2 hist. |
|---|---|---|---|---|---|---|
| 03c_v2 | 11,5 (0,11) | 11,3 (0,06) | 13,2 (0,01) | 8,5 (0,08) | 9,6 (-0,02) | 6,8 (0,03) |
| 03c_v1 | 10,2 (0,18) | 8,1 (0,16) | **6,2 (0,24)** | 11,1 (0,08) | **5,8 (0,17)** | 8,3 (0,10) |
| 03a_v2 | 8,6 (0,31) | 14,3 (0,20) | **5,1 (0,38)** | 14,1 (0,06) | 15,6 (0,07) | **7,8 (0,17)** |
| 03c | 14,0 (0,15) | 8,9 (0,15) | **5,9 (0,23)** | 11,8 (0,10) | **5,0 (0,17)** | **5,2 (0,16)** |
| 03a_v1 | 12,0 (0,29) | 10,1 (0,29) | **6,5 (0,30)** | 14,3 (0,14) | 17,2 (-0,01) | **7,4 (0,14)** |
| 02_v1 | 12,9 (0,44) | 14,2 (0,41) | 12,7 (0,43) | 13,1 (0,38) | 12,9 (0,37) | 12,2 (0,36) |

- Mejoran en **ambos** periodos: `03c_v1_r1`, `03c_v1_r2`, `03a_v2_r2`, `03c_r1`, `03c_r2`, `03a_v1_r2` (y `02_v1_r2` por un margen mínimo).
- **No** mejoran: `03c_v2_r1`, `03c_v2_r2`, `03a_v2_r1` (RSI(2) + salida SMA5), `03a_v1_r1` (vela de confirmación) y `02_v1_r1`.
- Las que funcionan combinan **límite de tiempo corto + stop/meta por ATR + filtro de régimen/IBS**; la
  confirmación de giro y el RSI(2) no aportaron en estos datos.
- Comprar y mantener sigue 1º. En el periodo 2020+ el mejor algoritmo (`03a_v2_r2`) rinde ~1,3% anual con 1% de exposición.

## Limitaciones
- 12 rondas con muestras aleatorias: diferencias de ~1 puesto no son significativas; se probaron 12 variaciones (riesgo de falsos positivos).
- Misma historia de mercado en ambos periodos; las acciones son las 200 mayores del S&P 500 de hoy (sesgo de supervivencia).
- El motor opera una acción a la vez: un portafolio real con muchas acciones a la vez usaría mucho más capital.
- Las bases se evaluaron con los `variables.cfg` previos al afinado (git HEAD), no con los afinados.
