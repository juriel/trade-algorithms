# Algoritmos creativos (`algorithmcreative01` … `06`)

Seis ideas distintas a las anteriores. Los valores por defecto salen de la lógica de cada idea y **no se ajustaron a los datos**
(solo se aflojó `creative01` —volumen ×2 y caída 3% en vez de ×2,5 y 4%— porque con los primeros valores casi no operaba).

| Algoritmo | Idea | Datos que usa |
|---|---|---|
| `01` Clímax vendedor | caída fuerte con volumen ≥2× + vela de rechazo (martillo, envolvente, penetrante, estrella de la mañana, palomo o IBS alto); sale en la SMA20 | volumen, patrones de velas, ATR |
| `02` Giro del pico del VIX | tras un pico del VIX (percentil ≥85 en 5 días), primer día que el VIX baja: compra acciones débiles (RSI<50) sobre su SMA200; sale al normalizarse el VIX | VIX |
| `03` Compresión y ruptura | ancho de Bollinger en su cuantil bajo de 120 días, luego cierre sobre la banda superior con volumen ×1,5 y sobre SMA200; trailing Chandelier | Bollinger, volumen |
| `04` Líderes en retroceso | fuerza relativa vs. S&P 500 (120 días) ≥ +10 pts, tendencia alcista, retroceso bajo la SMA20 con RSI<45 y S&P sobre su SMA200 | S&P 500 |
| `05` Interruptor macro | tendencia (EMA12>EMA26, ADX) solo en *risk-on* (S&P>SMA200, VIX/media50<1,1, DXY sin avance fuerte, curva no invertida); vende al pasar a *risk-off* | VIX, DXY, curva, S&P |
| `06` Efecto fin de mes | calendario: compra a la apertura del último día hábil del mes y mantiene 4 días, con S&P y acción sobre la SMA200 | calendario |

## Resultados (acciones de validación, 12 rondas × 50; `min_trades=10`; puesto medio / Calmar)

| | 2020+ puesto | 2020+ CAGR | 2020+ Calmar | 1996-2019 puesto | 1996-2019 CAGR | 1996-2019 Calmar |
|---|---|---|---|---|---|---|
| `creative01` | 5,9 | 0,09% | 0,04 | 3,1 | 0,26% | 0,11 |
| `creative02` | 8,4 | 1,49% | 0,18 | 8,0 | 0,54% | 0,06 |
| `creative03` | 8,1 | 2,33% | 0,24 | 8,4 | 1,26% | 0,12 |
| `creative04` | 6,8 | 1,33% | 0,22 | 5,6 | 0,72% | 0,13 |
| `creative05` | 9,5 | 2,66% | 0,20 | 9,3 | 4,68% | 0,24 |
| `creative06` | 11,8 | -0,17% | -0,01 | 10,8 | -0,24% | -0,02 |
| (ref.) `03a_v1_m1` | 3,5 | 1,35% | 0,40 | 4,1 | 1,30% | 0,25 |
| (ref.) `02_v1` | 6,5 | 9,22% | 0,44 | 10,1 | 5,08% | 0,24 |
| (ref.) comprar y mantener | 2,7 | 19,73% | 0,64 | 6,9 | 13,26% | 0,41 |

## Conclusiones
1. **Ninguno supera a los mejores anteriores** (`03a_v1_m1`, `03a_v2_m1`) ni a comprar y mantener.
2. `creative01` queda bien en puesto (5º y 2º) **solo porque casi no invierte** (0,7% del tiempo, CAGR 0,1%-0,3%): el fitness premia
   operar poco. Su Calmar (0,04-0,11) es de los peores; la idea del clímax con velas no mostró ventaja en estos datos.
3. `creative05` (interruptor macro) es el de mayor CAGR entre los nuevos (2,7% y 4,7%) con 23%-46% de exposición, pero con drawdown de 13%-20%
   y Calmar parecido a `02_v1`: el filtro macro no mejora a la tendencia simple.
4. `creative06` (fin de mes) **no muestra el efecto**: ~600 operaciones por ronda con retorno medio ≈ 0 tras costos (CAGR negativo).
5. `creative02`, `03` y `04` quedan a mitad de tabla sin ventaja clara.

## Limitaciones
- Una sola configuración por idea, sin optimizar: un resultado malo no descarta la idea, solo esta implementación.
- Mismas limitaciones del resto del proyecto (200 acciones de hoy, sesgo de supervivencia, una acción a la vez, fitness que premia operar poco).
- Los datos de crédito (HYG/LQD) empiezan en 2007, por eso `creative05` no los usa.
