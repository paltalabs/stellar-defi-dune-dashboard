-- Query: https://dune.com/queries/8810357
-- Matview: dune.paltalabs.result_scf_lp_periods   cron: 0 9 * * *
-- Última ejecución: 01M358RZ76VZAM2GCZ6XXJV1JD
-- Costo: 2.842 cr; filas: 754; engine medium
-- Active LPs and USD added/removed per calendar week and month (UTC), per protocol and all AMMs.
WITH tx AS (SELECT * FROM dune.paltalabs.result_scf_lp_tx WHERE day < CURRENT_DATE),
grains AS (
  SELECT 'week' AS grain, CAST(date_trunc('week', day) AS DATE) AS period_start, * FROM tx
  UNION ALL
  SELECT 'month', CAST(date_trunc('month', day) AS DATE), * FROM tx
), both_ AS (
  SELECT grain, period_start, protocol, user_address, direction, usd_total, valuation FROM grains
  UNION ALL
  SELECT grain, period_start, 'all AMMs', user_address, direction, usd_total, valuation FROM grains
)
SELECT grain, period_start, protocol,
       COUNT(DISTINCT user_address) AS active_lps,
       COUNT(DISTINCT CASE WHEN user_address LIKE 'G%' THEN user_address END) AS g_lps,
       COUNT(DISTINCT CASE WHEN user_address LIKE 'C%' THEN user_address END) AS c_lps,
       COUNT(*) AS lp_actions,
       SUM(usd_total) FILTER (WHERE direction = 'add') AS usd_added,
       SUM(usd_total) FILTER (WHERE direction = 'remove') AS usd_removed,
       COALESCE(SUM(usd_total) FILTER (WHERE direction = 'add'), 0) - COALESCE(SUM(usd_total) FILTER (WHERE direction = 'remove'), 0) AS usd_net,
       CAST(COUNT_IF(valuation = 'priced') AS DOUBLE) / COUNT(*) AS priced_action_share,
       date_add(grain, 1, period_start) <= CURRENT_DATE AS is_complete
FROM both_ GROUP BY 1, 2, 3
ORDER BY 1, 2, 3
