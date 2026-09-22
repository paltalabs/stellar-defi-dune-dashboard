-- Query: https://dune.com/queries/8810437
-- Matview: None   cron: None
-- Última ejecución: 01M358WDSER27DE00J9575TVEF
-- Costo: 0.034 cr; filas: 10; engine medium
-- Chart source: LP valuation coverage per protocol.
SELECT * FROM dune.paltalabs.result_scf_lp_price_coverage ORDER BY window_name, protocol
