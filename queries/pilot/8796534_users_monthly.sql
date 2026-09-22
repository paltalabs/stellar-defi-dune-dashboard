-- Query: https://dune.com/queries/8796534
-- Matview: dune.paltalabs.result_scf_users_monthly   cron: 0 9 * * *
-- Última ejecución: 01M34ZTHSFA7R76BJ394PQFH6Q
-- Costo: 1.131 cr; filas: 199; engine medium
-- Calendar months in UTC. New = first observed in covered history, not account creation.
WITH metadata AS (
  SELECT protocol, MIN(covered_from) AS history_from, MAX(covered_until) AS covered_until
  FROM dune.paltalabs.result_scf_users WHERE row_kind = 'metadata' GROUP BY 1
), activity AS (
  SELECT protocol, activity_date, user_address, role,
         MIN(activity_date) OVER (PARTITION BY protocol, user_address) AS first_seen
  FROM dune.paltalabs.result_scf_users WHERE row_kind = 'activity'
), grid AS (
  SELECT m.*, period_start
  FROM metadata m
  CROSS JOIN UNNEST(sequence(CAST(date_trunc('month', history_from) AS DATE),
    CAST(date_trunc('month', covered_until - INTERVAL '1' DAY) AS DATE), INTERVAL '1' MONTH)) AS t(period_start)
  
), counts AS (
  SELECT g.protocol, g.period_start,
    (g.period_start >= g.history_from AND date_add('month', 1, g.period_start) <= g.covered_until) AS is_complete
    ,
    COUNT(DISTINCT a.user_address) AS active_addresses,
    COUNT(DISTINCT CASE WHEN a.user_address LIKE 'G%' THEN a.user_address END) AS g_addresses,
    COUNT(DISTINCT CASE WHEN a.user_address LIKE 'C%' THEN a.user_address END) AS c_addresses,
    COUNT(DISTINCT CASE WHEN a.first_seen >= g.period_start THEN a.user_address END) AS new_observed,
    COUNT(DISTINCT CASE WHEN a.first_seen < g.period_start THEN a.user_address END) AS returning_observed,
    MIN(g.history_from) AS history_from, MAX(g.covered_until) AS covered_until
  FROM grid g LEFT JOIN activity a ON a.protocol = g.protocol
    AND a.activity_date >= g.period_start AND a.activity_date < date_add('month', 1, g.period_start)
  GROUP BY 1, 2, 3
), previous AS (
  SELECT *, LAG(active_addresses) OVER (PARTITION BY protocol ORDER BY period_start) AS previous_active,
     LAG(is_complete) OVER (PARTITION BY protocol ORDER BY period_start) AS previous_complete
  FROM counts
)
SELECT *, CASE WHEN is_complete AND previous_complete AND previous_active > 0
         THEN CAST(active_addresses - previous_active AS DOUBLE) / previous_active END AS growth_rate,
       CASE WHEN is_complete THEN 'Complete' ELSE 'Partial coverage / ongoing' END AS period_status
FROM previous ORDER BY period_start, protocol
