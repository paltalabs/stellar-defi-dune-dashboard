-- Query: https://dune.com/queries/8796540
-- Matview: dune.paltalabs.result_scf_users_validation   cron: 0 10 * * *
-- Última ejecución: 01M32KRTAVPJRJARGKRC3XVTHT
-- Costo: 2.822 cr; filas: 8; engine medium
WITH users AS (SELECT * FROM dune.paltalabs.result_scf_users WHERE row_kind = 'activity'),
duplicate_keys AS (
  SELECT protocol, activity_date, user_address, role, COUNT(*) AS n
  FROM users GROUP BY 1,2,3,4 HAVING COUNT(*) > 1
)
SELECT 'duplicate_daily_keys' AS check_name, COALESCE(SUM(n - 1), 0) AS failures FROM duplicate_keys
UNION ALL
SELECT 'invalid_addresses', COUNT(*) FROM users WHERE NOT regexp_like(user_address, '^[GC][A-Z2-7]{55}$')
UNION ALL
SELECT 'invalid_role_or_date', COUNT(*) FROM users WHERE role IS NULL OR activity_date IS NULL
UNION ALL
SELECT 'out_of_coverage', COUNT(*) FROM users WHERE activity_date < covered_from OR activity_date >= covered_until
UNION ALL
SELECT 'missing_protocol_metadata', 6 - COUNT(DISTINCT protocol)
FROM dune.paltalabs.result_scf_users WHERE row_kind = 'metadata'
UNION ALL
SELECT 'history_live_gap', COUNT(*) FROM (
  SELECT protocol FROM dune.paltalabs.result_scf_users WHERE row_kind = 'metadata'
  GROUP BY 1
  HAVING MAX(covered_until) FILTER (WHERE source_layer = 'history') IS NULL
      OR MAX(covered_until) FILTER (WHERE source_layer = 'history') < MAX(covered_from) FILTER (WHERE source_layer = 'live')
)
UNION ALL
SELECT 'cohort_partition_weekly', COUNT(*) FROM dune.paltalabs.result_scf_users_weekly
WHERE new_observed + returning_observed <> active_addresses OR g_addresses + c_addresses <> active_addresses
UNION ALL
SELECT 'cohort_partition_monthly', COUNT(*) FROM dune.paltalabs.result_scf_users_monthly
WHERE new_observed + returning_observed <> active_addresses OR g_addresses + c_addresses <> active_addresses
