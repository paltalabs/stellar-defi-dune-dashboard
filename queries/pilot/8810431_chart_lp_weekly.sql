-- Query: https://dune.com/queries/8810431
-- Matview: None   cron: None
-- Última ejecución: 01M358VXKPTS7487ZZ1S8673ZE
-- Costo: 0.036 cr; filas: 600; engine medium
-- Chart source: active LPs and USD added/removed per complete calendar week.
SELECT period_start, protocol, active_lps, g_lps, lp_actions, usd_added, usd_removed, usd_net, priced_action_share
FROM dune.paltalabs.result_scf_lp_periods
WHERE grain = 'week' AND is_complete
ORDER BY period_start, protocol
