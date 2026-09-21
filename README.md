# Stellar DeFi Dune Dashboards

Dashboards públicos en Dune con datos on-chain verificables de los protocolos DeFi de Stellar:
Blend, FxDAO, Soroswap, Aquarius, Phoenix y Etherfuse. Financiado por SCF #35
([submission](scf/submission-scf35.md), [página del proyecto](https://communityfund.stellar.org/project/stellar-defi-dune-dashboards-xn9)).

Dashboard: https://dune.com/paltalabs/stellar-defi, privado hasta revisión (piloto del Entregable 1).

| Archivo | Qué es |
|---|---|
| `plan.md` | Entregables, pasos, presupuesto de créditos y avance. Empezar por acá |
| `protocols.yml` | Contratos de cada protocolo, con fuente y fecha |
| `docs/modelo-de-datos.md` | El esquema único de actividad y cómo se saca el usuario en cada protocolo |
| `docs/runbook.md` | Cómo reconstruir y operar todo en Dune, sin pasos manuales recurrentes |
| `queries/<protocolo>/` | Espejo de cada query de Dune, con costo medido en la cabecera |
| `queries/pilot/`, `pilot.json` | Piloto T1: SQL de cada pieza, ids, ejecuciones, costos y visualizaciones |
| `scripts/` | `pilot_sql.py` genera el SQL, `deploy_pilot.py` lo despliega, `dune_mcp.py` habla con Dune |
| `.github/workflows/` | Re-ejecución diaria de las queries de gráficos |
| `data/` | Listas derivadas de la cadena (pools), con fecha |
| `scf/` | La submission tal cual fue aprobada |

Principios: nadie lo mantiene a mano, barato, reconstruible por cualquiera desde este repo.
Detalle en `CLAUDE.md`.
