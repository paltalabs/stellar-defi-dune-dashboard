# Modelo de datos

Una sola tabla normalizada por protocolo, con el mismo esquema en todos. Los cuatro entregables
de la SCF se calculan encima de ella, así que las tablas crudas de Stellar se escanean una vez
por período y no una vez por gráfico.

## Esquema de `result_scf_<protocolo>_activity` (y su `_archive`)

| Columna | Tipo | Qué es |
|---|---|---|
| `protocol` | varchar | `blend`, `fxdao`, `soroswap`, `aquarius`, `phoenix`, `etherfuse`, `sushiswap` |
| `contract_id` | varchar | contrato que emitió el evento o recibió la invocación |
| `closed_at` | timestamp | cierre del ledger |
| `tx_hash` | varchar | hash hex en minúsculas, `lower(to_hex(transaction_hash))` |
| `user_address` | varchar | la cuenta o contrato que actuó. G = wallet, C = contrato |
| `action` | varchar | verbo del protocolo tal cual (`swap`, `supply`, `borrow`, `backstop_deposit`...) |
| `role` | varchar | segmento: `swapper`, `lp`, `lender`, `borrower`, `liquidator`, `backstop_provider`, `aggregator_user`, `claimer`, `holder`, `trader`, `minter`, `redeemer`, `vault_owner` |
| `pool` | varchar | pool, vault o mercado donde ocurrió, si aplica |
| `token_a` | varchar | token de entrada o token A |
| `amount_a` | decimal(38,7) | en unidades del token, 7 decimales |
| `token_b` | varchar | token de salida o token B |
| `amount_b` | decimal(38,7) | ídem |
| `row_kind` | varchar | `activity` (una acción) o `metadata` (una fila por capa con el rango cubierto, existe aunque el protocolo no tenga actividad) |
| `covered_from`, `covered_until` | date | rango cubierto por la capa: `[covered_from, covered_until)` |
| `refreshed_at` | timestamp | cuándo corrió la capa |
| `source_layer` | varchar | `archive` o `live` |

Generado por `scripts/activity_sql.py` (Fase 1, 2026-09-22). El archive cubre desde
2024-02-01 (SushiSwap desde 2026-03-01, el mes de su factory) hasta el primer día del mes en curso; la viva, desde el `covered_until` del archive
(con poda literal de 75 días) hasta ayer. Las dos capas no se solapan, así que la unión no
deduplica.

Reglas:

- Una fila por acción de usuario. Eventos administrativos (`set_status`, `gulp_emissions`,
  `reserve_emission_update`, `config_rewards`...) se descartan: no tienen usuario.
- `SELECT DISTINCT` sobre el grano del evento antes de parsear: Dune duplica cada evento de
  `stellar.history_contract_events` (medido: `events = 2 × txs` en todos los protocolos).
- Los contratos también cuentan como usuarios (bots, vaults de DeFindex, el aggregator). El
  dashboard separa `G` de `C` para mostrar wallets reales vs contratos.
- Filtros obligatorios en la tabla de eventos: `type_string = 'ContractEventTypeContract'`
  (los `fn_call`/`fn_return` son diagnósticos), `successful`, `in_successful_contract_call`, y
  siempre `closed_at_date` para podar particiones.

## Cómo se obtiene el usuario en cada protocolo

Verificado con sondeos de 7 y 30 días el 2026-09-10 (queries 8666280, 8666378, y siguientes).

| Protocolo | Fuente | Dónde está el usuario | Acciones y roles |
|---|---|---|---|
| Blend | eventos de pools y backstops | pools: topics `[action, asset, from]` → `from`. `fill_auction`: `data.vec[0]` (el liquidador). `claim`: topics `[claim, from]`. Backstop: `[action, pool, from]` | `supply`, `withdraw`, `supply_collateral`, `withdraw_collateral` → lender · `borrow`, `repay`, `flash_loan` → borrower · `fill_auction` → liquidator · backstop `deposit`, `withdraw`, `queue_withdrawal`, `dequeue_withdrawal`, `donate` → backstop_provider |
| Aquarius | eventos de los 3 routers **y de los 431 pools** (corregido 2026-09-21: en 7 días, 736 de 904 depósitos y 71.851 de 113.543 trades ocurrían en pools sin evento del router) | router: topics `[action, vec[tokens], user]` → tercer topic. Pool `trade`: topics `[trade, token_in, token_out, caller]`, se descarta cuando el caller es un router (el evento del router trae al usuario). Pool `claim_reward`: `topics[2]`. Pool `position_update`: `topics[1]`. `deposit_liquidity`/`withdraw_liquidity` no traen usuario: se usa el `source_account` de la operación que invoca al pool (solo operaciones directas al pool) | `swap`, `pool_trade` → swapper · `deposit`, `withdraw`, `pool_deposit`, `pool_withdraw`, `position_update` → lp · `claim`, `claim_reward` → claimer |
| Soroswap | eventos del router, los pares y las 10 versiones del aggregator; **y el aggregator por el SDEX** (desde 2026-09-22): `stellar.history_transactions` exitosas con memo `SoroswapAggregator%` y sus path payments en `stellar.history_operations`, mismo criterio que `paltalabs/dune-dashboards` (queries 8395684 y 8395746) | Soroban: `data.map.to`, **un registro por evento** (antes se pivoteaba por transacción y varias swaps de una tx quedaban en una con un solo destinatario). SDEX: la cuenta de la transacción y, si es distinta, el receptor (`to`) del path payment, en una fila sin montos para no duplicar volumen. Tokens SDEX como `native` o `CODE:ISSUER`, montos ya en unidades | `SoroswapRouter swap` y `SoroswapPair swap` → swapper · `deposit`, `withdraw` de pares → lp · `SoroswapAggregator swap`, `aggregator_sdex_swap`, `aggregator_sdex_recipient` → aggregator_user |
| Phoenix | eventos de los pools (registro desde el storage de la factory) | Formato nuevo: un evento por acción con `data.map`, pivoteado por evento. Formato viejo: N eventos por acción con topics `["swap","sender"]`...; se agrupa por `(pool, tx_hash, action)` y, si en ese grupo hay más de un `sender`, cada uno queda como fila sin montos en vez de fundirlos | `swap` → swapper · `provide_liquidity`, `withdraw_liquidity` → lp |
| FxDAO | `stellar.history_operations` (los contratos no emiten eventos útiles) | `source_account`; la función en `parameters_json_decoded[1].symbol` | vaults: `new_vault`, `increase_collateral`, `increase_debt`, `pay_debt`, `redeem`, `liquidate` → vault_owner / redeemer / liquidator · locking pool: `deposit`, `withdraw` → lp |
| SushiSwap | eventos de los 58 pools (CLMM estilo Uniswap v3; verificado el 2026-09-22 con 30 días) | `swap`: `data.map.sender`, también cuando rutea el router (el router pasa la wallet como `sender`; su propio evento no se lee). Montos con signo: positivo entra al pool (304 de 304 swaps de un salto coinciden con el `amount_in` del router). `mint`: `sender` (51 de 51 igual al firmante cuando se invoca directo el position manager). `collect`: `recipient`. `burn` no se lee: no trae usuario, va en otra transacción que su `collect` y no mueve tokens; los tokens salen del pool en el `collect` | `swap` → swapper · `add_liquidity` (mint), `collect` → lp |
| Etherfuse | `stellar.history_operations` y `stellar.history_trades` filtradas por el issuer | `source_account`, `from`, `to`, cuentas de cada trade | payment desde el issuer → minter (el receptor) · payment hacia el issuer → redeemer · otros payments → holder · trades → trader |

## Descubrimiento de pools

`result_scf_contracts` (query `SCF35 · contract registry`, cron lunes 02:00 UTC) descubre los
pools desde el storage de las factories y desde los eventos `add_pool` de los routers de
Aquarius. El primer escaneo desde 2024 costó 78,9 cr; desde entonces se lee a sí mismo y solo
mira los últimos 14 días (3,9 cr). Al 2026-09-22: 27 pools de Blend, 214 pares de Soroswap,
14 pools de Phoenix, 431 de Aquarius (31 más que la lista de septiembre) y 58 de SushiSwap.

Las queries de actividad llevan esas listas **literales**, generadas desde `data/contracts.csv`
(`deploy_pilot.py export-registry`). Un `IN (subquery)` no poda particiones: la misma consulta
costó 0,198 cr con subquery y 0,057 con lista literal. El check `unregistered_contracts` de
`result_scf_users_validation` da mayor que 0 cuando el registro encuentra un contrato que el SQL
todavía no incluye; el arreglo es `export-registry` y volver a desplegar las capas.

| Protocolo | Dónde | Forma |
|---|---|---|
| Blend | factories v1 y v2 | key `{"vec":[{"symbol":"Contracts"},{"address":"<pool>"}]}`, 15 pools v1 y 12 v2 al 2026-09-10 |
| Phoenix | factory | key `map{token_a, token_b[, pool_type]}` → val `{"address":"<pool>"}` |
| Aquarius | routers, eventos `add_pool` | la dirección del pool en `data`; `data/aquarius-pools.csv` es la lista vieja de septiembre |
| Soroswap | factory | key `{"vec":[{"symbol":"PairAddressesNIndexed"},...]}` → val `{"address":"<pair>"}` |
| SushiSwap | factory | key `{"vec":[{"symbol":"GetPool"},{"address":"<token>"},{"address":"<token>"},{"u32":<fee>}]}` → val `{"address":"<pool>"}`, dos entradas por pool (una por orden). `token_a` = token0 = el de bytes de dirección menores (`from_base32`; 58 de 58 contra el `params.token0` de cada pool, el orden de texto falla en 3). Se escanea siempre desde 2026-03-01 (0,08 cr). 58 pools al 2026-09-22, iguales a los de stellar.expert |

## Montos y precios

Los montos quedan en unidades del token (7 decimales). En SushiSwap aparecen swaps con montos
crudos de 19 y 20 dígitos, lo que sugiere tokens con más de 7 decimales (no verificado). La capa de
precios del Entregable 3 tiene que leer los decimales de cada token antes de valorizar. El precio en USD se agrega en la capa de
análisis, para el entregable 3, con una tabla de precios diaria propia y acotada a los tokens
que efectivamente aparecen (patrón del repo dune-dashboards: 8 assets cuestan 1,35 cr/día; 70
tokens costaban 825).

## Integridad: qué mide "usuarios activos" y dónde leerlo bien

Observación del 2026-09-22: en los gráficos Soroswap parecía tener más actividad que Aquarius,
aunque Aquarius mueve mucho más volumen y TVL. Las dos cosas son ciertas a la vez, y la forma
correcta de leerlo es la tabla `result_scf_integrity` ("Activity concentration by protocol" en el
dashboard):

- **Direcciones no es volumen.** WAU/MAU cuentan direcciones distintas. Un AMM puede tener mucho
  volumen con pocas direcciones (bots de arbitraje y market making). La tabla muestra, en los
  últimos 28 días, acciones por dirección, la participación del top 10 y cuántas direcciones
  hacen el 90% de las acciones.
- **Los contratos intermedios cuentan como un usuario.** Cuando el aggregator de Soroswap (o un
  router) opera en un pool de otro protocolo, el evento del pool registra al contrato, no a la
  persona. Esa persona se cuenta en el protocolo donde firmó (Soroswap, `aggregator_user`) y en
  el pool aparece un solo usuario C. La columna `router_or_aggregator_action_share` mide cuánto
  de la actividad de cada protocolo llega así.
- **El aggregator por el SDEX no emite eventos Soroban.** Esos swaps se leen por el memo de la
  transacción (`SoroswapAggregator-<apiUser>`). Una transacción Soroban lleva una sola operación,
  así que ninguna transacción cae en las dos vías; una misma dirección que usa las dos se cuenta
  una vez por el `COUNT DISTINCT`. El memo es texto libre y se acepta como criterio. Al
  2026-09-22 sumó 1.888 direcciones a Soroswap, 970 de ellas ausentes de todos los protocolos.
- **Para comparar protocolos entre sí**, lo correcto es la columna de acciones y la de
  concentración, no solo WAU. Para "cuánta gente usa el ecosistema", el WAU/MAU del ecosistema
  (direcciones únicas entre protocolos) y separar G de C.
- El volumen en USD es del Entregable 3 (necesita precios) y no está en esta tabla.

## Solapamiento entre protocolos (Entregable 2)

Cuatro tablas sobre `result_scf_users`, sin tablas crudas (`scripts/pilot_sql.py`):

- `result_scf_overlap_matrix`: para cada par (A, B), cuántas direcciones de A también usaron B, en
  toda la historia y en los últimos 90 y 28 días. La diagonal son las direcciones de A (el check
  `overlap_diagonal_vs_health` la compara con la tabla de salud). La matriz no es simétrica en
  porcentaje: `share_of_a` se divide por las direcciones de A.
- `result_scf_protocol_count`: cuántos protocolos usó cada dirección (1, 2, 3, 4+).
- `result_scf_first_protocol`: el protocolo de entrada es el del primer día en que la dirección
  aparece en cualquiera de los siete desde 2024-02-01. Si ese día aparece en dos, es `multiple`.
  No es la creación de la cuenta, y SushiSwap solo puede ser de entrada desde 2026-03.
- `result_scf_journeys`: del primer protocolo al segundo, por primer día visto en cada uno;
  `none` = nunca usó un segundo protocolo.

Las cuatro suman las mismas direcciones únicas (check `overlap_totals`). Los contratos
intermediarios generan solapamiento artificial: un pool de Aquarius que recibe un swap del
aggregator de Soroswap registra al contrato como usuario de Aquarius. Por eso las columnas solo G
son la lectura principal.

## Precios (Entregable 3)

`result_scf_token_prices` (`scripts/prices_sql.py`) guarda un precio en USD por día y token, solo
los días con precio observado (sin relleno).

- **Tokens.** `data/tokens.csv` lista cada token de las filas de swap y LP. Un SAC se une a su
  asset clásico (`CODE:ISSUER` o `native`): primero por `asset_code`/`asset_issuer` de
  `stellar.contract_data`, y si su instancia es anterior a 2024 (XLM, sUSD), con el id derivado
  offline en `scripts/sac.py` (sha256 del preimage `FROM_ASSET`, validado 253 de 253). Los tokens
  wasm llevan los decimales de su METADATA: hay tokens de 6, 8, 9 y 18 decimales, y las capas
  guardan `raw * 1e-7`, así que el monto real es `amount * 10^(7 - decimals)`.
- **Fuente.** VWAP diario del SDEX (`stellar.history_trades`) contra USDC de Circle; si ese día no
  hay USD 50 de volumen contra USDC, VWAP contra XLM por el XLM/USDC del día. Los tokens sin
  mercado en el SDEX toman el precio implícito de sus swaps Soroban de las capas contra un token
  con precio SDEX (`price_source = soroban_swaps`), con el mismo mínimo de volumen.
- **Operación.** El build escanea el SDEX desde 2024-02-01 (45,5 cr). Después la matview se lee a
  sí misma y recalcula los últimos 7 días (1,73 cr por día).
- **Verificación.** Contra CoinGecko en 365 días: XLM, desvío mediano 0,98%; AQUA, 0,77%.

## LPs (Entregable 3)

LP son las acciones con `role = 'lp'` de los AMMs: Aquarius, Soroswap, Phoenix, SushiSwap y el
locking pool de FxDAO. Blend (supply/borrow) no cuenta como LP. `result_scf_lp_tx` valoriza cada
acción con el último precio de hasta 7 días antes:

| Acción | Dirección |
|---|---|
| `deposit`, `pool_deposit`, `provide_liquidity`, `add_liquidity`, `locking_deposit` | add |
| `withdraw`, `pool_withdraw`, `withdraw_liquidity`, `remove_liquidity`, `locking_withdraw`, `collect` | remove |
| `position_update` (Aquarius, sin tokens) | other |

Reglas de valorización (`usd_method`):

- `sum`: suma de los dos lados. Es la regla normal y la única en SushiSwap: en liquidez
  concentrada, una posición de un solo lado es legítima. En Sushi, `collect` incluye los fees ganados.
- `capped_2x_min`: en pools de producto constante o stable, los dos lados valen parecido. Si
  difieren más de 10×, el precio de un token ilíquido está mal y cuenta 2 × el menor.
- `one_leg_2x`: si un solo lado tiene precio, cuenta 2 × ese lado.
- `legacy_2x_a`: los `pool_deposit` de Aquarius anteriores a 2026-09-01 se leyeron como `[a, b,
  shares]` cuando el evento es `[shares, a, b]`. En esas filas `amount_a` son shares y `amount_b`
  es el monto de A; se valorizan como 2 × A. Desde 2026-09-01 la capa guarda los montos correctos.
  El tercer token de los pools de 3 tokens no se guarda.

FxDAO no trae montos por token en sus operaciones: sus acciones cuentan como LP activo, sin USD.
