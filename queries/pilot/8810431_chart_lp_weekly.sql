-- Query: https://dune.com/queries/8810431
-- Matview: None   cron: None
-- Última ejecución: 01M5JYCEMCRCTYS7TYHWA533PK
-- Costo: 0.052 cr; filas: 484; engine medium
-- Chart source: active LPs and USD added/removed per complete calendar week, one row per AMM.
-- Charted as stacked columns: the column is the total and each color one AMM's share. The
-- 'all AMMs' row (unique LPs across AMMs) stays in result_scf_lp_periods, out of the stack.
SELECT period_start, protocol, active_lps, g_lps, lp_actions, usd_added, usd_removed, usd_net, priced_action_share
FROM dune.paltalabs.result_scf_lp_periods
WHERE grain = 'week' AND is_complete AND protocol <> 'all AMMs'
ORDER BY period_start, protocol
