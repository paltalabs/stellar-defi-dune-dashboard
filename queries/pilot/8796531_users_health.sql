-- Query: https://dune.com/queries/8796531
-- Matview: dune.paltalabs.result_scf_users_health   cron: 0 9 * * *
-- Última ejecución: 01M32KRKBXR861DX9JD0DPFRF7
-- Costo: 1.027 cr; filas: 6; engine medium
WITH metadata AS (
  SELECT protocol, MIN(covered_from) AS history_from, MAX(covered_until) AS covered_until,
         MAX(refreshed_at) FILTER (WHERE source_layer = 'live') AS live_refreshed_at,
         MIN(refreshed_at) AS oldest_layer_refresh
  FROM dune.paltalabs.result_scf_users WHERE row_kind = 'metadata' GROUP BY 1
), activity AS (
  SELECT protocol, MAX(last_activity_at) AS last_activity_at,
         COUNT(DISTINCT user_address) AS observed_addresses,
         COUNT(DISTINCT CASE WHEN user_address LIKE 'C%' THEN user_address END) AS c_addresses
  FROM dune.paltalabs.result_scf_users WHERE row_kind = 'activity' GROUP BY 1
)
SELECT m.*, a.last_activity_at, COALESCE(a.observed_addresses, 0) AS observed_addresses,
       COALESCE(a.c_addresses, 0) AS c_addresses,
       date_diff('hour', m.live_refreshed_at, CURRENT_TIMESTAMP) AS refresh_age_hours,
       CASE WHEN date_diff('hour', m.live_refreshed_at, CURRENT_TIMESTAMP) > 36
              OR covered_until < CURRENT_DATE - INTERVAL '1' DAY THEN 'STALE'
            ELSE 'OK' END AS pipeline_status,
       CASE WHEN m.protocol = 'etherfuse' THEN 'Historical since 2024-02-01 + daily live'
            ELSE 'Pilot since 2026-06-01; historical archive pending' END AS coverage_note
FROM metadata m LEFT JOIN activity a ON m.protocol = a.protocol ORDER BY m.protocol
