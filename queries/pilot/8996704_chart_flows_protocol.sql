-- Query: https://dune.com/queries/8996704
-- Matview: None   cron: None
-- Última ejecución: 01M5MDPF7KAY1PQE128JD288N4
-- Costo: 0.037 cr; filas: 168; engine medium
-- Chart source: net liquidity flow per protocol and complete calendar month, wallets (G) only.
SELECT period_start, protocol, usd_in, usd_out, usd_net, addresses
FROM dune.paltalabs.result_scf_flows_periods
WHERE grain = 'month' AND is_complete AND protocol <> 'all protocols' AND pool = 'all' AND flow_type = 'liquidity'
  AND address_type = 'G' AND period_start >= DATE '2024-02-01'
ORDER BY period_start, protocol
