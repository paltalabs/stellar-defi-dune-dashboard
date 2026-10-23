-- Query: https://dune.com/queries/8996709
-- Matview: None   cron: None
-- Última ejecución: 01M5MDQ5YTP9GSR6PRAWSXGE2C
-- Costo: 0.028 cr; filas: 162; engine medium
-- Chart source: two-step migrations per complete calendar month and route, top 6 routes by count, rest as other.
WITH m AS (
  SELECT CAST(date_trunc('month', out_day) AS DATE) AS period_start, from_protocol || ' > ' || to_protocol AS route, user_address, usd_migrated
  FROM dune.paltalabs.result_scf_migrations
  WHERE NOT same_tx AND out_day < CAST(date_trunc('month', CURRENT_DATE) AS DATE)
), top AS (
  SELECT route FROM m GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 6
)
SELECT period_start, CASE WHEN route IN (SELECT route FROM top) THEN route ELSE 'other' END AS route,
       COUNT(*) AS migrations, COUNT(DISTINCT user_address) AS addresses, SUM(usd_migrated) AS usd_migrated
FROM m GROUP BY 1, 2 ORDER BY 1, 2
