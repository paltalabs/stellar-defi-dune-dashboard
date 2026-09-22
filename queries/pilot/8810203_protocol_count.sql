-- Query: https://dune.com/queries/8810203
-- Matview: dune.paltalabs.result_scf_protocol_count   cron: 0 9 * * *
-- Última ejecución: 01M357HGSSBW591P6EMD73DP75
-- Costo: 1.237 cr; filas: 119; engine medium
-- How many protocols each address used: all time, last 28 complete days, complete calendar months.
WITH u AS (SELECT protocol, activity_date, user_address FROM dune.paltalabs.result_scf_users WHERE row_kind = 'activity' AND activity_date < CURRENT_DATE),
per_period AS (
  SELECT 'all_time' AS period_kind, DATE '2024-02-01' AS period_start, user_address,
         COUNT(DISTINCT protocol) AS protocols_used
  FROM u GROUP BY 3
  UNION ALL
  SELECT 'last_28d', CAST(CURRENT_DATE - INTERVAL '28' DAY AS DATE), user_address, COUNT(DISTINCT protocol)
  FROM u WHERE activity_date >= CURRENT_DATE - INTERVAL '28' DAY GROUP BY 3
  UNION ALL
  SELECT 'month', CAST(date_trunc('month', activity_date) AS DATE), user_address, COUNT(DISTINCT protocol)
  FROM u WHERE activity_date < CAST(date_trunc('month', CURRENT_DATE) AS DATE) GROUP BY 2, 3
), buckets AS (
  SELECT period_kind, period_start,
         CASE WHEN protocols_used >= 4 THEN '4+' ELSE CAST(protocols_used AS VARCHAR) END AS protocols_used,
         COUNT(*) AS addresses, COUNT_IF(user_address LIKE 'G%') AS g_addresses,
         COUNT_IF(user_address LIKE 'C%') AS c_addresses
  FROM per_period GROUP BY 1, 2, 3
)
SELECT *, CAST(addresses AS DOUBLE) / SUM(addresses) OVER (PARTITION BY period_kind, period_start) AS share_of_addresses,
       CAST(g_addresses AS DOUBLE) / NULLIF(SUM(g_addresses) OVER (PARTITION BY period_kind, period_start), 0) AS share_of_g_addresses
FROM buckets ORDER BY 1, 2, 3
