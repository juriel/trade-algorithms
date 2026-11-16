# Mejoras de los 5 mejores algoritmos (`_i1`, `_i2`)

**Selección:** los 5 de mayor alpha significativo en el torneo de carteras (`ANALISIS_CARTERAS.md`): `03a_v1`, `01b`, `03a_v1_m1`,
`03a_v2_r2`, `03c_v1`. Las variaciones heredan las reglas de la base (copia por herencia) y tienen su propio `variables.cfg`.

## Qué mostró el análisis de operaciones (entradas 1996-2019, mitad "análisis"; `python -m algorithms.analyze <alg>`)
- **Bollinger (03a/03c):** el rebote crece con la profundidad de la caída: retorno a 5 días <= -14% rinde 2,0-4,0% por operación contra
  0,6-0,9% en caídas leves; estar a >37% de los máximos de un año rinde 1,9-3,7% contra 0,6-0,8%; IBS <= 0,06 rinde ~2%.
  El volumen climático (>2,5x) rinde menos, no más: contradice la idea de `creative01`.
- **01b:** señal casi uniforme; IBS <= 0,07 rinde algo más (0,89% contra ~0,55%) y las caídas extremas (>33% bajo máximos) peor (0,23%).

## Variaciones
| | Cambio |
|---|---|
| `_i1` | Solo entra con caída profunda: retorno a 5 días <= -10% y a >25% de los máximos (en 01b: IBS <= 0,10 y distancia a máximos entre -35% y -10%) |
| `_i2` | Misma entrada, **tamaño de posición proporcional a la profundidad** (caída a 5 días / 10%, entre 0,5x y 3x); en 01b, 1,5x con IBS <= 0,07. Gancho nuevo `Algorithm.size_series` (solo carteras) |

## Resultados (carteras de 20 acciones, 150 pruebas, acciones de la mitad "validación" que NO se usó para el análisis)
Diferencia de alpha frente a la base (pareada por prueba, IC 95%):

| Base | `_i2` 1990-2019 | `_i2` 2020-2023 | `_i1` 1990-2019 | `_i1` 2020-2023 |
|---|---|---|---|---|
| `03a_v1` | **+1,07 (0,50 a 1,78)** | +0,18 (-0,24 a 0,57) | +0,22 (-0,23 a 0,66) | **-0,48 (-0,79 a -0,18)** |
| `03a_v1_m1` | **+0,95 (0,56 a 1,38)** | -0,13 (-0,39 a 0,11) | +0,02 (-0,27 a 0,33) | +0,16 (-0,04 a 0,37) |
| `03a_v2_r2` | **+0,87 (0,47 a 1,32)** | **+0,48 (0,10 a 0,83)** | -0,01 (-0,31 a 0,33) | **-0,39 (-0,58 a -0,20)** |
| `03c_v1` | **+0,66 (0,36 a 1,00)** | -0,22 (-0,60 a 0,11) | +0,05 (-0,20 a 0,28) | -0,17 (-0,42 a 0,07) |
| `01b` | **+1,03 (0,58 a 1,56)** | **+0,32 (0,11 a 0,53)** | **-1,72 (-2,50 a -1,00)** | **-2,31 (-2,96 a -1,66)** |

## Conclusiones
1. **Lo que se sostiene:** dimensionar por profundidad (`_i2`) mejora el alpha de forma significativa en las 5 bases con acciones no vistas
   (1990-2019). En 2020-2023 (fuera de tiempo) la mejora se reduce: significativa en `03a_v2_r2_i2` y `01b_i2`, nula en las otras
   tres, nunca significativamente negativa. Las más robustas: **`03a_v2_r2_i2`** (1,65 contra 1,17 en 2020-23) y **`01b_i2`**.
2. **Cuidado: más alpha con más riesgo.** El dimensionado sube exposición y drawdown (03a_v1: DD 7,3% → 9,7% en 2020-23) y el
   Calmar no mejora (1,26 → 1,20; 1,86 → 1,59 en 1990-2019). Mejora el rendimiento del capital usado, no el cociente rendimiento/riesgo.
3. **Los filtros de caída profunda (`_i1`) no mejoran el alpha:** operan 55%-60% menos con alpha igual (1990-2019) o peor (2020-23, y en
   01b mucho peor). Sí bajan el drawdown (Calmar de 1,86 a 3,16 en `03a_v2_r2`): intercambian rentabilidad por menos riesgo.
4. Ningún algoritmo supera a comprar y mantener en CAGR (8,1% en 2020-23, 17,2% en 1990-2019).

## Limitaciones
- Umbrales de las variaciones tomados de cuartiles del análisis, no optimizados.
- 2020-2023 son solo 4 años: las 150 carteras se solapan mucho. El periodo desde 2024 sigue reservado.
- Sesgo de supervivencia del universo, que favorece a los rebotes de caídas profundas.
