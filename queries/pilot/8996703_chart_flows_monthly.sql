-- Query: https://dune.com/queries/8996703
-- Matview: None   cron: None
-- Última ejecución: 01M5MDPAX1ZSVGCHR1VT07JF7V
-- Costo: 0.045 cr; filas: 31; engine medium
-- Chart source: liquidity in, out and net USD of the ecosystem per complete calendar month, wallets (G) only.
-- usd_out_negative draws withdrawals below the axis.
SELECT period_start, usd_in, -usd_out AS usd_out_negative, usd_out, usd_net, addresses, addresses_in, addresses_out
FROM dune.paltalabs.result_scf_flows_periods
WHERE grain = 'month' AND is_complete AND protocol = 'all protocols' AND pool = 'all' AND flow_type = 'liquidity'
  AND address_type = 'G' AND period_start >= DATE '2024-02-01'
ORDER BY period_start
