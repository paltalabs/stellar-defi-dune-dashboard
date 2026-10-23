-- Query: https://dune.com/queries/8996706
-- Matview: None   cron: None
-- Última ejecución: 01M5MDPSG1MYPRW0DDDHMWZ918
-- Costo: 0.032 cr; filas: 31; engine medium
-- Chart source: borrowed and repaid USD per lending protocol and complete calendar month, G and C.
SELECT period_start, protocol, SUM(usd_out) AS usd_borrowed, SUM(usd_in) AS usd_repaid,
       COALESCE(SUM(usd_in), 0) - COALESCE(SUM(usd_out), 0) AS usd_net_repaid,
       SUM(addresses) AS addresses
FROM dune.paltalabs.result_scf_flows_periods
WHERE grain = 'month' AND is_complete AND protocol <> 'all protocols' AND pool = 'all' AND flow_type = 'credit'
GROUP BY 1, 2 ORDER BY 1, 2
