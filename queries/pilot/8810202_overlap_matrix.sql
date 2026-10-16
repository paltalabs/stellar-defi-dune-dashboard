-- Query: https://dune.com/queries/8810202
-- Matview: dune.paltalabs.result_scf_overlap_matrix   cron: 0 9 * * *
-- Última ejecución: 01M357H6521J49DTYFGAC7SSXX
-- Costo: 1.078 cr; filas: 123; engine medium
-- Protocol x protocol shared addresses, all time and last 90/28 complete UTC days.
WITH windows AS (
  SELECT * FROM (VALUES ('all_time', DATE '2024-02-01'),
    ('last_90d', CAST(CURRENT_DATE - INTERVAL '90' DAY AS DATE)),
    ('last_28d', CAST(CURRENT_DATE - INTERVAL '28' DAY AS DATE))) AS t(window_name, window_from)
), pa AS (
  SELECT DISTINCT w.window_name, w.window_from, u.protocol, u.user_address
  FROM dune.paltalabs.result_scf_users u CROSS JOIN windows w
  WHERE u.row_kind = 'activity' AND u.activity_date >= w.window_from AND u.activity_date < CURRENT_DATE
), totals AS (
  SELECT window_name, protocol, COUNT(*) AS protocol_addresses,
         COUNT_IF(user_address LIKE 'G%') AS protocol_g_addresses
  FROM pa GROUP BY 1, 2
), pairs AS (
  SELECT a.window_name, a.window_from, a.protocol AS protocol_a, b.protocol AS protocol_b,
         COUNT(*) AS shared_addresses, COUNT_IF(a.user_address LIKE 'G%') AS shared_g_addresses
  FROM pa a JOIN pa b ON a.window_name = b.window_name AND a.user_address = b.user_address
  GROUP BY 1, 2, 3, 4
)
SELECT p.window_name, p.window_from, CURRENT_DATE AS window_until, p.protocol_a, p.protocol_b,
       p.shared_addresses, p.shared_g_addresses, p.shared_addresses - p.shared_g_addresses AS shared_c_addresses,
       t.protocol_addresses AS protocol_a_addresses, t.protocol_g_addresses AS protocol_a_g_addresses,
       CAST(p.shared_addresses AS DOUBLE) / t.protocol_addresses AS share_of_a,
       CAST(p.shared_g_addresses AS DOUBLE) / NULLIF(t.protocol_g_addresses, 0) AS g_share_of_a
FROM pairs p JOIN totals t ON t.window_name = p.window_name AND t.protocol = p.protocol_a
ORDER BY 1, 4, 5
