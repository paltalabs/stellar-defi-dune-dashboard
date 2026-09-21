-- Query: https://dune.com/queries/8798252
-- Matview: dune.paltalabs.result_scf_contracts   cron: 0 2 * * 1
-- Última ejecución: 01M32SX3Z2ABHJ7Q1ERVCPV0ZF
-- Costo: 3.904 cr; filas: 686; engine medium
-- Contract registry, incremental: previous snapshot of this matview + contracts seen in the last 14 days.
WITH prev AS (SELECT protocol, kind, contract_id, token_a, token_b, first_seen FROM dune.paltalabs.result_scf_contracts),
fresh AS (
-- Contract registry discovered on chain. Source of data/contracts.csv, which feeds the literal
-- contract lists of every activity query (a literal list prunes; an IN (subquery) does not).
SELECT 'blend' AS protocol, 'pool' AS kind, json_extract_scalar(key_decoded, '$.vec[1].address') AS contract_id,
       CAST(NULL AS VARCHAR) AS token_a, CAST(NULL AS VARCHAR) AS token_b, MIN(closed_at) AS first_seen
FROM stellar.contract_data
WHERE contract_id IN ('CCZD6ESMOGMPWH2KRO4O7RGTAPGTUPFWFQBELQSS7ZUK63V3TZWETGAG', 'CDSYOAVXFY7SM5S64IZPPPYB4GVGGLMQVFREPSQQEZVIWXX5R23G4QSU') AND closed_at_date >= CURRENT_DATE - INTERVAL '14' DAY
  AND contract_key_type = 'ScValTypeScvVec' AND json_extract_scalar(key_decoded, '$.vec[0].symbol') = 'Contracts'
  AND json_extract_scalar(key_decoded, '$.vec[1].address') IS NOT NULL
GROUP BY 1, 2, 3
UNION ALL
SELECT 'soroswap', 'pair', json_extract_scalar(val_decoded, '$.address'), NULL, NULL, MIN(closed_at)
FROM stellar.contract_data
WHERE contract_id = 'CA4HEQTL2WPEUYKYKCDOHCDNIV4QHNJ7EL4J4NQ6VADP7SYHVRYZ7AW2' AND closed_at_date >= CURRENT_DATE - INTERVAL '14' DAY
  AND contract_key_type = 'ScValTypeScvVec' AND json_extract_scalar(key_decoded, '$.vec[0].symbol') = 'PairAddressesNIndexed'
  AND json_extract_scalar(val_decoded, '$.address') IS NOT NULL
GROUP BY 1, 2, 3
UNION ALL
SELECT 'phoenix', 'pool', json_extract_scalar(val_decoded, '$.address'),
       MAX(regexp_extract(key_decoded, '"token_a"\},"val":\{"address":"(C[A-Z2-7]{55})"', 1)),
       MAX(regexp_extract(key_decoded, '"token_b"\},"val":\{"address":"(C[A-Z2-7]{55})"', 1)), MIN(closed_at)
FROM stellar.contract_data
WHERE contract_id = 'CB4SVAWJA6TSRNOJZ7W2AWFW46D5VR4ZMFZKDIKXEINZCZEGZCJZCKMI' AND closed_at_date >= CURRENT_DATE - INTERVAL '14' DAY
  AND contract_key_type = 'ScValTypeScvMap' AND json_extract_scalar(val_decoded, '$.address') IS NOT NULL
GROUP BY 1, 2, 3
UNION ALL
SELECT 'aquarius', 'pool', regexp_extract(he.data_decoded, '"address":"(C[A-Z2-7]{55})"', 1), NULL, NULL, MIN(he.closed_at)
FROM stellar.history_contract_events he
WHERE he.contract_id IN ('CBQDHNBFBZYE4MKPWBSJOPIYLW4SFSXAXUTSXJN76GNKYVYPCKWC6QUK', 'CA7RQDMMV6E53P5EDZA5GPWBZ33AMW2ZNO42XLI2RGRIAP4QXIARUOJQ', 'CB4YHF4ESRJ4XZRXISLXSUZTYY6YPBPZ73MZWSTUWY46DKYW7IGLHGF7') AND he.closed_at_date >= CURRENT_DATE - INTERVAL '14' DAY
  AND he.type_string = 'ContractEventTypeContract'
    AND he.successful = TRUE AND he.in_successful_contract_call = TRUE
  AND he.topics_decoded LIKE '[{"symbol":"add_pool"}%'
  AND regexp_extract(he.data_decoded, '"address":"(C[A-Z2-7]{55})"', 1) IS NOT NULL
GROUP BY 1, 2, 3

)
SELECT protocol, kind, contract_id, MAX(token_a) AS token_a, MAX(token_b) AS token_b, MIN(first_seen) AS first_seen
FROM (SELECT * FROM prev UNION ALL SELECT * FROM fresh)
GROUP BY 1, 2, 3
