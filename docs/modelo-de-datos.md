# Modelo de datos

Una sola tabla normalizada por protocolo, con el mismo esquema en todos. Los cuatro entregables
de la SCF se calculan encima de ella, así que las tablas crudas de Stellar se escanean una vez
por período y no una vez por gráfico.

## Esquema de `result_scf_<protocolo>_activity` (y su `_archive`)

| Columna | Tipo | Qué es |
|---|---|---|
| `protocol` | varchar | `blend`, `fxdao`, `soroswap`, `aquarius`, `phoenix`, `etherfuse` |
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
| Aquarius | eventos del ROUTER (los pools no hace falta enumerarlos) | topics `[action, vec[tokens], user]` → tercer topic. `data.vec[0]` es el pool | `swap` → swapper · `deposit`, `withdraw` → lp · `claim` → claimer |
| Soroswap | eventos del router, los pares y las 10 versiones del aggregator | `data.map.to` | `SoroswapRouter swap` y `SoroswapPair swap` → swapper · `deposit`, `withdraw` de pares → lp · `SoroswapAggregator swap` → aggregator_user |
| Phoenix | eventos de los pools (registro desde el storage de la factory) | N eventos por acción con topics `["swap","sender"]`, `["provide_liquidity","sender"]`, `["withdraw_liquidity","sender"]`; el usuario está en `data.address` del evento `sender`. Se agrupa por `(pool, tx_hash, action)` | `swap` → swapper · `provide_liquidity`, `withdraw_liquidity` → lp |
| FxDAO | `stellar.history_operations` (los contratos no emiten eventos útiles) | `source_account`; la función en `parameters_json_decoded[1].symbol` | vaults: `new_vault`, `increase_collateral`, `increase_debt`, `pay_debt`, `redeem`, `liquidate` → vault_owner / redeemer / liquidator · locking pool: `deposit`, `withdraw` → lp |
| Etherfuse | `stellar.history_operations` y `stellar.history_trades` filtradas por el issuer | `source_account`, `from`, `to`, cuentas de cada trade | payment desde el issuer → minter (el receptor) · payment hacia el issuer → redeemer · otros payments → holder · trades → trader |

## Descubrimiento de pools

Se hace dentro de cada query, desde `stellar.contract_data` filtrado por el contrato factory
(0,3 créditos por escaneo completo, medido). Así aparecen solos los pools nuevos.

| Protocolo | Dónde | Forma |
|---|---|---|
| Blend | factories v1 y v2 | key `{"vec":[{"symbol":"Contracts"},{"address":"<pool>"}]}`, 15 pools v1 y 12 v2 al 2026-09-10 |
| Phoenix | factory | key `map{token_a, token_b[, pool_type]}` → val `{"address":"<pool>"}` |
| Aquarius | no hace falta: el router emite todo | los 400 pools quedaron en `data/aquarius-pools.csv` para T3 |
| Soroswap | factory | pendiente de verificar en el storage; hoy la lista vive en `result_soroswap_pools_filtered_tokens` del repo dune-dashboards |

## Montos y precios

Los montos quedan en unidades del token (7 decimales). El precio en USD se agrega en la capa de
análisis, para el entregable 3, con una tabla de precios diaria propia y acotada a los tokens
que efectivamente aparecen (patrón del repo dune-dashboards: 8 assets cuestan 1,35 cr/día; 70
tokens costaban 825).
