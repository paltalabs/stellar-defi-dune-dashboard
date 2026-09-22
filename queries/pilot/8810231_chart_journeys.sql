-- Query: https://dune.com/queries/8810231
-- Matview: None   cron: None
-- Última ejecución: 01M357NVMMM7GYCF0GD9K77YT4
-- Costo: 0.029 cr; filas: 44; engine medium
-- Chart source: first -> second protocol journeys, excluding addresses that stayed in one protocol.
SELECT from_protocol, to_protocol, addresses, g_addresses, share_of_from, median_days_to_second
FROM dune.paltalabs.result_scf_journeys
WHERE to_protocol <> 'none'
ORDER BY addresses DESC
