-- Query: https://dune.com/queries/8913375
-- Matview: ninguna (gráfico, schedule de Dune)
-- Última ejecución: 01M4C26GWXK4XQA8R8TCYRQ9SE
-- Costo: 0.325 cr; filas: 9; engine medium
-- Chart source: active addresses per protocol in the last complete calendar week and month (UTC).
-- Soroswap appears as its two products and as a total: unique addresses across AMM and aggregator.
WITH wp AS (SELECT MAX(period_start) AS p FROM dune.paltalabs.result_scf_users_weekly WHERE is_complete),
mp AS (SELECT MAX(period_start) AS p FROM dune.paltalabs.result_scf_users_monthly WHERE is_complete),
w AS (
  SELECT protocol, active_addresses, g_addresses FROM dune.paltalabs.result_scf_users_weekly
  WHERE is_complete AND period_start = (SELECT p FROM wp)
), m AS (
  SELECT protocol, active_addresses, g_addresses FROM dune.paltalabs.result_scf_users_monthly
  WHERE is_complete AND period_start = (SELECT p FROM mp)
), s AS (
  SELECT 'soroswap_total' AS protocol,
    COUNT(DISTINCT CASE WHEN activity_date >= (SELECT p FROM wp) AND activity_date < date_add('day', 7, (SELECT p FROM wp)) THEN user_address END) AS last_week_active,
    COUNT(DISTINCT CASE WHEN activity_date >= (SELECT p FROM wp) AND activity_date < date_add('day', 7, (SELECT p FROM wp)) AND user_address LIKE 'G%' THEN user_address END) AS last_week_g,
    COUNT(DISTINCT CASE WHEN activity_date >= (SELECT p FROM mp) AND activity_date < date_add('month', 1, (SELECT p FROM mp)) THEN user_address END) AS last_month_active,
    COUNT(DISTINCT CASE WHEN activity_date >= (SELECT p FROM mp) AND activity_date < date_add('month', 1, (SELECT p FROM mp)) AND user_address LIKE 'G%' THEN user_address END) AS last_month_g
  FROM dune.paltalabs.result_scf_users
  WHERE row_kind = 'activity' AND protocol IN ('soroswap_amm', 'soroswap_aggregator')
    AND activity_date >= LEAST((SELECT p FROM wp), (SELECT p FROM mp))
)
SELECT m.protocol, COALESCE(w.active_addresses, 0) AS last_week_active, COALESCE(w.g_addresses, 0) AS last_week_g,
       m.active_addresses AS last_month_active, m.g_addresses AS last_month_g
FROM m LEFT JOIN w ON w.protocol = m.protocol
UNION ALL
SELECT protocol, last_week_active, last_week_g, last_month_active, last_month_g FROM s
ORDER BY last_month_active DESC
