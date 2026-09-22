-- Query: https://dune.com/queries/8796535
-- Matview: dune.paltalabs.result_scf_users_roles_weekly   cron: 0 9 * * *
-- Última ejecución: 01M34ZTSWWD6Z7658K25ZTSCC4
-- Costo: 14.338 cr; filas: 11245; engine medium
-- Calendar weeks in UTC. New = first observed in covered history, not account creation.
WITH metadata AS (
  SELECT protocol, MIN(covered_from) AS history_from, MAX(covered_until) AS covered_until
  FROM dune.paltalabs.result_scf_users WHERE row_kind = 'metadata' GROUP BY 1
), activity AS (
  SELECT protocol, activity_date, user_address, role,
         MIN(activity_date) OVER (PARTITION BY protocol, user_address) AS first_seen
  FROM dune.paltalabs.result_scf_users WHERE row_kind = 'activity'
), grid AS (
  SELECT m.*, period_start, r.role
  FROM metadata m
  CROSS JOIN UNNEST(sequence(CAST(date_trunc('week', history_from) AS DATE),
    CAST(date_trunc('week', covered_until - INTERVAL '1' DAY) AS DATE), INTERVAL '7' DAY)) AS t(period_start)
  CROSS JOIN (SELECT DISTINCT role FROM activity) r
), counts AS (
  SELECT g.protocol, g.period_start,
    (g.period_start >= g.history_from AND date_add('week', 1, g.period_start) <= g.covered_until) AS is_complete
    , g.role,
    COUNT(DISTINCT a.user_address) AS active_addresses,
    COUNT(DISTINCT CASE WHEN a.user_address LIKE 'G%' THEN a.user_address END) AS g_addresses,
    COUNT(DISTINCT CASE WHEN a.user_address LIKE 'C%' THEN a.user_address END) AS c_addresses,
    COUNT(DISTINCT CASE WHEN a.first_seen >= g.period_start THEN a.user_address END) AS new_observed,
    COUNT(DISTINCT CASE WHEN a.first_seen < g.period_start THEN a.user_address END) AS returning_observed,
    MIN(g.history_from) AS history_from, MAX(g.covered_until) AS covered_until
  FROM grid g LEFT JOIN activity a ON a.protocol = g.protocol
    AND a.activity_date >= g.period_start AND a.activity_date < date_add('week', 1, g.period_start) AND a.role = g.role
  GROUP BY 1, 2, 3, 4
), previous AS (
  SELECT *, LAG(active_addresses) OVER (PARTITION BY protocol, role ORDER BY period_start) AS previous_active,
     LAG(is_complete) OVER (PARTITION BY protocol, role ORDER BY period_start) AS previous_complete
  FROM counts
)
SELECT *, CASE WHEN is_complete AND previous_complete AND previous_active > 0
         THEN CAST(active_addresses - previous_active AS DOUBLE) / previous_active END AS growth_rate,
       CASE WHEN is_complete THEN 'Complete' ELSE 'Partial coverage / ongoing' END AS period_status
FROM previous ORDER BY period_start, protocol, role
