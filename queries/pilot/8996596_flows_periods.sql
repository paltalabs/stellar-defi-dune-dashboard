-- Query: https://dune.com/queries/8996596
-- Matview: dune.paltalabs.result_scf_flows_periods   cron: 30 9 * * *
-- Última ejecución: 01M5MBKXX1K3TSSNTAFCHJHAZZ
-- Costo: 1.772 cr; filas: 16194; engine medium
-- Liquidity flows per week and month: in, out and net USD per pool, protocol and ecosystem.
WITH tx AS (SELECT * FROM dune.paltalabs.result_scf_flow_tx WHERE day < CURRENT_DATE),
grains AS (
  SELECT 'week' AS grain, CAST(date_trunc('week', day) AS DATE) AS period_start, * FROM tx
  UNION ALL
  SELECT 'month', CAST(date_trunc('month', day) AS DATE), * FROM tx
), levels AS (
  SELECT grain, period_start, protocol, pool, flow_type, address_type, direction, user_address, usd_value, valuation FROM grains
  UNION ALL
  SELECT grain, period_start, protocol, 'all', flow_type, address_type, direction, user_address, usd_value, valuation FROM grains
  UNION ALL
  SELECT grain, period_start, 'all protocols', 'all', flow_type, address_type, direction, user_address, usd_value, valuation
  FROM grains WHERE address_type = 'G'
)
SELECT grain, period_start, protocol, pool, flow_type, address_type,
       COUNT(DISTINCT user_address) AS addresses,
       COUNT(DISTINCT CASE WHEN direction = 'in' THEN user_address END) AS addresses_in,
       COUNT(DISTINCT CASE WHEN direction = 'out' THEN user_address END) AS addresses_out,
       COUNT_IF(direction = 'in') AS actions_in, COUNT_IF(direction = 'out') AS actions_out,
       SUM(usd_value) FILTER (WHERE direction = 'in') AS usd_in,
       SUM(usd_value) FILTER (WHERE direction = 'out') AS usd_out,
       COALESCE(SUM(usd_value) FILTER (WHERE direction = 'in'), 0) - COALESCE(SUM(usd_value) FILTER (WHERE direction = 'out'), 0) AS usd_net,
       CAST(COUNT_IF(valuation = 'priced') AS DOUBLE) / NULLIF(COUNT_IF(valuation NOT IN ('excluded', 'no_tokens')), 0) AS priced_action_share,
       date_add(grain, 1, period_start) <= CURRENT_DATE AS is_complete
FROM levels GROUP BY 1, 2, 3, 4, 5, 6
