-- Query: https://dune.com/queries/8797135
-- Matview: dune.paltalabs.result_scf_phoenix_users_history   cron: None
-- Última ejecución: 01M32GDK1BM4Z1SD4QHJDCRQ83
-- Costo: 1.025 cr; filas: 1235; engine medium
-- Bootstrap of the history layer from existing matviews. Replaced by the incremental SQL after the first run.
WITH r AS (
  SELECT protocol, activity_date, user_address, role, last_activity_at FROM dune.paltalabs.result_scf_phoenix_users_live
  WHERE row_kind = 'activity' AND activity_date < DATE '2026-09-19'
)
SELECT protocol, activity_date, user_address, role, last_activity_at, 'activity' AS row_kind,
       DATE '2026-06-01' AS covered_from, DATE '2026-09-19' AS covered_until, CURRENT_TIMESTAMP AS refreshed_at, 'history' AS source_layer
FROM r
UNION ALL
SELECT 'phoenix', CAST(NULL AS DATE), CAST(NULL AS VARCHAR), CAST(NULL AS VARCHAR),
       CAST(NULL AS TIMESTAMP WITH TIME ZONE), 'metadata', DATE '2026-06-01', DATE '2026-09-19', CURRENT_TIMESTAMP, 'history'
