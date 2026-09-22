# Sondeos

Queries temporales usadas para validar el diseño el 2026-09-10. No están programadas ni tienen
matview. Se listan para poder volver a mirarlas; el SQL final vive en `queries/<protocolo>/`.

| Query | Qué probó | Costo |
|---|---|---|
| [8666280](https://dune.com/queries/8666280) | Formas de eventos por protocolo, 7 días | 1,33 |
| [8666340](https://dune.com/queries/8666340) | Invocaciones por protocolo en history_operations, 30 días | 0,68 |
| [8666314](https://dune.com/queries/8666314) | Registros de pools desde eventos de factories, historia completa. Solo sirvió para Aquarius. **No repetir** | 37,36 |
| [8666378](https://dune.com/queries/8666378) | Blend normalizado, 30 días | 3,78 |
| [8666382](https://dune.com/queries/8666382) | Storage de factories Blend y Phoenix | 0,32 |
| [8666399](https://dune.com/queries/8666399) | Aquarius normalizado, 30 días | 4,17 |
| [8666417](https://dune.com/queries/8666417) | Eventos de router y aggregator Soroswap, 30 días | 1,56 |
| [8666420](https://dune.com/queries/8666420) | Pools y eventos Phoenix, 30 días | 1,88 |
| [8666431](https://dune.com/queries/8666431) | FxDAO por función, 180 días | 1,24 |
| [8666440](https://dune.com/queries/8666440) | Etherfuse ops clásicas y trades, 30 días | 0,43 |

SushiSwap, 2026-09-22 (el SQL quedó en cada query de Dune, temporal):

| Query | Qué probó | Costo |
|---|---|---|
| [8807444](https://dune.com/queries/8807444) | Storage del factory: 116 entradas `GetPool`, desde 2026-03-02 | 0,17 |
| [8807449](https://dune.com/queries/8807449) | Los 58 pools (cruzados 1:1 con stellar.expert) | 0,08 |
| [8807456](https://dune.com/queries/8807456) | Formas de evento de factory, router y pools, 7 días | 0,88 |
| [8807465](https://dune.com/queries/8807465) | Position manager y quién firma los swaps, 30 días | 5,70 |
| [8807515](https://dune.com/queries/8807515) | token0 = token de bytes menores, 58 de 58 | 0,77 |
| [8807521](https://dune.com/queries/8807521) | Signo de los montos contra el router, 304 de 304 | 2,13 |
| [8807571](https://dune.com/queries/8807571) | Capa normalizada, 7 días (mostró los `burn` sin usuario) | 2,39 |
| [8807578](https://dune.com/queries/8807578) | Firmante de los LP: coincide en mint, no existe para la mayoría | 7,31 |
| [8807730](https://dune.com/queries/8807730) | `sender` por regex y por JSON, 0 diferencias | 1,17 |
| [8807737](https://dune.com/queries/8807737) | Swaps por día: 551 wallets G el 2026-09-22 contra 3 a 7 los días previos | 0,79 |
