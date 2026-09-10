# Runbook: reconstruir y operar

Cualquier persona con acceso al team `paltalabs` en Dune puede reconstruir todo desde este repo.
No hay nada fuera de Dune y de este repo. No hay pasos manuales recurrentes.

## Piezas

```
por protocolo:
  SCF35 · <protocolo> activity archive   query, no temporal, sin parámetros
      └─ result_scf_<protocolo>_activity_archive   matview, cron mensual (1 de cada mes, 03:00 UTC)
  SCF35 · <protocolo> activity           query: lee la tabla cruda solo desde MAX(closed_at) del archive
      └─ result_scf_<protocolo>_activity           matview, cron diario (05:00 UTC)
capa común:
  SCF35 · activity (all protocols)       UNION ALL de las 12 matviews de arriba
      └─ result_scf_activity                       matview, cron diario (05:30 UTC)
dashboard:
  SCF35 · <métrica>                      queries de análisis: solo leen result_scf_activity
      └─ result_scf_<métrica>                      matview, cron diario (06:00 UTC), o cada 6 h si se decide pagarlo
```

Por qué así: el refresh de una matview re-ejecuta su query y actualiza el resultado que muestran
los widgets, y su cron se crea por API. Los schedules de queries en la UI no se ven por API y se
pierden si nadie los recuerda.

## Crear una pieza nueva

1. Crear la query en Dune con el SQL del repo. `is_temp: false`. Nombre con prefijo `SCF35 ·`.
2. Ejecutar en engine medium. Anotar filas y `executionCostCredits` en la cabecera del archivo SQL.
3. `createMaterializedView` con el nombre `result_scf_...` y el cron de la tabla de arriba.
   Esperar a que termine la primera ejecución antes de crear consumidores.
4. Guardar el SQL en `queries/<protocolo>/<query_id>_<slug>.sql` con la cabecera estándar.
5. Marcar el paso en `plan.md`. Commit.

## Espejar el SQL al repo

`scripts/mirror.py` baja el SQL de cada query de `queries.yml` por la API REST de Dune y escribe
`queries/<protocolo>/<id>_<slug>.sql` con la cabecera. Necesita `DUNE_API_KEY` con permiso de
lectura de queries. **Al 2026-09-10 las dos llaves que tenemos devolvieron `invalid API Key`
en `GET /api/v1/query/{id}`** (la del MCP y la del dataroom), así que los espejos de hoy se
escribieron a mano desde el texto enviado a Dune. Pendiente: generar en Dune una API key del
team y probar de nuevo; hasta entonces, después de cada `updateDuneQuery` hay que copiar el SQL
al archivo.

## Cabecera estándar de cada SQL

```
-- Query: SCF35 · <nombre>          https://dune.com/queries/<id>
-- Matview: dune.paltalabs.result_scf_<...>   cron: <expresión>   (o "ninguna")
-- Lee: <tablas crudas o matviews>
-- Costo medido: <fecha> <créditos> cr, <filas> filas, engine medium
-- Notas:
```

## Si algo se rompe

- **Un protocolo cambia el formato de un evento o despliega un contrato nuevo.** La query se
  queda ciega en silencio. Señal: la fila de ese protocolo en el widget "last event per protocol"
  del dashboard se atrasa. Arreglo: actualizar `protocols.yml`, el `VALUES` de la query, y
  refrescar el archive una vez.
- **El archive falla un mes.** La ventana viva sigue desde el último `MAX(closed_at)` del archive,
  así que no hay hueco mientras la ventana viva no supere su filtro de poda (`current_date - 75 días`).
  Si pasó más de eso, refrescar el archive a mano una vez.
- **Se quiere apagar todo.** Quitar el cron de las matviews (`updateMaterializedView` con
  `cron_expression: null`). Las tablas quedan congeladas y el dashboard sigue mostrando la última foto.

## Rodar el corte a mano

No hace falta. El archive se refresca solo cada mes con historia completa; el costo de eso es el
precio de no tener pasos manuales (ver `plan.md`, presupuesto).
