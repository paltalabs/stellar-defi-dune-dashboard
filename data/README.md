# data/

Listas derivadas de la cadena, con fecha. No son fuente de verdad: se regeneran con las queries
indicadas y sirven para revisar a ojo o para armar `VALUES`.

| Archivo | Qué es | Generado por | Fecha |
|---|---|---|---|
| `aquarius-pools.csv` | Los 400 pools que registraron los tres routers de Aquarius (`add_pool`), con tipo y fee | Dune query 8666314, sondeo de historia completa (37,4 cr, no repetir) | 2026-09-10 |
| `tokens.csv` | Los 356 tokens de las filas de swap y LP: tipo (sac, wasm, classic), asset clásico, símbolo, decimales | `deploy_pilot.py export-tokens` (4 sondeos, ~1,4 cr); SAC sin entrada en `contract_data` derivados con `scripts/sac.py` | 2026-09-22 |
