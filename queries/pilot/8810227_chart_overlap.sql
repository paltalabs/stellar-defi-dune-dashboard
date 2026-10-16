-- Query: https://dune.com/queries/8810227
-- Matview: None   cron: None
-- Última ejecución: 01M357NG0ZMT6KD7BY2WGR8MA7
-- Costo: 0.03 cr; filas: 72; engine medium
-- Chart source: protocol x protocol overlap, all time and last 90 days, off-diagonal pairs.
SELECT window_name, protocol_a, protocol_b, shared_addresses, shared_g_addresses, protocol_a_addresses,
       share_of_a, g_share_of_a
FROM dune.paltalabs.result_scf_overlap_matrix
WHERE window_name IN ('all_time', 'last_90d') AND protocol_a <> protocol_b AND shared_addresses > 0
ORDER BY window_name, share_of_a DESC
