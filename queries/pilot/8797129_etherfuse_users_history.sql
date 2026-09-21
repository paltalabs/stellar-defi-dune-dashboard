-- Query: https://dune.com/queries/8797129
-- Matview: dune.paltalabs.result_scf_etherfuse_users_history   cron: None
-- Última ejecución: 01M32GCNVE64FPXEV9M295TNH1
-- Costo: 1.17 cr; filas: 55611; engine medium
-- Bootstrap of the history layer from existing matviews. Replaced by the incremental SQL after the first run.
WITH r AS (
  SELECT protocol, activity_date, user_address, role, last_activity_at FROM dune.paltalabs.result_scf_etherfuse_users_live
  WHERE row_kind = 'activity' AND activity_date < DATE '2026-09-19'
  UNION ALL
  SELECT protocol, activity_date, user_address, role, last_activity_at
  FROM dune.paltalabs.result_scf_etherfuse_users_archive
  WHERE row_kind = 'activity' AND activity_date < (SELECT MAX(covered_from) FROM dune.paltalabs.result_scf_etherfuse_users_live WHERE row_kind = 'metadata')
)
SELECT protocol, activity_date, user_address, role, last_activity_at, 'activity' AS row_kind,
       DATE '2024-02-01' AS covered_from, DATE '2026-09-19' AS covered_until, CURRENT_TIMESTAMP AS refreshed_at, 'history' AS source_layer
FROM r
UNION ALL
SELECT 'etherfuse', CAST(NULL AS DATE), CAST(NULL AS VARCHAR), CAST(NULL AS VARCHAR),
       CAST(NULL AS TIMESTAMP WITH TIME ZONE), 'metadata', DATE '2024-02-01', DATE '2026-09-19', CURRENT_TIMESTAMP, 'history'
