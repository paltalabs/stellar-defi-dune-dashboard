-- Query: https://dune.com/queries/8996702
-- Matview: None   cron: None
-- Última ejecución: 01M5MDP6X1QWK8Y5VNWZ0GX2GR
-- Costo: 0.035 cr; filas: 13; engine medium
-- Chart source: liquidity in, out and net USD of the ecosystem per complete calendar week, wallets (G) only.
-- usd_out_negative draws withdrawals below the axis.
SELECT period_start, usd_in, -usd_out AS usd_out_negative, usd_out, usd_net, addresses, addresses_in, addresses_out
FROM dune.paltalabs.result_scf_flows_periods
WHERE grain = 'week' AND is_complete AND protocol = 'all protocols' AND pool = 'all' AND flow_type = 'liquidity'
  AND address_type = 'G' AND period_start >= date_add('week', -13, CAST(date_trunc('week', CURRENT_DATE) AS DATE))
ORDER BY period_start
