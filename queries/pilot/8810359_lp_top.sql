-- Query: https://dune.com/queries/8810359
-- Matview: dune.paltalabs.result_scf_lp_top   cron: 0 9 * * *
-- Última ejecución: 01M358SPT0468AX10VAA59B7BT
-- Costo: 1.065 cr; filas: 300; engine medium
-- Top 100 LP addresses by USD added, all AMMs, all time and last 90 / 30 complete days.
WITH windows AS (
  SELECT * FROM (VALUES ('all_time', DATE '2024-02-01'),
    ('last_90d', CAST(CURRENT_DATE - INTERVAL '90' DAY AS DATE)),
    ('last_30d', CAST(CURRENT_DATE - INTERVAL '30' DAY AS DATE))) AS t(window_name, window_from)
), per_lp AS (
  SELECT w.window_name, w.window_from, x.user_address,
         SUM(x.usd_total) FILTER (WHERE x.direction = 'add') AS usd_added,
         SUM(x.usd_total) FILTER (WHERE x.direction = 'remove') AS usd_removed,
         COUNT(*) AS lp_actions,
         array_join(array_sort(array_distinct(array_agg(x.protocol))), ', ') AS protocols,
         COUNT(DISTINCT x.pool) AS pools,
         MIN(x.day) AS first_day, MAX(x.day) AS last_day
  FROM dune.paltalabs.result_scf_lp_tx x CROSS JOIN windows w
  WHERE x.day >= w.window_from AND x.day < CURRENT_DATE
  GROUP BY 1, 2, 3
), ranked AS (
  SELECT *, COALESCE(usd_added, 0) - COALESCE(usd_removed, 0) AS usd_net,
         ROW_NUMBER() OVER (PARTITION BY window_name ORDER BY usd_added DESC NULLS LAST, user_address) AS rank_
  FROM per_lp
)
SELECT * FROM ranked WHERE rank_ <= 100 ORDER BY window_name, rank_
