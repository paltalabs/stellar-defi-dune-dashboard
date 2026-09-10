-- Query: SCF35 · Aquarius activity          https://dune.com/queries/8666484
-- Matview: ninguna   cron: ninguno
-- Lee: stellar.history_contract_events
-- Costo medido: 2026-09-10 6.27 cr, 188771 filas, engine medium, ventana 45 days
-- Espejo escrito a mano el 2026-09-10 (el endpoint REST de lectura devolvió 401; ver docs/runbook.md). El SQL manda en Dune.

-- SCF35 · Aquarius activity. Schema: docs/modelo-de-datos.md in github.com/paltalabs/defi-dune-dashboards
WITH routers AS (
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
    AND he.closed_at_date >= CURRENT_DATE - INTERVAL '45' DAY      -- WINDOW
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
WHERE user_address IS NOT NULL
