# Minuta Tranche 2: solapamiento de usuarios y actividad de LPs

SCF #35, Stellar DeFi Dune Dashboards. Entregables 2 (USD 3.333) y 3 (USD 5.000).
Fecha de cierre técnico: 2026-09-22. Estado: construido y validado en Dune; dashboard **privado**
a la espera de revisión y publicación, igual que la T1.

- Dashboard: https://dune.com/paltalabs/stellar-defi (secciones "User overlap between protocols" y
  "Liquidity providers (AMMs)")
- Repositorio: https://github.com/paltalabs/stellar-defi-dune-dashboard, rama `tranche-2`
- Plan y gasto: `plan.md`. Operación: `docs/runbook.md`. Esquema, precios y reglas de
  valorización: `docs/modelo-de-datos.md`.

## 1. Qué pedía la SCF y qué se entrega

| Pide la submission | Entregado | Dónde se ve |
|---|---|---|
| E2: usuarios únicos y solapamiento entre protocolos | Matriz protocolo × protocolo de direcciones compartidas (toda la historia, 90 y 28 días), G por separado | [Protocol overlap](https://dune.com/queries/8810227/12840868) |
| E2: cuántos usuarios usan más de un protocolo | Direcciones por cantidad de protocolos usados, por mes | [Protocols per address](https://dune.com/queries/8810228/12840869) |
| E2: qué protocolos traen direcciones nuevas al ecosistema | Protocolo de entrada de cada dirección, por mes | [Entry protocol](https://dune.com/queries/8810230/12840870) |
| E2: recorridos y sinergias | Del primer protocolo al segundo, con mediana de días | [Journeys](https://dune.com/queries/8810231/12840871) |
| E3: valor por transacción con precios del SDEX y de los DEX Soroban | Cada acción LP valorizada en USD con una tabla de precios diaria propia | [Largest LP actions](https://dune.com/queries/8810435/12841098), tabla `result_scf_lp_tx` |
| E3: wallets LP activas | LPs activos por semana y mes, por protocolo y en todos los AMMs | [Weekly](https://dune.com/queries/8810431/12841094), [Monthly](https://dune.com/queries/8810432/12841093) |
| E3: top LPs | Top 100 por USD agregado (histórico, 90 y 30 días), con protocolos y pools | [Top LPs](https://dune.com/queries/8810434/12841097) |
| E3: cómo mueven capital | USD agregado y flujo neto por protocolo y mes | [Added](https://dune.com/queries/8810432/12841095), [Net](https://dune.com/queries/8810432/12841096) |
| Verificable y que se actualice sola | SQL público y espejado; matviews con cron; validación diaria; cobertura de precios visible | [Valuation coverage](https://dune.com/queries/8810437/12841100) |

## 2. Solapamiento: cómo se mide

Todo sale de `result_scf_users` (grano diario protocolo, día, dirección, rol), la misma tabla de
la T1, sin escanear la cadena otra vez.

1. **Solapamiento.** Para el par (A, B), cuántas direcciones de A usaron también B en la ventana.
   El porcentaje se divide por las direcciones de A, así que la matriz no es simétrica.
2. **Protocolo de entrada.** El protocolo del primer día en que la dirección aparece en cualquiera
   de los siete desde 2024-02-01. Si ese día aparece en dos, es `multiple`. No es la creación de
   la cuenta.
3. **Recorridos.** Del primer protocolo al segundo, cada uno por el primer día visto en él;
   `none` = nunca usó un segundo protocolo.
4. **Contratos intermediarios.** Cuando el aggregator de Soroswap opera en un pool de Aquarius, el
   pool registra al contrato como usuario, y eso crea solapamiento artificial en direcciones C.
   Las columnas solo G son la lectura principal.

Resultado al 2026-09-22: de 78.376 direcciones, el 90,3% usó un solo protocolo, el 8,1% dos y el
1,6% tres o más. Protocolo de entrada: Blend 35.313, Aquarius 27.488, Etherfuse 6.122, Phoenix
4.877, Soroswap 2.616, `multiple` 1.755. El recorrido más frecuente es Aquarius → Blend (3.601
direcciones, mediana 7 días), seguido de Blend → Aquarius (608, 1 día) y Aquarius → Soroswap (555,
167 días).

## 3. LPs: precios y valorización

**Quién es LP.** Las acciones de agregar y retirar liquidez en los AMMs: Aquarius, Soroswap,
Phoenix, SushiSwap y el locking pool de FxDAO. Blend (supply y borrow) no se cuenta como LP;
decisión del 2026-09-22.

**Precios propios** (`result_scf_token_prices`):

1. Tokens: los 356 que aparecen en filas de swap y LP (`data/tokens.csv`). Cada SAC se une a su
   asset clásico; los tokens wasm llevan los decimales de su contrato (hay de 6, 8, 9 y 18).
2. Precio del día: VWAP del SDEX contra USDC de Circle; si no hay USD 50 de volumen, VWAP contra
   XLM por el XLM/USDC del día; si el token no tiene mercado en el SDEX, el precio implícito de
   sus swaps Soroban contra un token con precio SDEX.
3. Cada acción usa el último precio de hasta 7 días antes.

**Reglas de valorización** (columna `usd_method` de `result_scf_lp_tx`): en pools de producto
constante y stable los dos lados de un depósito valen parecido. Si difieren más de 10×, el precio
de un token ilíquido está mal y se cuenta 2 × el lado menor; si un solo lado tiene precio, 2 × ese
lado. SushiSwap (liquidez concentrada) siempre suma los lados, y su `collect` incluye fees.

Resultado al 2026-09-22: entre USD 1,3 y 17,2 M agregados por mes desde junio de 2025, entre 245
y 3.743 LPs activos por mes. El depósito más grande fue de 3 M PYUSD + 3 M USDC en Aquarius
(2025-10-31).

## 4. Arquitectura en Dune

```
diario 05:00  vivas de actividad (T1)
diario 06:00  token_prices: se lee a sí misma y recalcula los últimos 7 días desde el SDEX y las capas
diario 08:00  users (T1)
diario 08:30  lp_tx: acciones LP valorizadas
diario 09:00  solapamiento (4 tablas) y LPs (periods, top, coverage)
diario 10:00  validación, 13 checks
diario 10:30  queries de gráficos (schedule de Dune, a programar en la UI)
```

| Pieza | Query | Matview |
|---|---|---|
| Matriz de solapamiento | [8810202](https://dune.com/queries/8810202) | `result_scf_overlap_matrix` |
| Protocolos por dirección | [8810203](https://dune.com/queries/8810203) | `result_scf_protocol_count` |
| Protocolo de entrada | [8810205](https://dune.com/queries/8810205) | `result_scf_first_protocol` |
| Recorridos | [8810219](https://dune.com/queries/8810219) | `result_scf_journeys` |
| Precios diarios | [8810347](https://dune.com/queries/8810347) | `result_scf_token_prices` |
| Acciones LP en USD | [8810356](https://dune.com/queries/8810356) | `result_scf_lp_tx` |
| LPs por período | [8810357](https://dune.com/queries/8810357) | `result_scf_lp_periods` |
| Top LPs | [8810359](https://dune.com/queries/8810359) | `result_scf_lp_top` |
| Cobertura de precios | [8810360](https://dune.com/queries/8810360) | `result_scf_lp_price_coverage` |

## 5. Validación y verificación

`result_scf_users_validation` pasa de 9 a 13 checks, todos en 0 al 2026-09-22:
`overlap_diagonal_vs_health` (la diagonal de la matriz coincide con la tabla de salud),
`overlap_totals` (entrada, protocolos por dirección y recorridos suman las mismas direcciones
únicas), `unknown_tokens` (todo token de las acciones LP está clasificado) y `lp_tx_vs_layers`
(125.866 acciones LP valorizadas = filas LP de las 14 capas).

Precios contra CoinGecko en 365 días: XLM con desvío mediano de 0,98% (95,3% de los días por debajo
del 5%), AQUA con 0,77% (98,4%). Cobertura de precio de las acciones LP en 90 días: Aquarius 95,6%,
SushiSwap 99,7%, Phoenix 100%, Soroswap 63% (129 acciones; las parciales se valorizan por el lado
con precio).

### Corrección hecha durante la tranche

**Montos de los depósitos directos a pools de Aquarius.** El evento `deposit_liquidity` trae
`[shares, a, b]`, y la capa de la T1 lo leía como `[a, b, shares]`. Se verificó contra las
transferencias de la misma transacción en 7 fechas entre 2024-11 y 2026-09. Afectaba solo los
montos de 66.090 filas, no los usuarios ni ningún gráfico de la T1. Quedó corregido hacia adelante
en la capa viva y en el SQL mensual del archive. La historia anterior a 2026-09-01 se valoriza como
2 × el monto de A, lo que evita reconstruir el archive de Aquarius (~519 cr).

## 6. Diferencias con la submission

- **LP = AMMs.** Blend queda fuera del Entregable 3; sus lenders ya están en la T1 como rol.
- **FxDAO** cuenta LPs activos, pero sin USD: sus operaciones no traen montos por token.
- **Pools de 3 tokens de Aquarius:** el tercer token no se guarda en la capa, así que esas
  acciones quedan subvaluadas.
- **"Runs every 6 hours":** todo refresca una vez al día, como en la T1.

## 7. Costos

| Parte | Créditos |
|---|---|
| Entregable 2 (4 matviews, validación, gráficos) | 12,6 |
| Entregable 3: sondeos (incluye 18,6 de la verificación de Aquarius) | 29,7 |
| Entregable 3: tokens, precios (build 45,5 + incremental 1,7), métricas LP, validación, gráficos | 60,3 |
| Entregable 3: viva de Aquarius con el parser corregido | 22,9 |
| **Total T2** | **125,5** |

Acumulado del proyecto: 2.329,7 cr, con un tope de construcción de 3.500. Recurrente agregado, a
confirmar con las corridas del 2026-09-23: unos 8 cr/día de precios y LPs y entre 4 y 11 cr/día de
solapamiento (`first_protocol` midió 7,98 cr en su primera corrida), es decir, entre ~360 y ~580
cr/mes.

## 8. Pendientes para cerrar la tranche

- **Usuario:** programar en la UI de Dune los 9 gráficos nuevos a las 10:30 UTC (tabla en el runbook).
- **Usuario:** revisar y publicar el dashboard (junto con la T1).
- Medir las corridas diarias del 2026-09-23 (`first_protocol`, `token_prices`, `lp_*`). Si el
  solapamiento cuesta lo que midió, pasar `first_protocol` y `journeys` a semanal, como se hizo con
  `integrity`.
- Si la variación de precios ilíquidos aparece en el top de LPs, bajar `MAX_LEG_RATIO` o subir
  `MIN_USD_VOLUME` en `scripts/prices_sql.py`.
