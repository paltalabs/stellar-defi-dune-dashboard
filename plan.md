# Plan: Stellar DeFi Dune Dashboards (SCF #35)

Actualizado 2026-09-22. La submission está en `scf/submission-scf35.md`. Este archivo es el
único lugar donde se marca avance y gasto.

## Lo que se decidió el 2026-09-10

1. **Nadie mantiene esto a mano.** Todo lo recurrente es una matview con cron creado por API.
2. **Dos capas por protocolo.** Archive con historia completa, refresh mensual automático.
   Ventana viva desde el último `closed_at` del archive, refresh diario. Los gráficos leen la unión.
3. **Un esquema para los seis protocolos** (`docs/modelo-de-datos.md`). Las tablas crudas se
   escanean una vez por período, y de ahí salen los cuatro entregables.
4. **Los pools se descubren solos** desde el storage de cada factory (0,3 créditos).
5. **Gasto gradual y medido.** Cada paso anota su costo acá. Los pasos caros (archives) se
   corren de a uno por día, mirando el uso antes del siguiente.

## Presupuesto

Cuenta Dune: plan Plus, 25.000 créditos por período (9 de cada mes). Al 2026-09-10 a las 13:00
UTC iban 1.788 usados por otros proyectos. Costos medidos, engine medium:

| Qué | Medido | De dónde sale |
|---|---|---|
| Eventos, 7 días, 14 contratos | 1,33 cr | query 8666280 |
| Eventos, 30 días, un protocolo | 1,6 a 4,2 cr | 8666378 Blend 3,78 · 8666399 Aquarius 4,17 · 8666417 Soroswap 1,56 · 8666420 Phoenix 1,88 |
| Operaciones, 30 días | 0,7 cr · 180 días 1,2 cr | 8666340, 8666431 (FxDAO) |
| Operaciones y trades clásicos, 30 días | 0,43 cr | 8666440 (Etherfuse) |
| Storage de una factory, historia completa | 0,32 cr | 8666382 |
| **Eventos, historia completa (desde 2024-02), 6 contratos** | **37,4 cr** | 8666314. Es el costo de un archive, casi independiente de cuántos contratos |

Proyección con esos números:

| Pieza | Costo unitario | Frecuencia | Por mes |
|---|---|---|---|
| 6 archives (historia completa) | ~40 cr cada uno | mensual, automático | ~240 |
| 6 ventanas vivas (promedio 15 días de datos) | ~2,5 cr cada una | diaria | ~450 |
| Unión + métricas del dashboard (leen matviews) | ~5 a 10 cr en total | diaria | ~250 |
| **Total régimen** | | | **~950 cr/mes, 4% de la cuota** |
| Alternativa: métricas cada 6 h como dice la submission | | 4 por día | ~+600 cr/mes |

Gasto del proyecto hasta ahora: **103,5 cr**: 57,8 en 13 sondeos temporales y 45,6 en las seis queries de actividad del paso 1 (más un re-run de Etherfuse). Nada programado todavía.

Tope acordado para la construcción del Entregable 1: **500 cr**. Los archives (~240) se corren
uno por día. Si un archive mide más de 80 cr se para y se revisa antes de seguir.

## Entregable 1: Weekly & Monthly Active Users (Tranche 1, USD 8.333)

Qué promete la submission: wallets únicas por período, desglose por protocolo, segmentación por
acción (swappers, LPs, aggregator users, lenders, borrowers, liquidators), nuevos vs
recurrentes, tasa de crecimiento semanal y mensual. Medida de completitud: la query está en el
dashboard público, verificable, y se actualiza sola.

### Paso 0: diseño validado con sondeos baratos ✅ 2026-09-10, 52,8 cr

- [x] Tablas y esquemas Stellar en Dune, con particiones (`closed_at_date` en todas las history_*).
- [x] Cómo emite eventos cada protocolo y dónde va el usuario (`docs/modelo-de-datos.md`).
- [x] Registro de contratos (`protocols.yml`) desde stellar.expert, docs oficiales y factories.
- [x] Pools: Blend 15 v1 + 12 v2 (storage de factories), Phoenix 14 (storage), Aquarius 400 (`data/`).
- [x] Prototipos de 30 días de las seis queries de actividad, sin usuarios nulos.

### Paso 1: queries de actividad, capa viva ✅ 2026-09-10, 45,6 cr (estimado 30)

Una query por protocolo, no temporal, ventana `closed_at_date >= current_date - 45 días`, con el
esquema normalizado. Ejecutadas, medidas, espejadas en `queries/<protocolo>/`. Todavía sin matview.
Registro con ids y costos: `queries.yml`.

- [x] Blend 8666478: pools desde storage de las 2 factories + 2 backstops. 6,7 cr, 138.807 filas
- [x] Aquarius 8666484: 3 routers. 6,3 cr, 188.771 filas
- [x] Soroswap 8666498: router + 10 aggregators + pares directos sin router (desde storage de la factory). 7,9 cr, 31.598 filas
- [x] Phoenix 8666499: pools desde storage de la factory, dos formatos de evento. 11,1 cr, 3.506 filas
- [x] FxDAO 8666504: operaciones a vaults y locking pool. 0,1 cr, 0 filas en 45 días (join verificado a 150 días: 17 filas)
- [x] Etherfuse 8666506: path payments, payments, offers y trades del issuer. 6,7 cr, 895.391 filas (bots de market making)

### Paso 2: archives, uno por día (estimado 240 cr) → hecho en la Fase 1 (abajo), 1.135,3 cr

Misma query sin el filtro de ventana, `is_temp: false`, matview `result_scf_<p>_activity_archive`
con cron `0 3 1 * *`. Se crea, se espera la primera ejecución, se anota el costo real.

- [ ] Etherfuse (operaciones, el más barato: prueba el patrón)
- [ ] FxDAO
- [ ] Phoenix
- [ ] Blend
- [ ] Soroswap
- [ ] Aquarius (el de más filas)

### Paso 3: capa viva apuntada al archive y unión (estimado 20 cr) → hecho en la Fase 1; la unión no se materializa, `result_scf_users` lee las 12 capas

- [ ] Reescribir cada query viva: `closed_at > (SELECT MAX(closed_at) FROM archive)` más la poda
      `closed_at_date >= current_date - 75 días`. Matview `result_scf_<p>_activity`, cron `0 5 * * *`.
- [ ] `SCF35 · activity (all protocols)`: UNION ALL de las 12 matviews. Matview `result_scf_activity`, cron `0 6 * * *`.

### Paso 4: métricas y dashboard (estimado 30 cr) → hecho en la Fase 1, salvo publicar y el reporte

Todas leen solo `result_scf_activity`. Cada una con matview y cron `30 6 * * *`.

- [ ] WAU y MAU por protocolo (wallets G y contratos C por separado)
- [ ] WAU y MAU por rol, por protocolo
- [ ] Nuevos vs recurrentes por semana y por mes, con primera aparición por (protocolo, usuario)
- [ ] Crecimiento semana a semana y mes a mes
- [ ] Salud: último evento por protocolo y edad del dato
- [ ] Dashboard público `dune.com/paltalabs/stellar-defi` con texto de metodología y links a este repo
- [ ] Reporte de la tranche: qué se entregó, links, costos, y lo que quedó fuera

### Piloto diario de usuarios (2026-09-21), 239,5 cr; acumulado del proyecto 343,0 de 500

Reemplaza en la práctica a los pasos 2 a 4 para T1 mientras dura la prueba. Estado, ids y cada
ejecución en `pilot.json`; SQL generado por `scripts/pilot_sql.py`, desplegado con
`scripts/deploy_pilot.py`, espejado en `queries/pilot/`. Decisiones: refresco diario, se cuentan
direcciones G y C (smart wallets), métricas de trading quedan para un plan futuro, no se crean
más archives sin aprobación.

- [x] 6 sondeos de 7 días (180 para FxDAO): 12,1 cr
- [x] Archive Etherfuse 8796351 `result_scf_etherfuse_users_archive` desde 2024-02-01: 102,65 cr, 55.255 filas. Cron quitado (pausado) tras medir
- [x] 6 vivas 8796374, 8796466, 8796476, 8796497, 8796508, 8796519, cron `0 5 * * *`: 116,97 cr (Phoenix 45,5, Blend 26,4, Aquarius 25,2, Soroswap 15,7). Los otros 5 protocolos arrancan en 2026-06-01
- [x] Unión 8796528 `result_scf_users` (`0 8 * * *`) y 6 métricas 8796531 a 8796540 (`0 9`, validación `0 10`): 7,6 cr
- [x] Validación: 7 checks, 0 fallos. Salud: 6 protocolos OK, Etherfuse desde 2024-02-01, resto desde 2026-06-01. Lectura 0,055 cr
- [x] 5 queries de gráficos 8796719 a 8796723 (SELECT sobre matviews, sin matview propia): 0,149 cr
- [x] 9 visualizaciones en inglés (ids en `pilot.json` → `visualizations`)
- [x] Refresco de las queries de gráficos por MCP: `python3 scripts/deploy_pilot.py refresh-charts`. Hace falta porque la ejecución de una matview deja en su query origen solo `{"rows": N}` y los widgets no pueden colgar de las queries de métricas. Medido 2026-09-21: 0,172 cr por corrida (~5,2 cr/mes, costo de operación, no de construcción)
- [x] Reemplazado: los gráficos usan el schedule de Dune (decisión del 2026-09-22, `docs/runbook.md`)
- [x] Layout aplicado al dashboard 220644 el 2026-09-21: 2 textos (metodología, cobertura parcial) y 9 visualizaciones. Sigue **privado**; publicar requiere OK tras revisión
- [x] Revisión 2026-09-21 (sondeos 9,3 cr): FxDAO inactivo de verdad (sin invocaciones a vaults ni `mint` de sus 4 assets desde junio). Aquarius **subcontado**: en 7 días 736 de 904 `deposit_liquidity` y 71.851 de 113.543 `trade` ocurren en pools sin evento del router. Blend plausible: 68% de 17.824 lenders activos un solo día, 89 contratos C
- [x] Capa `result_scf_<p>_users_history` (sin cron todavía) para no re-escanear desde junio cada día. 5 creadas copiando de las matviews vivas: 6,1 cr (8797129 etherfuse, 8797130 fxdao, 8797131 blend, 8797133 soroswap, 8797135 phoenix)
- [x] ⚠️ Aquarius history 8797138 reconstruida desde crudo con eventos de pool: **181,4 cr** (estimado 25 a 45), 25.700 filas contra ~8.300 del router solo. Superó el límite de 80 cr y el tope de 500: acumulado 539,8 cr. Detenido a la espera de decisión
- [x] **Fase 0, puente (2026-09-21, 28,7 cr):** tope del script subido a 600 con OK del usuario (opción A). Las 6 vivas escanean desde `DATE '2026-09-17'` (literal, poda particiones) y la unión lee history (congelada hasta 2026-09-18) + viva. Refresco de las vivas: 18,8 cr (Aquarius 7,9; Phoenix 3,9; Etherfuse 2,3; Soroswap 2,1; Blend 1,6; FxDAO 1,0), antes ~117 cr/día. Validación 8 checks (nuevo `history_live_gap`) en 0. Aquarius pasa de 1.397 a 2.139 direcciones
- [x] WAU y MAU del ecosistema (únicas entre protocolos, G y C por separado): queries 8797598 y 8797599, visualizaciones 12827594 y 12827595, agregadas al dashboard (privado)
- [x] `getDuneQuery` por REST (`GET /api/v1/query/{id}`): la llave del `.env` funciona y el MCP devolvía cuerpos vacíos
- [x] Reemplazado: la GitHub Action se quitó el 2026-09-22 a favor del schedule de Dune
- [ ] El puente crece un día por día (~4,7 cr más por cada día de ventana, Aquarius la mitad). Sirve una o dos semanas, no más. Lo reemplaza la Fase 1

Acumulado del proyecto al cierre de la Fase 0: **568,5 cr** (tope 600).

### Fase 1: diseño de CLAUDE.md aplicado ✅ 2026-09-22, 1.315,9 cr; acumulado del proyecto 1.884,4

Tope subido a 2.000 con OK del usuario ("correr todo independiente del costo para cerrar la
tranche 1"). Cada capa en el esquema normalizado de `docs/modelo-de-datos.md`, generado por
`scripts/activity_sql.py`. Ids y ejecuciones en `pilot.json`.

- [x] Registro `result_scf_contracts` 8798252: primer build 78,9 cr, luego incremental 3,9 cr/semana (lunes 02:00). 686 contratos: 27 pools Blend, 214 pares Soroswap, 14 pools Phoenix, 431 pools Aquarius (31 que la lista de septiembre no tenía)
- [x] Listas de contratos literales en el SQL: con subquery la misma consulta costó 3,5 veces más
- [x] Archives con historia desde 2024-02-01, 1.135,3 cr:

| Protocolo | Query | Costo (cr) | Filas |
|---|---|---|---|
| FxDAO | 8798419 | 11,9 | 3.786 |
| Soroswap | 8798502 | 65,4 | 590.915 |
| Blend | 8798463 | 87,8 | 1.204.167 |
| Etherfuse | 8798538 | 117,9 | 8.442.298 |
| Phoenix | 8798422 | 331,8 | 262.058 |
| Aquarius | 8798647 | 519,4 | 4.782.485 |

- [x] Dune no acepta crons mensuales (máximo semanal). Los archives corren cada lunes 03:00 y se leen a sí mismos: el primer lunes del mes agregan el mes cerrado; los demás lunes la condición de fecha es falsa y no escanean (0,01 cr contra 0,66). Verificado en FxDAO: 1,17 cr, mismas filas
- [x] Vivas (queries del paso 1, 8666478, 8666484, 8666498, 8666499, 8666504, 8666506), cron 05:00, del 1 al 21 de septiembre: 59,4 cr (Aquarius 24,2; Soroswap 11,5; FxDAO 9,0; Etherfuse 6,5; Blend 4,6; Phoenix 3,8)
- [x] `result_scf_users` desde las 12 capas (731.765 filas) y métricas, integridad y validación: 11,2 cr. Validación 9 checks en 0 (nuevos: `archive_live_gap`, `unregistered_contracts`). Salud: 6 protocolos OK desde 2024-02-01
- [x] Tabla de integridad `result_scf_integrity` (query 8798721) y gráfico 8798732: explica por qué Aquarius, con 14 veces las acciones de Soroswap, tiene un número parecido de direcciones (68 direcciones hacen el 90% de sus acciones, contra 672 en Soroswap). Documentado en `docs/modelo-de-datos.md`, sección Integridad
- [x] Piloto retirado: las 6 `users_live` sin cron (quitar el cron dispara un refresco: 17,3 cr)
- [x] Dashboard privado con 12 gráficos, historia completa y textos actualizados. Gráficos con schedule de Dune (excepción a la regla 1, `docs/runbook.md`)
- [ ] **Usuario:** programar en la UI de Dune las 8 queries de gráficos a las 10:30 UTC (lista en el runbook)
- [ ] **Usuario:** revisar y publicar el dashboard; commit de este trabajo
- [ ] Medir el primer lunes (2026-09-28) cuánto cuesta la copia semanal de los archives grandes (Etherfuse 8,4 M filas, Aquarius 4,8 M) y el primer lunes de octubre (2026-10-05) el agregado del mes
- [ ] Optimizar la viva de FxDAO (9 cr por 2 filas: el join con `history_transactions` escanea todas las transacciones) y la de Aquarius

Costo recurrente estimado: vivas entre ~5 cr (día 1 del mes) y ~60 cr (fin de mes), unos 30 cr/día
de promedio (~900 cr/mes, dos tercios Aquarius); unión y métricas ~11 cr/día (~330 cr/mes);
registro ~16 cr/mes; archives: agregado mensual (Aquarius ~50 cr) más las copias semanales, a
medir; gráficos ~15 cr/mes. **Total estimado ~1.300 a 1.500 cr/mes**, por encima de los ~950 del
presupuesto original; decidir con Esteban si se optimiza Aquarius o se acepta.

## Entregable 2: solapamiento de usuarios (Tranche 2, USD 3.333)

Sale de `result_scf_activity` sin escanear nada nuevo: matriz protocolo × protocolo de usuarios
compartidos, primer protocolo de cada wallet, viajes entre protocolos. Costo esperado < 30 cr.

## Entregable 3: actividad de LPs (Tranche 2, USD 5.000)

Necesita precios en USD. Se hace una tabla diaria propia acotada a los tokens que aparecen en la
actividad LP (patrón de `dune-dashboards`: 8 assets 1,35 cr/día). LPs activos, top LPs, valor por
transacción. Las columnas `token_*` y `amount_*` ya están en la actividad.

## Entregable 4: flujos y migraciones de liquidez (Tranche 3, USD 8.333)

Entradas y salidas por protocolo y pool desde `add`/`remove`, `deposit`/`withdraw`,
`provide_liquidity`/`withdraw_liquidity`, `supply`/`withdraw`. Migración: misma wallet retira en
un protocolo y deposita en otro dentro de una ventana. Todo desde `result_scf_activity` más precios.

## Lo que la submission promete y acá se hace distinto

- **"Runs every 6 hours".** El diseño refresca los datos crudos una vez al día y las métricas
  una vez al día. Pasar las métricas a 6 h cuesta ~600 cr/mes más y no cambia lo que se ve, porque
  los datos de abajo son diarios. Decidir antes de cerrar la tranche y decirlo en el reporte.
- **Usuarios = direcciones.** Un contrato que opera (bot, vault de DeFindex, el aggregator) cuenta
  como usuario del protocolo que toca. Se muestra separado de las wallets G para no inflar.
- **Soroswap.** Los usuarios salen de los eventos de los pares (cubre router y llamadas directas)
  más el aggregator. Los usuarios del aggregator por el canal SDEX (memo) quedan fuera de T1;
  están medidos en `dune-dashboards` si hace falta sumarlos.
- **FxDAO** está casi inactivo (decenas de operaciones por mes). Se incluye igual y se dice.
- **Etherfuse** no es un protocolo Soroban: se mide como asset clásico (path payments, trades,
  redeems al issuer).
