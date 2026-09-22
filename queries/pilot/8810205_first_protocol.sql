-- Query: https://dune.com/queries/8810205
-- Matview: dune.paltalabs.result_scf_first_protocol   cron: 0 9 * * *
-- Última ejecución: 01M357HWPNVMHKJEGMWZR89YHC
-- Costo: 7.979 cr; filas: 177; engine medium
-- Entry protocol of each address into the covered ecosystem (first day seen since 2024-02-01).
-- Seen in two protocols on its first day -> 'multiple'. Not account creation.
WITH firsts AS (SELECT user_address, protocol, MIN(activity_date) AS first_seen
  FROM dune.paltalabs.result_scf_users WHERE row_kind = 'activity' AND activity_date < CURRENT_DATE GROUP BY 1, 2),
eco AS (SELECT user_address, MIN(first_seen) AS eco_first_seen, COUNT(*) AS protocols_used FROM firsts GROUP BY 1),
entry AS (
  SELECT e.user_address, e.eco_first_seen, e.protocols_used,
         CASE WHEN COUNT(*) > 1 THEN 'multiple' ELSE MAX(f.protocol) END AS entry_protocol
  FROM eco e JOIN firsts f ON f.user_address = e.user_address AND f.first_seen = e.eco_first_seen
  GROUP BY 1, 2, 3
)
SELECT CAST(date_trunc('month', eco_first_seen) AS DATE) AS entry_month, entry_protocol,
       COUNT(*) AS new_ecosystem_addresses,
       COUNT_IF(user_address LIKE 'G%') AS g_addresses, COUNT_IF(user_address LIKE 'C%') AS c_addresses,
       COUNT_IF(protocols_used > 1) AS used_other_protocols_later,
       CAST(date_trunc('month', eco_first_seen) AS DATE) < CAST(date_trunc('month', CURRENT_DATE) AS DATE) AS is_complete
FROM entry GROUP BY 1, 2 ORDER BY 1, 2
