-- Query: https://dune.com/queries/8797131
-- Matview: dune.paltalabs.result_scf_blend_users_history   cron: None
-- Última ejecución: 01M32GD0W14CDFPG8NDAF2CTZ7
-- Costo: 1.065 cr; filas: 44266; engine medium
-- Bootstrap of the history layer from existing matviews. Replaced by the incremental SQL after the first run.
WITH r AS (
  SELECT protocol, activity_date, user_address, role, last_activity_at FROM dune.paltalabs.result_scf_blend_users_live
  WHERE row_kind = 'activity' AND activity_date < DATE '2026-09-19'
)
SELECT protocol, activity_date, user_address, role, last_activity_at, 'activity' AS row_kind,
       DATE '2026-06-01' AS covered_from, DATE '2026-09-19' AS covered_until, CURRENT_TIMESTAMP AS refreshed_at, 'history' AS source_layer
FROM r
UNION ALL
SELECT 'blend', CAST(NULL AS DATE), CAST(NULL AS VARCHAR), CAST(NULL AS VARCHAR),
       CAST(NULL AS TIMESTAMP WITH TIME ZONE), 'metadata', DATE '2026-06-01', DATE '2026-09-19', CURRENT_TIMESTAMP, 'history'
