# Variantes con variables de mercado (`_m1`, `_m2`)

Se usaron las variables `mkt_*` (VIX, S&P 500, amplitud, crédito, curva de tasas, DXY; ver `ticker2db.FEATURE_DOC`)
para filtrar las entradas de los 6 mejores algoritmos (`03c_v2`, `03c_v1`, `03a_v2`, `03c`, `03a_v1`, `02_v1`).
Cada variante hereda las reglas de su base y suma un filtro de mercado; sus valores están en su `variables.cfg`.

## Qué mostró el análisis de operaciones (entradas 1996-2019, mitad "análisis" de las acciones)
`python -m algorithms.analyze <algoritmo> --since 1996-01-01 --until 2019-12-31`

- **Retorno a la media (03c, 03c_v1/v2, 03a_v1/v2):** los rebotes rinden más en *capitulación del mercado*:
  VIX en su percentil >96 del año (3,5% por operación contra ~0,6% en el resto, 03c_v1), RSI(14) del S&P 500 < 31
  (1,8%-2,8%), amplitud < ~25% de acciones sobre su SMA200 (2,2%-3,3%), crédito riesgoso (HYG/LQD) cayendo >4%
  (2,8%-4,3%). Rinden menos en la zona media (VIX 19-24, S&P ligeramente a la baja).
- **Tendencia (02_v1):** señal débil y ruidosa; solo se notó peor rendimiento con la curva de tasas invertida
  (3,6% contra 8-11% por operación) y mejor con amplitud alta.

## Variantes
| Variante | Filtro (se suma a la entrada de la base) |
|---|---|
| `_m1` (retorno a la media) | al menos 2 de 4 señales de capitulación: VIX en percentil ≥90, RSI S&P ≤31, amplitud ≤25%, S&P ≤-8% a 20 días |
| `_m2` (retorno a la media) | basta 1 señal de estrés: VIX/media50 ≥1,3, HYG/LQD ≤-4% a 20 días o S&P ≤-8% a 20 días |
| `02_v1_m1` | S&P sobre SMA200, amplitud ≥45% y curva 10a-3m ≥0,7 |
| `02_v1_m2` | `_m1` + VIX en percentil ≤80 y DXY a 20 días ≤+1,3% |

Los umbrales salen de los cuartiles del análisis; **no están optimizados**.

## Resultados (acciones de validación, 12 rondas × 50, `min_trades=10`; puesto medio, menor = mejor; entre paréntesis, Calmar)
`python -m algorithms.compete <algoritmos> --group validation --period test|train --since 1996-01-01 --set min_trades=10`

| Base | 2020+ base | m1 | m2 | 1996-2019 base | m1 | m2 |
|---|---|---|---|---|---|---|
| 03c_v2 | 12,4 (0,11) | 7,0 (0,12) | 9,7 (0,07) | 7,8 (0,24) | 5,2 (0,33) | 5,3 (0,25) |
| 03c_v1 | 11,1 (0,18) | 8,3 (0,14) | 10,7 (0,10) | 8,6 (0,26) | 6,7 (0,23) | 8,6 (0,17) |
| 03a_v2 | 10,3 (0,31) | 4,8 (0,38) | 7,6 (0,30) | 12,9 (0,18) | 8,5 (0,21) | 8,6 (0,20) |
| 03c | 15,2 (0,15) | 9,3 (0,11) | 11,4 (0,12) | 8,7 (0,24) | 4,4 (0,33) | 6,1 (0,27) |
| 03a_v1 | 13,3 (0,29) | 4,6 (0,40) | 10,5 (0,27) | 14,4 (0,20) | 9,1 (0,25) | 11,8 (0,19) |
| 02_v1 | 12,8 (0,44) | 12,8 (0,26) | 13,4 (0,24) | 18,0 (0,24) | 16,6 (0,26) | 16,8 (0,23) |

## Conclusiones
1. En el retorno a la media, el filtro mejora el puesto en 19 de 20 comparaciones, **pero lo hace recortando
   operaciones (-50% a -80%), exposición y drawdown; el CAGR baja en casi todas** (p.ej. 03a_v1: 1,97% → 1,35%).
   Sube la tasa de aciertos (69% → 77%-80%). El Calmar mejora solo en parte (ver tabla).
2. Mejoran puesto **y** Calmar en ambos periodos: `03a_v1_m1`, `03a_v2_m1` y, por margen mínimo en 2020+, `03c_v2_m1`.
3. La tendencia (`02_v1`) **no mejora**: el filtro baja la exposición de 49% a 15% y el CAGR de 9,2% a 2,2% en 2020+.
4. El ranking usa el fitness actual (CAGR − ½·drawdown), que premia operar menos; por eso se muestra también el Calmar.
   Comprar y mantener sigue siendo mejor en CAGR (19,7% en 2020+).

## Limitaciones
- Los umbrales se eligieron con el mismo mercado de 1996-2019 que la columna "1996-2019" de arriba (otras acciones, **mismas
  fechas**): solo 2020+ es independiente en el tiempo, y ese periodo incluye pocos episodios de estrés (COVID, 2022).
- Pocas operaciones por variante (≈200-700 en 12 rondas). Diferencias pequeñas pueden ser ruido; se probaron 12 variantes.
- Los datos de mercado empiezan en 1990-1996 (VIX, amplitud), por eso las pruebas parten de 1996 (`--since`); el crédito
  (HYG/LQD) y el VIX3M existen desde 2006-2007, y antes de esas fechas esa señal vale "no activa".
- Las bases se compararon con sus `variables.cfg` previos al afinado (los del último commit).
