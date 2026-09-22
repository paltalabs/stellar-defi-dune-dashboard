-- Query: https://dune.com/queries/8810219
-- Matview: dune.paltalabs.result_scf_journeys   cron: 0 9 * * *
-- Última ejecución: 01M357M762KE85G7TPRYXRV1GT
-- Costo: 1.061 cr; filas: 52; engine medium
-- First protocol -> second protocol per address (by first day seen). 'none' = never used a second one.
WITH firsts AS (SELECT user_address, protocol, MIN(activity_date) AS first_seen
  FROM dune.paltalabs.result_scf_users WHERE row_kind = 'activity' AND activity_date < CURRENT_DATE GROUP BY 1, 2),
ranked AS (SELECT *, DENSE_RANK() OVER (PARTITION BY user_address ORDER BY first_seen) AS step FROM firsts),
steps AS (
  SELECT user_address, step, MIN(first_seen) AS first_seen,
         CASE WHEN COUNT(*) > 1 THEN 'multiple' ELSE MAX(protocol) END AS protocol
  FROM ranked WHERE step <= 2 GROUP BY 1, 2
), pairs AS (
  SELECT s1.user_address, s1.protocol AS from_protocol, COALESCE(s2.protocol, 'none') AS to_protocol,
         date_diff('day', s1.first_seen, s2.first_seen) AS days_to_second
  FROM steps s1 LEFT JOIN steps s2 ON s2.user_address = s1.user_address AND s2.step = 2
  WHERE s1.step = 1
)
SELECT from_protocol, to_protocol, COUNT(*) AS addresses,
       COUNT_IF(user_address LIKE 'G%') AS g_addresses, COUNT_IF(user_address LIKE 'C%') AS c_addresses,
       CAST(COUNT(*) AS DOUBLE) / SUM(COUNT(*)) OVER (PARTITION BY from_protocol) AS share_of_from,
       approx_percentile(days_to_second, 0.5) AS median_days_to_second
FROM pairs GROUP BY 1, 2 ORDER BY 1, 3 DESC
