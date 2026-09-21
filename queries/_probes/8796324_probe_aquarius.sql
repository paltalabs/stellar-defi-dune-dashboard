-- Query: https://dune.com/queries/8796324
-- Matview: None   cron: None
-- Última ejecución: 01M32BYEPS364TA2RSPJTYD764
-- Costo: 1.873 cr; filas: 4; engine medium
WITH source AS (WITH routers AS (
  SELECT contract_id FROM (VALUES
    ('CBQDHNBFBZYE4MKPWBSJOPIYLW4SFSXAXUTSXJN76GNKYVYPCKWC6QUK'),   -- router (main)
    ('CA7RQDMMV6E53P5EDZA5GPWBZ33AMW2ZNO42XLI2RGRIAP4QXIARUOJQ'),   -- router 2
    ('CB4YHF4ESRJ4XZRXISLXSUZTYY6YPBPZ73MZWSTUWY46DKYW7IGLHGF7')    -- router 3
  ) AS v(contract_id)
),
ev AS (
  SELECT DISTINCT
    he.contract_id, he.closed_at, lower(to_hex(he.transaction_hash)) AS tx_hash, he.topics_decoded, he.data_decoded
  FROM stellar.history_contract_events he
  WHERE he.contract_id IN (SELECT contract_id FROM routers)
    AND he.closed_at_date >= CURRENT_DATE - INTERVAL '7' DAY AND he.closed_at_date < CURRENT_DATE
    AND he.type_string = 'ContractEventTypeContract'
    AND he.successful = TRUE
    AND he.in_successful_contract_call = TRUE
    AND (he.topics_decoded LIKE '[{"symbol":"swap"}%' OR he.topics_decoded LIKE '[{"symbol":"deposit"}%'
         OR he.topics_decoded LIKE '[{"symbol":"withdraw"}%' OR he.topics_decoded LIKE '[{"symbol":"claim"}%')
),
parsed AS (
  SELECT
    contract_id, closed_at, tx_hash,
    json_extract_scalar(topics_decoded, '$[0].symbol')  AS action,
    json_extract_scalar(topics_decoded, '$[1].vec[0].address') AS pool_token_a,
    json_extract_scalar(topics_decoded, '$[1].vec[1].address') AS pool_token_b,
    json_extract_scalar(topics_decoded, '$[2].address') AS user_address,
    json_extract_scalar(data_decoded, '$.vec[0].address') AS pool,
    json_extract_scalar(data_decoded, '$.vec[1].address') AS swap_token_in,
    json_extract_scalar(data_decoded, '$.vec[2].address') AS swap_token_out,
    TRY(CAST(json_extract_scalar(data_decoded, '$.vec[3].u128') AS DECIMAL(38,0))) AS swap_in,
    TRY(CAST(json_extract_scalar(data_decoded, '$.vec[4].u128') AS DECIMAL(38,0))) AS swap_out,
    TRY(CAST(json_extract_scalar(data_decoded, '$.vec[1].vec[0].u128') AS DECIMAL(38,0))) AS dep_a,
    TRY(CAST(json_extract_scalar(data_decoded, '$.vec[1].vec[1].u128') AS DECIMAL(38,0))) AS dep_b,
    TRY(CAST(json_extract_scalar(data_decoded, '$.vec[2].vec[0].u128') AS DECIMAL(38,0))) AS wd_a,
    TRY(CAST(json_extract_scalar(data_decoded, '$.vec[2].vec[1].u128') AS DECIMAL(38,0))) AS wd_b,
    json_extract_scalar(data_decoded, '$.vec[1].address') AS claim_token,
    TRY(CAST(json_extract_scalar(data_decoded, '$.vec[2].u128') AS DECIMAL(38,0))) AS claim_amount
  FROM ev
)
SELECT
  'aquarius' AS protocol,
  contract_id,
  closed_at,
  tx_hash,
  user_address,
  action,
  CASE action WHEN 'swap' THEN 'swapper' WHEN 'deposit' THEN 'lp' WHEN 'withdraw' THEN 'lp' WHEN 'claim' THEN 'claimer' END AS role,
  pool,
  CASE action WHEN 'swap' THEN swap_token_in WHEN 'claim' THEN claim_token ELSE pool_token_a END AS token_a,
  CAST(CASE action WHEN 'swap' THEN swap_in WHEN 'deposit' THEN dep_a WHEN 'withdraw' THEN wd_a WHEN 'claim' THEN claim_amount END * DECIMAL '0.0000001' AS DECIMAL(38,7)) AS amount_a,
  CASE action WHEN 'swap' THEN swap_token_out WHEN 'claim' THEN NULL ELSE pool_token_b END AS token_b,
  CAST(CASE action WHEN 'swap' THEN swap_out WHEN 'deposit' THEN dep_b WHEN 'withdraw' THEN wd_b END * DECIMAL '0.0000001' AS DECIMAL(38,7)) AS amount_b
FROM parsed
WHERE user_address IS NOT NULL)
SELECT protocol, role, substr(user_address, 1, 1) AS address_type,
       COUNT(*) AS parsed_rows, COUNT(DISTINCT user_address) AS addresses,
       COUNT_IF(user_address IS NULL OR NOT regexp_like(user_address, '^[GC][A-Z2-7]{55}$')) AS invalid_addresses,
       MIN(closed_at) AS first_event, MAX(closed_at) AS last_event
FROM source GROUP BY 1,2,3 ORDER BY 1,2,3
