-- Query: https://dune.com/queries/8808241 (temporal)
-- Costo: 4.901 cr; filas: 1; engine medium. 2026-09-22.
-- Resultado: 27.534 path payments, 226 direcciones (224 firmantes, 226 receptores), 3 swaps con receptor distinto,
-- 6 ops con source distinta de la cuenta de la tx, 0 inválidas, 138 direcciones ausentes de result_scf_users en 30 días.
-- [SCF35 probe] Soroswap aggregator via SDEX (memo 'SoroswapAggregator%'), last 30 complete days.
WITH agg_txs AS (
  SELECT id AS transaction_id, account, memo
  FROM stellar.history_transactions
  WHERE closed_at_date >= CURRENT_DATE - INTERVAL '30' DAY AND closed_at_date < CURRENT_DATE
    AND memo LIKE 'SoroswapAggregator%' AND successful = TRUE
),
ops AS (
  SELECT o.id AS op_id, o.transaction_id, o.source_account, o."to" AS recipient
  FROM stellar.history_operations o
  WHERE o.closed_at_date >= CURRENT_DATE - INTERVAL '30' DAY AND o.closed_at_date < CURRENT_DATE
    AND o.type_string IN ('path_payment_strict_send', 'path_payment_strict_receive')
    AND o.transaction_id IN (SELECT transaction_id FROM agg_txs)
),
j AS (SELECT o.*, t.account FROM ops o JOIN agg_txs t ON t.transaction_id = o.transaction_id),
addrs AS (
  SELECT account AS a FROM j UNION SELECT recipient FROM j
),
known AS (
  SELECT DISTINCT user_address FROM dune.paltalabs.result_scf_users
  WHERE row_kind = 'activity' AND activity_date >= CURRENT_DATE - INTERVAL '30' DAY
)
SELECT
  (SELECT COUNT(*) FROM agg_txs) AS memo_txs,
  (SELECT COUNT(DISTINCT transaction_id) FROM j) AS memo_txs_with_path_payment,
  COUNT(*) AS path_payment_rows,
  COUNT(DISTINCT op_id) AS distinct_ops,
  COUNT(DISTINCT account) AS distinct_tx_accounts,
  COUNT(DISTINCT recipient) AS distinct_recipients,
  COUNT_IF(recipient <> account) AS ops_recipient_ne_account,
  COUNT_IF(source_account <> account) AS ops_opsource_ne_txaccount,
  COUNT_IF(NOT regexp_like(COALESCE(recipient, ''), '^[GC][A-Z2-7]{55}$')) AS invalid_recipient,
  COUNT_IF(NOT regexp_like(COALESCE(account, ''), '^[GC][A-Z2-7]{55}$')) AS invalid_account,
  (SELECT COUNT(*) FROM addrs) AS distinct_addresses_both,
  (SELECT COUNT(*) FROM addrs WHERE a NOT IN (SELECT user_address FROM known)) AS addresses_not_in_scf_users_30d
FROM j
