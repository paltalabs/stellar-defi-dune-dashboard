-- Query: https://dune.com/queries/8797598
-- Matview: None   cron: None
-- Última ejecución: 01M5JZ0DZ684B6YAKN95A6H2RZ
-- Costo: 0.136 cr; filas: 13; engine medium
-- Chart source: unique addresses across all protocols, complete calendar weeks (weeks: the last 13).
SELECT CAST(date_trunc('week', activity_date) AS DATE) AS period_start,
       COUNT(DISTINCT user_address) AS active_addresses,
       COUNT(DISTINCT CASE WHEN user_address LIKE 'G%' THEN user_address END) AS g_addresses,
       COUNT(DISTINCT CASE WHEN user_address LIKE 'C%' THEN user_address END) AS c_addresses
FROM dune.paltalabs.result_scf_users
WHERE row_kind = 'activity' AND activity_date >= date_add('week', -13, CAST(date_trunc('week', CURRENT_DATE) AS DATE))
  AND activity_date < CAST(date_trunc('week', CURRENT_DATE) AS DATE)
GROUP BY 1
ORDER BY 1
