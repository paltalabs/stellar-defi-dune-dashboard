# Runbook: reconstruir y operar

Cualquier persona con acceso al team `paltalabs` en Dune puede reconstruir todo desde este repo.
Ids, ejecuciones y costos de cada pieza están en `pilot.json`; el SQL lo genera
`scripts/activity_sql.py` (capas de actividad, registro, unión, integridad) y
`scripts/pilot_sql.py` (métricas, validación, gráficos); `scripts/deploy_pilot.py` lo despliega.

## Piezas (Fase 1, 2026-09-22)

```
registro:
  SCF35 · contract registry            result_scf_contracts              lunes 02:00   incremental, se lee a sí mismo
por protocolo (blend, aquarius, soroswap, phoenix, fxdao, etherfuse, sushiswap):
  SCF35 · <P> activity archive         result_scf_<p>_activity_archive   lunes 03:00   historia desde 2024-02-01 (sushiswap desde 2026-03-01) hasta el 1 del mes
  SCF35 · <P> activity                 result_scf_<p>_activity           diario 05:00  desde el covered_until del archive hasta ayer
capa común y métricas:
  SCF35 · users                        result_scf_users                  diario 08:00  grano diario (protocolo, día, dirección, rol) desde las 12 capas
  SCF35 · users weekly / monthly / roles weekly / roles monthly / health, activity concentration
                                       result_scf_users_*                                diario 09:00
  SCF35 · activity concentration       result_scf_integrity              lunes 09:00   ventana de 28 días; semanal desde 2026-09-22
solapamiento (Entregable 2, desde 2026-09-22):
  SCF35 · protocol overlap matrix / protocols per address / entry protocol / protocol journeys
                                       result_scf_overlap_matrix, _protocol_count, _first_protocol, _journeys   diario 09:00
  SCF35 · users validation             result_scf_users_validation       diario 10:00
gráficos:
  queries SCF35 · ... que hacen SELECT sobre las matviews, con schedule de Dune a las 10:30 (ver abajo)
```

### Por qué el archive corre cada lunes y no cada mes

Dune rechaza crons de matview mensuales (`Unsupported cron expression`; el máximo es semanal).
El archive corre cada lunes y se lee a sí mismo: el primer lunes del mes agrega el mes que
cerró desde las tablas crudas; los demás lunes la condición `day_of_month(CURRENT_DATE) <= 7`
es falsa, Dune no escanea (medido: 0,01 cr contra 0,66) y la tabla se copia igual. El primer
build sí escanea toda la historia. Repetir un escaneo completo es un paso a mano: `activity-archive
<p>` con el SQL de build y volver a `activity-archive-incremental <p>`.

### Cadena diaria

05:00 vivas → 08:00 users → 09:00 métricas e integridad → 10:00 validación → 10:30 gráficos.
Dune no garantiza orden entre matviews; los horarios dejan margen. La tabla de salud marca
`STALE` si la viva no corrió en 36 h.

## Gráficos: schedule de Dune (excepción a la regla 1)

El refresco de una matview deja en su query origen solo `{"rows": N}` (verificado 2026-09-21),
así que un widget sobre esa query no muestra datos. Los widgets cuelgan de queries propias
que hacen SELECT sobre las matviews, y esas queries necesitan un schedule. La API y el MCP de
Dune no pueden crear, leer ni restaurar schedules de queries, por eso esto se hace a mano y
queda anotado acá. Decidido con el usuario el 2026-09-22.

En cada query, `Schedule` → diario → 10:30 UTC → engine medium:

| Query | Qué alimenta |
|---|---|
| https://dune.com/queries/8796723 | Data coverage and pipeline health |
| https://dune.com/queries/8797598 | WAU across all protocols (G y C) |
| https://dune.com/queries/8797599 | MAU across all protocols (G y C) |
| https://dune.com/queries/8796719 | WAU, crecimiento WoW, nuevos vs recurrentes por protocolo |
| https://dune.com/queries/8796720 | MAU, crecimiento MoM, nuevos vs recurrentes por protocolo |
| https://dune.com/queries/8796721 | WAU por rol |
| https://dune.com/queries/8796722 | MAU por rol |
| https://dune.com/queries/8798732 | Activity concentration by protocol (integridad) |
| https://dune.com/queries/8810227 | Protocol overlap (Entregable 2) |
| https://dune.com/queries/8810228 | Addresses by number of protocols used |
| https://dune.com/queries/8810230 | New ecosystem addresses by entry protocol |
| https://dune.com/queries/8810231 | User journeys, first to second protocol |

Costo medido: unos 0,5 cr por corrida de las 8 de la T1; las 4 del solapamiento suman 0,13 cr. `python3 scripts/deploy_pilot.py refresh-charts`
hace lo mismo por API si hace falta refrescarlas a mano.

## Reconstruir desde cero

Orden exacto (cada paso espera la primera ejecución del anterior):

1. `python3 scripts/deploy_pilot.py registry` crea el registro (primer build 78,9 cr) y
   `export-registry` escribe `data/contracts.csv`. Después, `registry` otra vez deja el SQL
   incremental. La rama de SushiSwap escanea siempre desde 2026-03-01 (0,08 cr), también en el
   incremental.
2. Por protocolo: `test-activity <p> <día>` (1 día, barato), `activity-archive <p>` (build
   completo), `activity-archive-incremental <p>` (SQL que se lee a sí mismo), `activity-live <p>`.
3. `metric users`, luego `metric users_weekly`, `users_monthly`, `users_roles_weekly`,
   `users_roles_monthly`, `users_health`, `integrity`, `overlap_matrix`, `protocol_count`,
   `first_protocol`, `journeys`, y al final `metric users_validation` (sus checks de solapamiento
   leen esas cuatro tablas).
4. `chart <clave>` para cada gráfico, schedule en la UI (tabla de arriba), visualizaciones y
   dashboard (ids en `pilot.json` → `visualizations` y `dashboard_after_layout`).

Cualquier ejecución que supere `execution_alert_credits` de `pilot.json` detiene el script. El
tope de construcción está en `construction_cap_credits`.

## Espejar el SQL al repo

`deploy_pilot.py` escribe el SQL de cada pieza al crearla o cambiarla, con cabecera y último
costo: capas de actividad en `queries/<protocolo>/<id>_activity[_archive].sql`, el resto en
`queries/pilot/`. Antes de cambiar una query compara el SQL remoto con el último desplegado y se
detiene si alguien la cambió fuera del repo. `getDuneQuery` se lee por REST
(`GET /api/v1/query/{id}`): la llave actual funciona (verificado 2026-09-21) y el MCP devolvía
cuerpos vacíos.

## Agregar un protocolo

Así se agregó SushiSwap el 2026-09-22 (84,5 cr en total, detalle en `plan.md`):

1. Sondeos temporales `[SCF35 probe]`: storage de la factory, formas de evento, de dónde sale el
   usuario. Cruzar la lista de pools con una fuente externa (stellar.expert).
2. Rama del protocolo en `registry_scan` y fuente en `activity_sql.py` (`SOURCES`, `PROTOCOLS` y,
   si el protocolo es posterior a 2024, su inicio en `HISTORY_STARTS`).
3. `registry` (actualiza el SQL, refresca y exporta `data/contracts.csv`).
4. `activity-archive <p>`, `activity-archive-incremental <p>`, `activity-live <p>` (una viva
   nueva crea su query; solo los protocolos del paso 1 reusan la suya).
5. `metric users`, las métricas, `integrity` y `metric users_validation` (el check
   `missing_protocol_metadata` cuenta `PROTOCOLS`). Después `refresh-charts` y el texto del
   dashboard.

## Si algo se rompe

- **Un protocolo despliega un pool nuevo.** El registro lo encuentra el lunes y el check
  `unregistered_contracts` pasa a mayor que 0. Arreglo: `export-registry`, y volver a desplegar
  `activity-archive-incremental <p>` y `activity-live <p>` (el SQL lleva la lista literal).
- **Un protocolo cambia el formato de un evento.** La fila de ese protocolo en la tabla de salud
  se atrasa. Arreglo: actualizar la fuente en `activity_sql.py` y reconstruir el archive completo.
- **El archive falla el primer lunes del mes.** La viva sigue desde el `covered_until` viejo
  (hasta 75 días); el check `archive_live_gap` avisa si se pasa de eso.
- **Se quiere apagar todo.** `set-cron <clave> none` en cada matview. Las tablas quedan
  congeladas y el dashboard muestra la última foto.

## Piezas retiradas

El piloto T1 del 2026-09-21 (`result_scf_<p>_users_live`, `result_scf_<p>_users_history`,
`result_scf_etherfuse_users_archive`) quedó reemplazado por las capas de actividad. Sus matviews
quedan sin cron y su SQL en `queries/pilot/`.
