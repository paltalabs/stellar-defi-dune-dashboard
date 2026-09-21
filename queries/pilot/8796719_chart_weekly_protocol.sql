-- Query: https://dune.com/queries/8796719
-- Matview: None   cron: None
-- Última ejecución: 01M32WXRXF94W1W1CAPNMRF5J3
-- Costo: 0.037 cr; filas: 822; engine medium
-- Chart source: complete calendar weeks since 2024-02-01, one row per protocol.
SELECT period_start, protocol, active_addresses, g_addresses, c_addresses,
       new_observed, returning_observed, growth_rate
FROM dune.paltalabs.result_scf_users_weekly
WHERE is_complete AND period_start >= DATE '2024-02-01'
ORDER BY period_start, protocol
