-- Query: https://dune.com/queries/8796374
-- Matview: dune.paltalabs.result_scf_etherfuse_users_live   cron: 0 5 * * *
-- Última ejecución: 01M32KKMQD8882PW3CHQBZHVSB
-- Costo: 2.252 cr; filas: 233; engine medium
-- Generated from scripts/pilot_sql.py; T1 address activity only.
-- Daily UTC buckets. Metadata survives an empty protocol and is never a user.
WITH source AS (
WITH ops AS (
  SELECT
    o.type_string, o.closed_at, o.transaction_id, o.source_account, o."from" AS from_acct, o."to" AS to_acct, o.amount, o.source_amount,
    CASE WHEN o.asset_issuer = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC' THEN o.asset_code END AS dest_code,
    CASE WHEN o.source_asset_issuer = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC' THEN o.source_asset_code END AS src_code,
    CASE WHEN o.selling_asset_issuer = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC' THEN o.selling_asset_code
         WHEN o.buying_asset_issuer  = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC' THEN o.buying_asset_code END AS offer_code
  FROM stellar.history_operations o
  WHERE o.closed_at_date >= DATE '2026-09-17' AND o.closed_at_date < CURRENT_DATE
    AND o.type_string IN ('payment', 'path_payment_strict_send', 'path_payment_strict_receive', 'manage_sell_offer', 'manage_buy_offer', 'create_passive_sell_offer')
    AND (o.asset_issuer = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC'
      OR o.source_asset_issuer = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC'
      OR o.selling_asset_issuer = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC'
      OR o.buying_asset_issuer = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC')
),
tx AS (
  SELECT id, lower(to_hex(transaction_hash)) AS tx_hash
  FROM stellar.history_transactions
  WHERE closed_at_date >= DATE '2026-09-17' AND closed_at_date < CURRENT_DATE
    AND successful = TRUE
),
rows_ AS (
  SELECT o.closed_at, o.transaction_id, o.to_acct AS user_address,
         CASE WHEN COALESCE(o.from_acct, o.source_account) = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC' THEN 'mint' ELSE 'receive' END AS action,
         CASE WHEN COALESCE(o.from_acct, o.source_account) = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC' THEN 'minter' ELSE 'holder' END AS role,
         o.dest_code AS token_a, o.amount AS amount_a, o.src_code AS token_b, o.source_amount AS amount_b
  FROM ops o
  WHERE o.type_string IN ('payment', 'path_payment_strict_send', 'path_payment_strict_receive')
    AND o.dest_code IS NOT NULL
    AND o.to_acct <> 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC'
  UNION ALL
  SELECT o.closed_at, o.transaction_id, COALESCE(o.from_acct, o.source_account),
         CASE WHEN o.to_acct = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC' THEN 'redeem' ELSE 'send' END,
         CASE WHEN o.to_acct = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC' THEN 'redeemer' ELSE 'holder' END,
         COALESCE(o.src_code, o.dest_code), COALESCE(o.source_amount, o.amount), NULL, NULL
  FROM ops o
  WHERE o.type_string IN ('payment', 'path_payment_strict_send', 'path_payment_strict_receive')
    AND COALESCE(o.src_code, CASE WHEN o.type_string = 'payment' THEN o.dest_code END) IS NOT NULL
    AND COALESCE(o.from_acct, o.source_account) <> 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC'
  UNION ALL
  SELECT o.closed_at, o.transaction_id, o.source_account, 'offer', 'trader', o.offer_code, o.amount, NULL, NULL
  FROM ops o
  WHERE o.type_string IN ('manage_sell_offer', 'manage_buy_offer', 'create_passive_sell_offer') AND o.offer_code IS NOT NULL
),
trades AS (
  SELECT
    MIN(tr.closed_at) AS closed_at,
    tr.history_operation_id,
    acct AS user_address,
    CASE WHEN tr.selling_asset_issuer = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC' THEN tr.selling_asset_code ELSE tr.buying_asset_code END AS token_a,
    SUM(CASE WHEN tr.selling_asset_issuer = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC' THEN tr.selling_amount ELSE tr.buying_amount END) AS amount_a,
    CASE WHEN tr.selling_asset_issuer = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC' THEN COALESCE(NULLIF(tr.buying_asset_code, ''), 'XLM') ELSE COALESCE(NULLIF(tr.selling_asset_code, ''), 'XLM') END AS token_b,
    SUM(CASE WHEN tr.selling_asset_issuer = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC' THEN tr.buying_amount ELSE tr.selling_amount END) AS amount_b
  FROM stellar.history_trades tr
  CROSS JOIN UNNEST(ARRAY[tr.selling_account_address, tr.buying_account_address]) AS u(acct)
  WHERE tr.closed_at_date >= DATE '2026-09-17' AND tr.closed_at_date < CURRENT_DATE
    AND (tr.selling_asset_issuer = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC' OR tr.buying_asset_issuer = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC')
    AND acct IS NOT NULL AND acct <> ''
  GROUP BY 2, 3, 4, 6
)
SELECT
  'etherfuse' AS protocol,
  CAST(NULL AS VARCHAR) AS contract_id,
  r.closed_at,
  t.tx_hash,
  r.user_address,
  r.action,
  r.role,
  CAST(NULL AS VARCHAR) AS pool,
  r.token_a,
  CAST(r.amount_a AS DECIMAL(38,7)) AS amount_a,
  NULLIF(r.token_b, '') AS token_b,
  CAST(r.amount_b AS DECIMAL(38,7)) AS amount_b
FROM rows_ r
JOIN tx t ON t.id = r.transaction_id
WHERE r.user_address IS NOT NULL AND r.user_address <> ''
UNION ALL
SELECT 'etherfuse', NULL, closed_at, 'op:' || CAST(history_operation_id AS VARCHAR), user_address, 'trade', 'trader', NULL,
       token_a, CAST(amount_a AS DECIMAL(38,7)), token_b, CAST(amount_b AS DECIMAL(38,7))
FROM trades
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
SELECT 'etherfuse', CAST(NULL AS DATE), CAST(NULL AS VARCHAR), CAST(NULL AS VARCHAR),
       CAST(NULL AS TIMESTAMP WITH TIME ZONE), 'metadata', DATE '2026-09-17', CURRENT_DATE, CURRENT_TIMESTAMP, 'live'
