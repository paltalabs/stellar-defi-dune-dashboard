-- Query: https://dune.com/queries/8796720
-- Matview: None   cron: None
-- Última ejecución: 01M32E1RC8F2KPZ1MNH59TREF6
-- Costo: 0.033 cr; filas: 18; engine medium
-- Chart source: complete calendar months since the common pilot start, one row per protocol.
SELECT period_start, protocol, active_addresses, g_addresses, c_addresses,
       new_observed, returning_observed, growth_rate
FROM dune.paltalabs.result_scf_users_monthly
WHERE is_complete AND period_start >= DATE '2026-06-01'
ORDER BY period_start, protocol
