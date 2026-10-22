# data/

Listas derivadas de la cadena, con fecha. No son fuente de verdad: se regeneran con las queries
indicadas y sirven para revisar a ojo o para armar `VALUES`.

| Archivo | Qué es | Generado por | Fecha |
|---|---|---|---|
| `aquarius-pools.csv` | Los 400 pools que registraron los tres routers de Aquarius (`add_pool`), con tipo y fee | Dune query 8666314, sondeo de historia completa (37,4 cr, no repetir) | 2026-09-10 |
| `tokens.csv` | Los 364 tokens de las filas de swap y LP: tipo (sac, wasm, classic), asset clásico, símbolo, decimales | `deploy_pilot.py export-tokens` (4 sondeos, ~1,4 cr); SAC sin entrada en `contract_data` derivados con `scripts/sac.py`. Ocho wasm de UltraToken agregados a mano (ver abajo) | 2026-09-22, 2026-10-22 |

Agregados a mano el 2026-10-22: ocho tokens wasm de UltraToken (`ultratoken.xyz`) que aparecieron
en pools de Aquarius desde el 2026-10-08: yUSDT, yUSDC, yBTC, yETH, ySOL, BTC, SOL y ETH. Símbolo y
decimales (6, 8, 9 y 18) leídos de la instancia del contrato por RPC. Guardan su metadata bajo la
llave `Meta`, no `METADATA`, así que `export-tokens` no los lee: si se regenera el archivo, hay que
volver a ponerlos. `layer_rows` es el conteo de filas en `result_scf_lp_tx`, no en las capas. Sus
símbolos repiten los de assets clásicos de otro emisor (`yBTC:GBUVRNH4…` y otros): se cruzan por
contrato, nunca por símbolo. Quedan fuera, a propósito, USDE y SUSDE (`GDJ5BNU5…`, emisor sin
dominio) y BURNMKR (`GB23A2…`): `unknown_tokens` queda en 3.
