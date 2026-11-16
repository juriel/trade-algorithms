# Torneo de carteras (20 acciones por prueba, capital compartido)

`python -m algorithms.pcompete --tests 150 --seed 2026 --tag v1` — 52 algoritmos, 150 pruebas, `max_positions=10`
(posiciones de 10% del capital), universo de 320 acciones (inicios entre 1973 y 2024, 49 años distintos),
con los `variables.cfg` del último commit. Resultados: `output/portfolio_competition_v1.csv`.

| | CAGR | Drawdown máx. | Calmar |
|---|---|---|---|
| Benchmark: las 20 acciones a partes iguales | 16,9% | 20,2% | 0,84 |

## Resultados
- **20 de 52 algoritmos tienen alpha de timing significativo** (FDR 5%), todos de retorno a la media (familias `03a`,
  `03c` y `01b`). Alpha medio de +0,8 a +1,6 puntos de CAGR, con exposición de 2% a 17% del capital.
  Mejores: `03a_v1` (1,57, IC 0,88-2,19), `01b` (1,50), `03a_v1_m1` (1,38), `03a_v2_r2` (1,34), `03c_v1` (1,33).
- **Ninguno supera al benchmark en rentabilidad**: el mejor en exceso de CAGR es `02a_v2` con 13,0% contra 16,9%
  (-3,9 puntos, IC -5,1 a -2,6), con 77% de exposición y drawdown de 17%.
- **Tendencia (`02*`)**: alpha de -2,3 a 0, no significativo o negativo (`02c_v1` ≈ 0). Siguen sin aportar acierto de timing.
- **Calmar alto (>2) en varios de retorno a la media**: es engañoso. Con 1%-6% de exposición el CAGR de 5%-7% viene
  sobre todo del interés del efectivo, y el drawdown es pequeño porque casi no se invierte.

## Lecciones
1. Con 10 posiciones de 10%, los algoritmos de retorno a la media siguen casi sin invertir (exposición mediana de 4,9%):
   sus señales son raras. Falta probar posiciones más grandes (`max_positions=5` o 3) o más acciones por cartera.
2. Pasar de una acción a una cartera redujo el ruido: 20 algoritmos significativos contra 8 en el torneo de una acción.
3. El orden de los algoritmos es parecido en ambos torneos (retorno a la media arriba, tendencia abajo).

## Limitaciones
- Universo = acciones que hoy están entre las mayores del S&P 500 (más 100 de peor rendimiento y 20 de un proxy de
  small caps): sigue habiendo sesgo de supervivencia, que favorece sobre todo al retorno a la media.
- `max_positions` y el tamaño de posición no se optimizaron.
- Selección aleatoria entre señales simultáneas: no hay jerarquía por calidad de la señal.
