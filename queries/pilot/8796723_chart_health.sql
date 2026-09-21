-- Query: https://dune.com/queries/8796723
-- Matview: None   cron: None
-- Última ejecución: 01M32E25A9E8ETC4NF3ST8XPM3
-- Costo: 0.07 cr; filas: 6; engine medium
-- Chart source: coverage and freshness per protocol plus the validation total.
SELECT h.protocol, h.history_from, h.covered_until, h.last_activity_at, h.observed_addresses,
       h.c_addresses, h.live_refreshed_at, h.pipeline_status, h.coverage_note,
       (SELECT SUM(failures) FROM dune.paltalabs.result_scf_users_validation) AS validation_failures
FROM dune.paltalabs.result_scf_users_health h
ORDER BY h.protocol
