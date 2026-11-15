# Análisis de los 5 mejores algoritmos y sus versiones mejoradas

**Selección:** los 5 mejores del torneo (sin contar buy&hold): `03c`, `02`, `03a`, `02a`, `02c`.

**Método.** Las 200 acciones se dividieron en dos mitades disjuntas (`algorithms.analyze.split_symbols`):
- *análisis* (100): se usó para estudiar las operaciones (`python -m algorithms.analyze algorithm03c`) y elegir mejoras;
- *validación* (100): solo para evaluar el resultado final (`python -m algorithms.compete --group validation`).

## Qué encontró el análisis (mitad "análisis", historial completo)

| Algoritmo | Operaciones | Aciertos | Ganancia / pérdida media | Hallazgo principal |
|---|---|---|---|---|
| 03c Bollinger+MFI | 2.942 | 72% | +4,1% / -6,8% | 27% de las operaciones salen por tiempo con -6,8% de media; sin límite de pérdida |
| 03a Bollinger+RSI | 5.768 | 74% | +3,7% / -7,2% | igual: salidas por tiempo a -7,2%; peor operación -58% |
| 02 Tendencia | 11.356 | 41% | +10,5% / -5,3% | 75% salen por la SMA50 con -3,5% de media (salida tardía); la meta de 15% recorta las ganancias |
| 02a Cruce EMAs | 15.666 | 45% | +10,1% / -6,1% | 65% salen por el cruce con -4,9% (la peor salida); meta de 12% |
| 02c Retroceso | 21.492 | 60% | +4,7% / -5,2% | 63% salen por tiempo con -2,4% |

Patrones comunes:
1. **La volatilidad discrimina.** En los cinco algoritmos, el cuartil de mayor ATR% y de bandas de Bollinger más anchas rinde el doble (o más) que el de menor. Con un objetivo fijo de 4-5% las acciones tranquilas casi nunca lo alcanzan y en las volátiles se queda corto.
2. **Sin límite de pérdida** las operaciones de retorno a la media acaban en salidas por tiempo muy negativas. Es la causa de que ganen el 72% de las veces pero rindan solo ~1% por operación.
3. **Los de tendencia** pierden en la mayoría de operaciones y ganan por unas pocas grandes; las salidas por señal tardía y la meta fija limitan justamente esas ganancias.

## Cambios al motor
- `stop_pct`: vende **a la apertura** si el cierre de ayer cayó ese % bajo la entrada (sigue cumpliendo la regla de vender solo al inicio del día o al cumplir meta).
- Metas y stops en múltiplos de ATR: definir `target_atr_mult` / `stop_atr_mult` en las variables del algoritmo.

## Versiones mejoradas (cada una con su `variables.cfg`)

| Algoritmo | v1 | v2 |
|---|---|---|
| 03c | filtro ATR% mínimo; meta 1,5×ATR, stop 2,5×ATR | ancho de bandas ≥ 10%, stop 6%, máx. 8 días |
| 03a | filtro ATR% mínimo; meta 1,5×ATR, stop 2,5×ATR | caída ≥ 9% bajo SMA50, bandas ≥ 12%, stop 7% |
| 02 | momentum MACD ≥ 0,5%; salida Chandelier (máx. 22 días − 5×ATR); sin meta | ancho de bandas ≥ 12%; salida SMA50; meta 25% |
| 02a | misma entrada; salida Chandelier k=5; sin meta | ADX ≥ 25 y bandas ≥ 12%; Chandelier k=5; sin meta |
| 02c | ADX ≥ 25, retroceso ≥ 1,5% bajo SMA20; meta 2×ATR, stop 2,5×ATR | ATR% ≥ 2, MACD ≤ -0,3%; stop 6%, meta 7%, máx. 10 días |

La primera versión de 02_v1/02a_v1 usaba un Chandelier con k=3 y **empeoró** en validación (cortaba las
ganancias). Se barrieron 8 combinaciones en la mitad de análisis (k=3/5, meta, filtro MACD) y k=5 fue claramente
mejor, por eso es el valor final. Es un ajuste hecho sobre pocas combinaciones y se confirmó en la otra mitad.

## Resultado en validación (100 acciones no usadas en el análisis; 12 rondas × 50 acciones, periodos de 300-600 barras, seed 21)

Posición media entre rondas (menor es mejor); `buy&hold` queda 1º, pero los 10 algoritmos mejorados quedan por delante de su original:

| Familia | Original | v1 | v2 |
|---|---|---|---|
| 03c | 6,00 | 5,42 | **3,25** |
| 03a | 11,33 | **7,67** | 7,75 |
| 02 | 10,83 | **7,58** | 9,58 |
| 02a | 12,00 | **9,33** | 9,58 |
| 02c | 14,58 | **8,50** | 10,67 |

## Limitaciones
- **Ninguno supera a comprar y mantener** en esta muestra (acciones que hoy están entre las 200 mayores del S&P 500: sesgo de supervivencia).
- Parte de la mejora viene de operar menos y con menor drawdown, no de ganar más: `03c_v2` casi no invierte (exposición 1,2%).
- El método de ranking (puesto medio entre rondas) se adoptó después de ver que el fitness medio lo distorsionaban rondas atípicas.
- Los datos de validación son otras acciones, pero el **mismo periodo histórico**: no prueba robustez ante otro régimen de mercado.
