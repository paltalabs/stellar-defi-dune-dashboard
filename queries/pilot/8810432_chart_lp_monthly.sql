-- Query: https://dune.com/queries/8810432
-- Matview: None   cron: None
-- Última ejecución: 01M358W1GNB3CA8309X9K21NHZ
-- Costo: 0.038 cr; filas: 145; engine medium
-- Chart source: active LPs and USD added/removed per complete calendar month.
SELECT period_start, protocol, active_lps, g_lps, lp_actions, usd_added, usd_removed, usd_net, priced_action_share
FROM dune.paltalabs.result_scf_lp_periods
WHERE grain = 'month' AND is_complete
ORDER BY period_start, protocol
