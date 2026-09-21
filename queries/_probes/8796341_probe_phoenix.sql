-- Query: https://dune.com/queries/8796341
-- Matview: None   cron: None
-- Última ejecución: 01M32C0CP2EWY505CB906JWWPR
-- Costo: 3.574 cr; filas: 2; engine medium
WITH source AS (WITH pools AS (
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
    AND he.closed_at_date >= CURRENT_DATE - INTERVAL '7' DAY AND he.closed_at_date < CURRENT_DATE
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
)
SELECT protocol, role, substr(user_address, 1, 1) AS address_type,
       COUNT(*) AS parsed_rows, COUNT(DISTINCT user_address) AS addresses,
       COUNT_IF(user_address IS NULL OR NOT regexp_like(user_address, '^[GC][A-Z2-7]{55}$')) AS invalid_addresses,
       MIN(closed_at) AS first_event, MAX(closed_at) AS last_event
FROM source GROUP BY 1,2,3 ORDER BY 1,2,3
