-- Query: https://dune.com/queries/8796476
-- Matview: dune.paltalabs.result_scf_blend_users_live   cron: 0 5 * * *
-- Última ejecución: 01M32KNCQ6HNS5XF8Y7Z7NKQAC
-- Costo: 1.567 cr; filas: 389; engine medium
-- Generated from scripts/pilot_sql.py; T1 address activity only.
-- Daily UTC buckets. Metadata survives an empty protocol and is never a user.
WITH source AS (
WITH pools AS (
  SELECT DISTINCT json_extract_scalar(key_decoded, '$.vec[1].address') AS contract_id, 'pool' AS kind
  FROM stellar.contract_data
  WHERE contract_id IN ('CCZD6ESMOGMPWH2KRO4O7RGTAPGTUPFWFQBELQSS7ZUK63V3TZWETGAG',   -- pool factory v1
                        'CDSYOAVXFY7SM5S64IZPPPYB4GVGGLMQVFREPSQQEZVIWXX5R23G4QSU')   -- pool factory v2
    AND closed_at_date >= DATE '2024-02-01'
    AND contract_key_type = 'ScValTypeScvVec'
    AND json_extract_scalar(key_decoded, '$.vec[0].symbol') = 'Contracts'
),
contracts AS (
  SELECT contract_id, kind FROM pools
  UNION ALL
  SELECT contract_id, kind FROM (VALUES
    ('CAO3AGAMZVRMHITL36EJ2VZQWKYRPWMQAPDQD5YEOF3GIF7T44U4JAL3', 'backstop'),   -- backstop v1
    ('CAQQR5SWBXKIGZKPBZDH3KM5GQ5GUTPKB7JAFCINLZBC5WXPJKRG3IM7', 'backstop')    -- backstop v2
  ) AS v(contract_id, kind)
),
ev AS (
  SELECT DISTINCT
    c.kind, he.contract_id, he.closed_at, lower(to_hex(he.transaction_hash)) AS tx_hash, he.topics_decoded, he.data_decoded
  FROM stellar.history_contract_events he
  JOIN contracts c ON c.contract_id = he.contract_id
  WHERE he.closed_at_date >= DATE '2026-09-17' AND he.closed_at_date < CURRENT_DATE
    AND he.type_string = 'ContractEventTypeContract'
    AND he.successful = TRUE
    AND he.in_successful_contract_call = TRUE
),
parsed AS (
  SELECT
    kind, contract_id, closed_at, tx_hash,
    json_extract_scalar(topics_decoded, '$[0].symbol')  AS action,
    json_extract_scalar(topics_decoded, '$[1].address') AS t1_addr,
    json_extract_scalar(topics_decoded, '$[2].address') AS t2_addr,
    json_extract_scalar(data_decoded, '$.vec[0].address') AS d0_addr,
    COALESCE(
      TRY(CAST(COALESCE(json_extract_scalar(data_decoded, '$.vec[0].i128'), json_extract_scalar(data_decoded, '$.i128')) AS DECIMAL(38,0))),
      TRY(CAST(json_extract_scalar(data_decoded, '$.vec[0].i128.hi') AS DECIMAL(38,0)) * DECIMAL '18446744073709551616'
          + CAST(json_extract_scalar(data_decoded, '$.vec[0].i128.lo') AS DECIMAL(38,0)))
    ) AS d0_i128
  FROM ev
)
SELECT
  'blend' AS protocol,
  contract_id,
  closed_at,
  tx_hash,
  CASE
    WHEN kind = 'pool' AND action = 'fill_auction' THEN d0_addr      -- the filler is the liquidator
    WHEN kind = 'pool' AND action = 'claim'        THEN t1_addr
    WHEN kind = 'pool'                             THEN t2_addr      -- topics [action, asset, from]
    WHEN kind = 'backstop' AND action = 'claim'    THEN t1_addr
    WHEN kind = 'backstop'                         THEN t2_addr      -- topics [action, pool, from]
  END AS user_address,
  CASE WHEN kind = 'backstop' THEN 'backstop_' || action ELSE action END AS action,
  CASE
    WHEN kind = 'pool' AND action IN ('supply', 'withdraw', 'supply_collateral', 'withdraw_collateral') THEN 'lender'
    WHEN kind = 'pool' AND action IN ('borrow', 'repay', 'flash_loan') THEN 'borrower'
    WHEN kind = 'pool' AND action = 'fill_auction' THEN 'liquidator'
    WHEN kind = 'pool' AND action = 'claim' THEN 'claimer'
    WHEN kind = 'backstop' AND action IN ('deposit', 'withdraw', 'queue_withdrawal', 'dequeue_withdrawal', 'donate') THEN 'backstop_provider'
    WHEN kind = 'backstop' AND action = 'claim' THEN 'claimer'
  END AS role,
  CASE WHEN kind = 'backstop' THEN t1_addr ELSE contract_id END AS pool,
  CASE
    WHEN kind = 'pool' AND action IN ('supply', 'withdraw', 'supply_collateral', 'withdraw_collateral', 'borrow', 'repay', 'flash_loan') THEN t1_addr
    WHEN kind = 'backstop' AND action IN ('deposit', 'withdraw', 'donate') THEN 'CAS3FL6TLZKDGGSISDBWGGPXT3NRR4DYTZD7YOD3HMYO6LTJUVGRVEAM'   -- Comet BLND:USDC LP token
  END AS token_a,
  CASE
    WHEN (kind = 'pool' AND action IN ('supply', 'withdraw', 'supply_collateral', 'withdraw_collateral', 'borrow', 'repay', 'flash_loan'))
      OR (kind = 'backstop' AND action IN ('deposit', 'withdraw', 'donate'))
    THEN CAST(d0_i128 * DECIMAL '0.0000001' AS DECIMAL(38,7))
  END AS amount_a,
  CAST(NULL AS VARCHAR) AS token_b,
  CAST(NULL AS DECIMAL(38,7)) AS amount_b
FROM parsed
WHERE (kind = 'pool' AND action IN ('supply', 'withdraw', 'supply_collateral', 'withdraw_collateral', 'borrow', 'repay', 'flash_loan', 'fill_auction', 'claim'))
   OR (kind = 'backstop' AND action IN ('deposit', 'withdraw', 'queue_withdrawal', 'dequeue_withdrawal', 'donate', 'claim'))
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
SELECT 'blend', CAST(NULL AS DATE), CAST(NULL AS VARCHAR), CAST(NULL AS VARCHAR),
       CAST(NULL AS TIMESTAMP WITH TIME ZONE), 'metadata', DATE '2026-09-17', CURRENT_DATE, CURRENT_TIMESTAMP, 'live'
