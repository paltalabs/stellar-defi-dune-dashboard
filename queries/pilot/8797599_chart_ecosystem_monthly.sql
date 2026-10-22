-- Query: https://dune.com/queries/8797599
-- Matview: None   cron: None
-- Última ejecución: 01M5JZ0MDRNMBCP1WK3W96XQHA
-- Costo: 0.044 cr; filas: 31; engine medium
-- Chart source: unique addresses across all protocols, complete calendar months (weeks: the last 13).
SELECT CAST(date_trunc('month', activity_date) AS DATE) AS period_start,
       COUNT(DISTINCT user_address) AS active_addresses,
       COUNT(DISTINCT CASE WHEN user_address LIKE 'G%' THEN user_address END) AS g_addresses,
       COUNT(DISTINCT CASE WHEN user_address LIKE 'C%' THEN user_address END) AS c_addresses
FROM dune.paltalabs.result_scf_users
WHERE row_kind = 'activity' AND activity_date >= DATE '2024-02-01'
  AND activity_date < CAST(date_trunc('month', CURRENT_DATE) AS DATE)
GROUP BY 1
ORDER BY 1
