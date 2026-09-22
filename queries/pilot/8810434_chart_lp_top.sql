-- Query: https://dune.com/queries/8810434
-- Matview: None   cron: None
-- Última ejecución: 01M358W5CKXEX1WWWMQKFV03JS
-- Costo: 0.04 cr; filas: 100; engine medium
-- Chart source: top 100 LPs by USD added, last 90 days.
SELECT rank_, user_address, usd_added, usd_removed, usd_net, lp_actions, protocols, pools, first_day, last_day
FROM dune.paltalabs.result_scf_lp_top WHERE window_name = 'last_90d' ORDER BY rank_
