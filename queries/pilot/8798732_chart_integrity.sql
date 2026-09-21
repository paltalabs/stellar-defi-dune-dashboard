-- Query: https://dune.com/queries/8798732
-- Matview: None   cron: None
-- Última ejecución: 01M32WX18BJ5NZ3P8NVPAEANJ7
-- Costo: 0.043 cr; filas: 7; engine medium
-- Chart source: activity concentration table, protocols by actions, the total last.
SELECT protocol, actions, share_of_all_actions, addresses, share_of_all_addresses, g_addresses, c_addresses,
       actions_per_address, top10_action_share, addresses_for_90pct_of_actions, contract_action_share,
       COALESCE(router_or_aggregator_action_share, 0) AS router_or_aggregator_action_share, window_from, window_until
FROM dune.paltalabs.result_scf_integrity
ORDER BY CASE WHEN protocol = 'all protocols' THEN 1 ELSE 0 END, actions DESC
