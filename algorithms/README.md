# Algoritmos de inversión

Motor de backtest (`engine.py`) + un algoritmo por carpeta (`algorithm01`, `algorithm02`, ...).

## Reglas
- **Compra:** solo a la apertura del día; condicionada por `buy_signal` (datos del día anterior).
- **Venta:** a la apertura (`sell_signal` o `max_hold_days`) o al cumplir la meta `target_pct`
  (límite: al precio meta si el máximo del día lo alcanza; a la apertura si ya la supera).
- Sin lookahead: toda señal calculada al cierre de t se ejecuta en la apertura de t+1.

## Uso
```bash
python -m algorithms.run algorithm01 AAPL --start 2010-01-01
python -m algorithms.run algorithm02 NVDA --set target_pct=0.2 adx_min=25
```
```python
from algorithms.run import run
algo, res = run("algorithm03", "AAPL", stoch_max=15, target_pct=0.03)
res.trades, res.equity, res.metrics
```

## Herramientas
- `python -m algorithms.compete [--group validation]`: torneo de todos los algoritmos + buy&hold.
- `python -m algorithms.genetic`: optimiza las variables (genes en `genes.cfg`).
- `python -m algorithms.analyze algorithm03c`: análisis de operaciones (motivo de salida, año, indicadores).
- `ANALISIS.md`: análisis de los 5 mejores y sus versiones mejoradas (`algorithmNN_v1`, `_v2`).

Salidas extra del motor: `stop_pct` (venta a la apertura si el cierre de ayer cayó ese % bajo la entrada) y
metas/stops en múltiplos de ATR (`target_atr_mult`, `stop_atr_mult`).

## Variables editables
Cada algoritmo tiene su `variables.cfg` (sección `[params]`, formato INI con comentarios `#`).
Valores: números, `True`/`False` o `None`. Incluye las comunes (`initial_capital`,
`position_fraction`, `target_pct`, `max_hold_days`, `commission_pct`, `slippage_pct`) y las propias.
Prioridad: argumentos (`--set`, `run(..., x=...)`) > `variables.cfg` > valores de respaldo del
dataclass en `algorithm.py`. Otro archivo: `--cfg ruta/otro.cfg`. Una clave desconocida da error.

## Algoritmo nuevo
Copia una carpeta `algorithmNN/`, cambia su dataclass de parámetros, su `variables.cfg` y `buy_signal`/`sell_signal`
(series booleanas al cierre; `requires` lista las columnas de indicadores que usa).
