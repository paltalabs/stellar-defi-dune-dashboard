-- Query: https://dune.com/queries/8996707
-- Matview: None   cron: None
-- Última ejecución: 01M5MDPXK4K6KYEBVD2M1KAJAP
-- Costo: 0.034 cr; filas: 34; engine medium
-- Chart source: liquidity migrations between protocols (7-day window), all time, wallets (G).
SELECT from_protocol, to_protocol, COUNT(*) AS migrations, COUNT(DISTINCT user_address) AS addresses,
       COUNT_IF(NOT same_tx) AS two_step, COUNT_IF(same_tx) AS same_transaction,
       SUM(usd_migrated) AS usd_migrated, SUM(usd_migrated) FILTER (WHERE NOT same_tx) AS usd_two_step,
       approx_percentile(seconds_between, 0.5) / 3600.0 AS median_hours,
       MIN(out_day) AS first_day, MAX(out_day) AS last_day
FROM dune.paltalabs.result_scf_migrations
GROUP BY 1, 2 ORDER BY migrations DESC
