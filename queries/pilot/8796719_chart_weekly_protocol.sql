-- Query: https://dune.com/queries/8796719
-- Matview: None   cron: None
-- Última ejecución: 01M32E1M01SNXQPYAHDH80WJKT
-- Costo: 0.03 cr; filas: 96; engine medium
-- Chart source: complete calendar weeks since the common pilot start, one row per protocol.
SELECT period_start, protocol, active_addresses, g_addresses, c_addresses,
       new_observed, returning_observed, growth_rate
FROM dune.paltalabs.result_scf_users_weekly
WHERE is_complete AND period_start >= DATE '2026-06-01'
ORDER BY period_start, protocol
