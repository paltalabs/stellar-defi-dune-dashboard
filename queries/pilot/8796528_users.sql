-- Query: https://dune.com/queries/8796528
-- Matview: dune.paltalabs.result_scf_users   cron: 0 8 * * *
-- Última ejecución: 01M4BZJ762FBXPCW247X8MCRBA
-- Costo: 1.322 cr; filas: 772318; engine medium
-- Daily user grain derived from the normalized activity layers. Soroswap is split into
-- soroswap_amm and soroswap_aggregator by role.
WITH act AS (
SELECT protocol, closed_at, user_address, role, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_blend_activity_archive WHERE row_kind = 'activity'
UNION ALL
SELECT protocol, closed_at, user_address, role, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_blend_activity WHERE row_kind = 'activity'
UNION ALL
SELECT protocol, closed_at, user_address, role, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_aquarius_activity_archive WHERE row_kind = 'activity'
UNION ALL
SELECT protocol, closed_at, user_address, role, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_aquarius_activity WHERE row_kind = 'activity'
UNION ALL
SELECT protocol, closed_at, user_address, role, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_soroswap_activity_archive WHERE row_kind = 'activity'
UNION ALL
SELECT protocol, closed_at, user_address, role, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_soroswap_activity WHERE row_kind = 'activity'
UNION ALL
SELECT protocol, closed_at, user_address, role, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_phoenix_activity_archive WHERE row_kind = 'activity'
UNION ALL
SELECT protocol, closed_at, user_address, role, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_phoenix_activity WHERE row_kind = 'activity'
UNION ALL
SELECT protocol, closed_at, user_address, role, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_fxdao_activity_archive WHERE row_kind = 'activity'
UNION ALL
SELECT protocol, closed_at, user_address, role, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_fxdao_activity WHERE row_kind = 'activity'
UNION ALL
SELECT protocol, closed_at, user_address, role, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_etherfuse_activity_archive WHERE row_kind = 'activity'
UNION ALL
SELECT protocol, closed_at, user_address, role, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_etherfuse_activity WHERE row_kind = 'activity'
UNION ALL
SELECT protocol, closed_at, user_address, role, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_sushiswap_activity_archive WHERE row_kind = 'activity'
UNION ALL
SELECT protocol, closed_at, user_address, role, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_sushiswap_activity WHERE row_kind = 'activity'
), meta AS (
SELECT protocol, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_blend_activity_archive WHERE row_kind = 'metadata'
UNION ALL
SELECT protocol, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_blend_activity WHERE row_kind = 'metadata'
UNION ALL
SELECT protocol, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_aquarius_activity_archive WHERE row_kind = 'metadata'
UNION ALL
SELECT protocol, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_aquarius_activity WHERE row_kind = 'metadata'
UNION ALL
SELECT protocol, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_soroswap_activity_archive WHERE row_kind = 'metadata'
UNION ALL
SELECT protocol, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_soroswap_activity WHERE row_kind = 'metadata'
UNION ALL
SELECT protocol, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_phoenix_activity_archive WHERE row_kind = 'metadata'
UNION ALL
SELECT protocol, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_phoenix_activity WHERE row_kind = 'metadata'
UNION ALL
SELECT protocol, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_fxdao_activity_archive WHERE row_kind = 'metadata'
UNION ALL
SELECT protocol, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_fxdao_activity WHERE row_kind = 'metadata'
UNION ALL
SELECT protocol, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_etherfuse_activity_archive WHERE row_kind = 'metadata'
UNION ALL
SELECT protocol, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_etherfuse_activity WHERE row_kind = 'metadata'
UNION ALL
SELECT protocol, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_sushiswap_activity_archive WHERE row_kind = 'metadata'
UNION ALL
SELECT protocol, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_sushiswap_activity WHERE row_kind = 'metadata'
)
SELECT CASE WHEN protocol = 'soroswap' THEN CASE WHEN role = 'aggregator_user' THEN 'soroswap_aggregator' ELSE 'soroswap_amm' END ELSE protocol END AS protocol, CAST(closed_at AT TIME ZONE 'UTC' AS DATE) AS activity_date, user_address, role,
       MAX(closed_at) AS last_activity_at, 'activity' AS row_kind,
       covered_from, covered_until, MAX(refreshed_at) AS refreshed_at, source_layer
FROM act
GROUP BY 1, 2, 3, 4, 7, 8, 10
UNION ALL
SELECT p, CAST(NULL AS DATE), CAST(NULL AS VARCHAR), CAST(NULL AS VARCHAR),
       CAST(NULL AS TIMESTAMP WITH TIME ZONE), 'metadata', covered_from, covered_until, refreshed_at, source_layer
FROM meta
CROSS JOIN UNNEST(CASE WHEN protocol = 'soroswap' THEN ARRAY['soroswap_amm', 'soroswap_aggregator'] ELSE ARRAY[protocol] END) AS t(p)
