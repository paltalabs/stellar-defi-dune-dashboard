-- Query: https://dune.com/queries/8796508
-- Matview: dune.paltalabs.result_scf_soroswap_users_live   cron: None
-- Última ejecución: 01M32KM1ECB3MEYARZ7JMTR0C7
-- Costo: 2.139 cr; filas: 139; engine medium
-- Generated from scripts/pilot_sql.py; T1 address activity only.
-- Daily UTC buckets. Metadata survives an empty protocol and is never a user.
WITH source AS (
WITH pairs AS (
  SELECT DISTINCT json_extract_scalar(val_decoded, '$.address') AS contract_id, 'pair' AS kind
  FROM stellar.contract_data
  WHERE contract_id = 'CA4HEQTL2WPEUYKYKCDOHCDNIV4QHNJ7EL4J4NQ6VADP7SYHVRYZ7AW2'   -- factory
    AND closed_at_date >= DATE '2024-02-01'
    AND contract_key_type = 'ScValTypeScvVec'
    AND json_extract_scalar(key_decoded, '$.vec[0].symbol') = 'PairAddressesNIndexed'
    AND json_extract_scalar(val_decoded, '$.address') IS NOT NULL
),
contracts AS (
  SELECT contract_id, kind FROM pairs
  UNION ALL
  SELECT contract_id, kind FROM (VALUES
    ('CAG5LRYQ5JVEUI5TEID72EYOVX44TTUJT5BQR2J6J77FH65PCCFAJDDH', 'router'),
    ('CCHCH6XVKTMKTYCTKKTKNE2TFP5CMORNY77TA6XSRAD2XM7I2SJBUH3H', 'aggregator'),
    ('CC2CMNKAFI3KKL6ROMIYJKKX2WE2MV5QAF7DZDWC57ENHV6DQTHT3W64', 'aggregator'),
    ('CBFAORZNK4JSCJYT3ZLWFQ5QEI4IHOIYY6XCYT3E47AK6ZMZFKFP6ZKA', 'aggregator'),
    ('CACITNMTUSTZYKKH4TJVXNH4C4XHGYFVAPQ2EE3D5LTL3HIA32QY4Q6X', 'aggregator'),
    ('CDPJAUHPMJBOPUHBWBHO7NKSTR6J5EXZZ2OX4QGSXIHEJLBDY2JABM3L', 'aggregator'),
    ('CCXNPJPNWT4WDWKTUNRPKNUHFYKZW6XBJAOHKAW2KLY5PBBGX6ZCFUJC', 'aggregator'),
    ('CAWTTRKV7N4MBFSFU7BBZVMOAFEVYMZEDUS4ULBGUQH5YMFKPOFUWPF3', 'aggregator'),
    ('CCWLXIBMONXFCXELPFHXPT4VSXKUSSP67DXNXWQ4YIPFGNBHQWEX4W4P', 'aggregator'),
    ('CDEM2W2D2SC7VU3NOCIKHZWCUNCAUWI5GUGHSWBJNBENRHSVIMUT6EM2', 'aggregator'),
    ('CAYP3UWLJM7ZPTUKL6R6BFGTRWLZ46LRKOXTERI2K6BIJAWGYY62TXTO', 'aggregator')
  ) AS v(contract_id, kind)
),
ev AS (
  SELECT DISTINCT
    c.kind, he.contract_id, he.closed_at, lower(to_hex(he.transaction_hash)) AS tx_hash,
    json_extract_scalar(he.topics_decoded, '$[0].string') AS emitter,
    json_extract_scalar(he.topics_decoded, '$[1].symbol') AS action,
    he.data_decoded
  FROM stellar.history_contract_events he
  JOIN contracts c ON c.contract_id = he.contract_id
  WHERE he.closed_at_date >= DATE '2026-09-17' AND he.closed_at_date < CURRENT_DATE
    AND he.type_string = 'ContractEventTypeContract'
    AND he.successful = TRUE
    AND he.in_successful_contract_call = TRUE
    AND he.topics_decoded LIKE '[{"string":"Soroswap%'
),
actors AS (
  SELECT kind, contract_id, closed_at, tx_hash, action,
         json_extract_scalar(elem, '$.val.address') AS user_address
  FROM ev CROSS JOIN UNNEST(CAST(json_extract(data_decoded, '$.map') AS ARRAY(JSON))) AS t(elem)
  WHERE json_extract_scalar(elem, '$.key.symbol') = 'to'
), routed AS (
  SELECT DISTINCT tx_hash FROM actors WHERE kind IN ('router', 'aggregator')
)
SELECT 'soroswap' AS protocol, closed_at, user_address,
       CASE WHEN kind = 'aggregator' THEN 'aggregator_user'
            WHEN action = 'swap' THEN 'swapper' ELSE 'lp' END AS role
FROM actors a
WHERE (kind = 'router' AND action IN ('swap', 'add', 'remove'))
   OR (kind = 'aggregator' AND action = 'swap')
   OR (kind = 'pair' AND action IN ('swap', 'deposit', 'withdraw')
       AND NOT EXISTS (SELECT 1 FROM routed r WHERE r.tx_hash = a.tx_hash))

), users AS (
  SELECT protocol, CAST(closed_at AT TIME ZONE 'UTC' AS DATE) AS activity_date,
         user_address, role, MAX(closed_at) AS last_activity_at
  FROM source
  WHERE regexp_like(user_address, '^[GC][A-Z2-7]{55}$') AND role IS NOT NULL
  GROUP BY 1, 2, 3, 4
)
SELECT protocol, activity_date, user_address, role, last_activity_at,
       'activity' AS row_kind, DATE '2026-09-17' AS covered_from, CURRENT_DATE AS covered_until,
       CURRENT_TIMESTAMP AS refreshed_at, 'live' AS source_layer
FROM users
UNION ALL
SELECT 'soroswap', CAST(NULL AS DATE), CAST(NULL AS VARCHAR), CAST(NULL AS VARCHAR),
       CAST(NULL AS TIMESTAMP WITH TIME ZONE), 'metadata', DATE '2026-09-17', CURRENT_DATE, CURRENT_TIMESTAMP, 'live'
