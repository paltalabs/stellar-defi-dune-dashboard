-- Query: https://dune.com/queries/8996708
-- Matview: None   cron: None
-- Última ejecución: 01M5MDQ1VEGJ1D8TGWYZD4QKZB
-- Costo: 0.009 cr; filas: 34; engine medium
-- Chart source: migrations per complete calendar month, split by how they happened, wallets (G).
-- same transaction: an app withdrew and deposited in one step; two steps: the wallet did it in two transactions.
SELECT CAST(date_trunc('month', out_day) AS DATE) AS period_start,
       CASE WHEN same_tx THEN 'same transaction (app)' ELSE 'two steps (wallet)' END AS kind,
       COUNT(*) AS migrations, COUNT(DISTINCT user_address) AS addresses, SUM(usd_migrated) AS usd_migrated
FROM dune.paltalabs.result_scf_migrations
WHERE out_day < CAST(date_trunc('month', CURRENT_DATE) AS DATE)
GROUP BY 1, 2 ORDER BY 1, 2
