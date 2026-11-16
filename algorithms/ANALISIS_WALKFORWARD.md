# Optimización robusta de variables (walk-forward + meseta + búsqueda bayesiana)

`python -m algorithms.walkforward <algoritmos> [--stage walkforward|final] [--set radius=0.3 train_tests=32 trials=40]`
Código: `algorithms/walkforward.py`; configuración: `walkforward.cfg`. Se probó con 6 algoritmos sobre carteras de 20 acciones.

## Método
- **Walk-forward:** 8 pliegues deslizantes entre 1990 y 2023: entrenar 10 años, probar en los 3 siguientes con carteras NUEVAS.
- **Búsqueda:** optimización bayesiana (TPE de Optuna); la primera evaluación es la configuración actual.
- **Meseta:** de los 8 mejores candidatos se elige el de mejor promedio entre él y 6 vecinos (±10% en todos los parámetros numéricos).
- **Tres variantes fuera de muestra:** actual, "pico" (mejor valor en entrenamiento) y "meseta".
- **Periodo reservado (2024 en adelante):** usado UNA vez (`--stage final`) como confirmación. **Ya está consumido: no usarlo para
  seguir iterando.**
- **Regla de adopción** (fijada antes de ver los resultados de la versión 2): se adoptan nuevos valores solo si el IC 95% de la
  mejora fuera de muestra queda por encima de 0 y al menos 5 de 8 pliegues mejoran.

## Resultados (alpha medio fuera de muestra; 192 carteras por algoritmo)
| Algoritmo | v1 (todo el rango): actual → meseta | v2 (±30%, 32 pruebas): actual → meseta | Mejora v2 (IC 95%) | Pliegues |
|---|---|---|---|---|
| `02a_v2` | -3,81 → 0,35 | -3,81 → -1,80 | **+2,01 (1,04 a 2,94)** | 6/8 |
| `01b` | 1,72 → 0,80 (peor) | 1,72 → 1,99 | +0,27 (-0,36 a 0,88) | 5/8 |
| `03a_v2_r2` | 0,61 → 1,38 | 0,61 → 0,85 | +0,23 (-0,13 a 0,58) | 5/8 |
| `03c_v1` | 1,16 → 1,50 | 1,16 → 1,10 | -0,06 (-0,43 a 0,32) | 4/8 |
| `03a_v1` | 1,03 → 1,02 | 1,03 → 0,62 | -0,41 (-0,97 a 0,14) | 4/8 |
| `03a` | 0,94 → 0,87 | 0,94 → -0,25 | -1,19 (-1,77 a -0,64) (peor) | 4/8 |

## Conclusiones
1. **Optimizar casi nunca mejora fuera de muestra.** Solo `02a_v2` cumple la regla, y en las dos versiones. En `03a` y `01b`
   optimizar empeora de forma significativa.
2. **Sobreajuste grande:** el alpha de entrenamiento del mejor candidato es 3-6 puntos y fuera de muestra 0,3-2. La búsqueda
   acotada y las 32 pruebas lo redujeron, no lo eliminaron.
3. **La meseta reduce la fragilidad** (el candidato tolera mejor un ±10%), pero **no generaliza mejor que el pico** de forma
   consistente (v1: pico mejor en 3 de 6; v2: pico mejor en 4 de 6).
4. **Confirmación en el periodo reservado (2024+, una sola vez):** para `02a_v2` la configuración nueva dio -0,77 contra -0,61 de la
   actual (diferencia -0,16, IC -8,9 a 6,7): **no confirma ni desmiente** (24 carteras que se solapan mucho en 2,9 años).
   En `03a`, `03a_v1` y `01b` optimizar empeoró también ahí, de acuerdo con la decisión de no adoptar.

## Variables ajustadas
Solo `02a_v2`: `adx_min` 25 → 29,56, `min_bb_width` 12 → 13,91, `chandelier_window` 22 → 15, `chandelier_k` 5 → 6,30.
Los demás algoritmos conservan sus valores. **Aun con el ajuste, `02a_v2` sigue con alpha negativo** (peor que una cartera con
su misma exposición): el ajuste lo hace menos malo, no bueno.

## Limitaciones
- Solo se optimizaron 6 de 52 algoritmos; no se puede asumir que el resultado se extienda al resto.
- Las carteras de prueba de un mismo pliegue se solapan en el tiempo: los IC dentro de un pliegue están subestimados.
- Misma historia de mercado y universo con sesgo de supervivencia que el resto del proyecto.
