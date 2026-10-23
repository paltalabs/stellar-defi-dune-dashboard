-- Query: https://dune.com/queries/8996597
-- Matview: dune.paltalabs.result_scf_migrations   cron: 30 9 * * *
-- Última ejecución: 01M5MBM8C65W502FTTA2S9TJMY
-- Costo: 1.112 cr; filas: 26096; engine medium
-- Liquidity migrations: a wallet withdraws from one protocol and deposits in another within 7 days.
WITH f AS (
  SELECT protocol, pool, closed_at, tx_hash, user_address, direction, usd_value
  FROM dune.paltalabs.result_scf_flow_tx
  WHERE flow_type = 'liquidity' AND address_type = 'G'
), outs AS (
  SELECT * FROM f WHERE direction = 'out' AND closed_at < CURRENT_TIMESTAMP - INTERVAL '7' DAY
), ins AS (SELECT * FROM f WHERE direction = 'in'),
matched AS (
  SELECT o.protocol AS from_protocol, o.pool AS from_pool, o.closed_at AS out_at, o.tx_hash AS out_tx,
         o.user_address, o.usd_value AS usd_out,
         min_by(CAST(ROW(i.protocol, i.pool, i.closed_at, i.tx_hash, i.usd_value)
                AS ROW(protocol varchar, pool varchar, closed_at timestamp(3) with time zone, tx_hash varchar, usd_value double)),
                ROW(i.closed_at, i.tx_hash)) AS first_in
  FROM outs o
  JOIN ins i ON i.user_address = o.user_address AND i.protocol <> o.protocol
   AND i.closed_at >= o.closed_at AND i.closed_at <= o.closed_at + INTERVAL '7' DAY
  GROUP BY 1, 2, 3, 4, 5, 6
)
SELECT from_protocol, from_pool, first_in.protocol AS to_protocol, first_in.pool AS to_pool, user_address,
       out_at, first_in.closed_at AS in_at, CAST(out_at AT TIME ZONE 'UTC' AS DATE) AS out_day,
       out_tx, first_in.tx_hash AS in_tx, out_tx = first_in.tx_hash AS same_tx,
       date_diff('second', out_at, first_in.closed_at) AS seconds_between,
       usd_out, first_in.usd_value AS usd_in, LEAST(usd_out, first_in.usd_value) AS usd_migrated,
       CURRENT_TIMESTAMP AS refreshed_at
FROM matched
