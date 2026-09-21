-- Query: https://dune.com/queries/8797598
-- Matview: None   cron: None
-- Última ejecución: 01M32KT8Q47VRD19D3H0RR4GNM
-- Costo: 0.009 cr; filas: 16; engine medium
-- Chart source: unique addresses across all six protocols, complete calendar weeks.
SELECT CAST(date_trunc('week', activity_date) AS DATE) AS period_start,
       COUNT(DISTINCT user_address) AS active_addresses,
       COUNT(DISTINCT CASE WHEN user_address LIKE 'G%' THEN user_address END) AS g_addresses,
       COUNT(DISTINCT CASE WHEN user_address LIKE 'C%' THEN user_address END) AS c_addresses
FROM dune.paltalabs.result_scf_users
WHERE row_kind = 'activity' AND activity_date >= DATE '2026-06-01'
  AND activity_date < CAST(date_trunc('week', CURRENT_DATE) AS DATE)
GROUP BY 1
ORDER BY 1
