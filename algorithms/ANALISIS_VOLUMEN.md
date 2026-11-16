# Volumen: qué algoritmos lo usan y si sirve (`_vol1`, `_vol2`)

## Quién usa volumen
- **Pico contra el promedio de 20 días:** solo `creative01` (clímax vendedor) y `creative03` (ruptura con volumen). Alpha de carteras: -0,05 (n.s.) y -1,83 (significativamente negativo).
- **MFI (mezcla precio y volumen):** los 17 algoritmos de la familia `03c`. 12 de 15 con alpha significativo positivo, pero `03a` (RSI en vez de MFI) rinde igual: no hay evidencia de que el volumen aporte.
- **OBV:** se calcula y se guarda en la base, pero ningún algoritmo lo usa. El resto (unos 33) ignora el volumen.

## Estudio de eventos (`python -m algorithms.volume_study ...`)
Cortes en terciles fijados en el descubrimiento (mitad "análisis", 1996-2019) y aplicados sin cambios a dos confirmaciones (otras acciones,
1996-2019 y 2020-2023). Diferencia de retorno medio por operación, tercil de volumen BAJO menos ALTO (puntos %):

| Algoritmo / variable | Descubrimiento | Confirm. 1996-2019 | Confirm. 2020-2023 |
|---|---|---|---|
| `03a_v1` volumen del día | +0,91 (0,27 a 1,56) | +0,11 (-0,51 a 0,73) | +0,86 (-0,44 a 2,26) |
| `03a_v2_r2` volumen del día | +1,06 (0,31 a 1,81) | +0,56 (-0,19 a 1,35) | +0,50 (-1,01 a 2,02) |
| `03a_v1_m1` volumen del día | +1,33 (0,27 a 2,44) | -0,37 (-1,54 a 0,73) | +3,03 (0,84 a 5,29) |
| `03c_v1` flujo Chaikin 20d | +0,98 (0,02 a 1,99) | +0,93 (0,07 a 1,78) | -0,94 (-3,38 a 1,36) |
| `01b` volumen del día | -0,13 (-0,38 a 0,13) | +0,09 (-0,17 a 0,33) | +1,67 (1,04 a 2,32) |

Ninguna variable cumple el criterio fijado de antemano (significativa en descubrimiento **y** confirmada en las dos muestras): los efectos
encogen o cambian de signo fuera de la muestra de descubrimiento. Solo el volumen bajo del día en `03a_v2_r2` y `03a_v1` mantiene el signo
(positivo) en las tres muestras, sin significancia en las confirmaciones. CMF y OBV no son consistentes entre algoritmos.

## Variaciones y resultado (carteras de 20 acciones, 150 pruebas, acciones de la mitad "validación")
`_vol1`: solo con volumen del día <= 1,5x el promedio; `_vol2`: solo con volumen de 5 días <= 1,3x el de los 20 anteriores.
Diferencia de alpha frente a la base `_i2` (pareada, IC 95%):

| Base | `_vol1` 1990-2019 | `_vol1` 2020-2023 | `_vol2` 1990-2019 | `_vol2` 2020-2023 |
|---|---|---|---|---|
| `01b_i2` | **-1,39 (-1,93 a -0,90)** | **+0,64 (0,15 a 1,19)** | **-1,24 (-1,76 a -0,77)** | -0,07 (-0,58 a 0,49) |
| `03a_v2_r2_i2` | **-0,66 (-1,18 a -0,16)** | **-0,91 (-1,51 a -0,25)** | **-1,15 (-1,67 a -0,65)** | **-1,29 (-1,95 a -0,55)** |
| `03a_v1_i2` | -0,60 (-1,28 a 0,05) | **-1,01 (-1,68 a -0,31)** | **-0,87 (-1,64 a -0,17)** | **-0,92 (-1,70 a -0,05)** |

## Conclusiones
1. **Filtrar por volumen no mejora el alpha:** en 12 comparaciones, 9 empeoran de forma significativa y solo una mejora de forma significativa
   (`01b_i2_vol1` en 2020-2023), que empeora en 1990-2019. Los filtros eliminan entre 20% y 55% de las operaciones.
2. **Sí reducen el riesgo:** menos drawdown y mayor Calmar (p.ej. `03a_v2_r2_i2` 1,59 -> 2,52 en 1990-2019), a costa de rentabilidad.
3. **Recomendación:** no incorporar filtros de volumen a los mejores algoritmos. No se crearon variantes de OBV/CMF porque el estudio
   de eventos no mostró un efecto consistente.

## Limitaciones
- Los IC del estudio de eventos son optimistas (las operaciones de un mismo día están correlacionadas).
- Se probaron 5 variables x 5 algoritmos x 3 muestras: algún resultado aislado puede ser azar.
- Los resultados son para esta forma de usar el volumen (terciles, umbrales fijos), no descartan otras.
