-- Query: https://dune.com/queries/8796519
-- Matview: dune.paltalabs.result_scf_phoenix_users_live   cron: 0 5 * * *
-- Última ejecución: 01M32KMSXZZBX9EN2PTPFQQFEJ
-- Costo: 3.946 cr; filas: 19; engine medium
-- Generated from scripts/pilot_sql.py; T1 address activity only.
-- Daily UTC buckets. Metadata survives an empty protocol and is never a user.
WITH source AS (
WITH pools AS (
  SELECT pool, MAX(token_a) AS token_a, MAX(token_b) AS token_b
  FROM (
    SELECT json_extract_scalar(val_decoded, '$.address') AS pool,
           regexp_extract(key_decoded, '"token_a"\},"val":\{"address":"(C[A-Z2-7]{55})"', 1) AS token_a,
           regexp_extract(key_decoded, '"token_b"\},"val":\{"address":"(C[A-Z2-7]{55})"', 1) AS token_b
    FROM stellar.contract_data
    WHERE contract_id = 'CB4SVAWJA6TSRNOJZ7W2AWFW46D5VR4ZMFZKDIKXEINZCZEGZCJZCKMI'   -- factory
      AND closed_at_date >= DATE '2024-02-01'
      AND contract_key_type = 'ScValTypeScvMap'
      AND json_extract_scalar(val_decoded, '$.address') IS NOT NULL
  )
  GROUP BY pool
),
ev AS (
  SELECT DISTINCT
    he.contract_id AS pool, he.closed_at, lower(to_hex(he.transaction_hash)) AS tx_hash,
    COALESCE(json_extract_scalar(he.topics_decoded, '$[0].string'), json_extract_scalar(he.topics_decoded, '$[0].symbol')) AS action,
    json_extract_scalar(he.topics_decoded, '$[1].string') AS field,
    he.data_decoded
  FROM stellar.history_contract_events he
  WHERE he.contract_id IN (SELECT pool FROM pools)
    AND he.closed_at_date >= DATE '2026-09-17' AND he.closed_at_date < CURRENT_DATE
    AND he.type_string = 'ContractEventTypeContract'
    AND he.successful = TRUE
    AND he.in_successful_contract_call = TRUE
    AND (he.topics_decoded LIKE '[{"string":"swap"}%' OR he.topics_decoded LIKE '[{"string":"provide_liquidity"}%' OR he.topics_decoded LIKE '[{"string":"withdraw_liquidity"}%'
         OR he.topics_decoded LIKE '[{"symbol":"swap"}%' OR he.topics_decoded LIKE '[{"symbol":"provide_liquidity"}%' OR he.topics_decoded LIKE '[{"symbol":"withdraw_liquidity"}%')
),
actors AS (
  SELECT closed_at, action, json_extract_scalar(data_decoded, '$.address') AS user_address
  FROM ev WHERE replace(replace(field, ' ', '_'), '-', '_') = 'sender'
  UNION ALL
  SELECT closed_at, action, json_extract_scalar(elem, '$.val.address')
  FROM ev CROSS JOIN UNNEST(CAST(json_extract(data_decoded, '$.map') AS ARRAY(JSON))) AS t(elem)
  WHERE field IS NULL AND json_extract_scalar(elem, '$.key.symbol') = 'sender'
)
SELECT 'phoenix' AS protocol, closed_at, user_address,
       CASE WHEN action = 'swap' THEN 'swapper' ELSE 'lp' END AS role
FROM actors

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
SELECT 'phoenix', CAST(NULL AS DATE), CAST(NULL AS VARCHAR), CAST(NULL AS VARCHAR),
       CAST(NULL AS TIMESTAMP WITH TIME ZONE), 'metadata', DATE '2026-09-17', CURRENT_DATE, CURRENT_TIMESTAMP, 'live'
