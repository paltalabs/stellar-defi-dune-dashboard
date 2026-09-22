#!/usr/bin/env python3
"""Despliegue reanudable del piloto. IDs y ejecuciones quedan en pilot.json.

Cada comando crea/modifica solo la pieza indicada. No ejecuta automáticamente
otros archives. Siempre usa medium y conserva los widgets existentes.
"""
import argparse
import json
from pathlib import Path

from dune_mcp import DuneMCP, ROOT
import pilot_sql
import activity_sql

STATE = ROOT / 'pilot.json'


def load():
    return json.loads(STATE.read_text()) if STATE.exists() else {
        'dashboard_url': 'https://dune.com/paltalabs/stellar-defi',
        'construction_cap_credits': 500, 'previous_project_credits': 103.5,
        'pieces': {}, 'executions': [], 'visualizations': {}}


def save(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')


def budget(state):
    spent = state['previous_project_credits'] + sum(float(e.get('credits', 0) or 0) for e in state['executions'])
    if spent >= state['construction_cap_credits']:
        raise RuntimeError(f'Tope de construcción alcanzado: {spent}')
    return spent


def sync_query(client, state, key, sql, name, temporary=False):
    piece = state['pieces'].get(key)
    if piece:
        remote = client.call('getDuneQuery', {'query_id': piece['query_id']})
        if remote['query'].strip() != sql.strip():
            if remote['query'].strip() != piece['sql'].strip():
                raise RuntimeError(f'SQL remoto cambió fuera del despliegue: {key}')
            client.call('updateDuneQuery', {'queryId': piece['query_id'], 'query': sql})
        piece['sql'] = sql
    else:
        result = client.call('createDuneQuery', {'name': name, 'query': sql, 'is_private': False,
                    'is_temp': temporary, 'description': 'SCF35 daily pilot. Addresses include G and C. See github.com/paltalabs/stellar-defi-dune-dashboard.'})
        print(json.dumps({'created': key, 'result': result}), flush=True)
        query_id = result.get('query_id') or result.get('queryId')
        if not query_id:
            raise RuntimeError('No query ID in response')
        piece = {'query_id': query_id, 'sql': sql, 'matview': None, 'cron': None}
        state['pieces'][key] = piece
    save(state)
    mirror(key, piece)
    return piece


def mirror(key, piece):
    protocol, _, rest = key.partition('_')
    if rest in ('activity', 'activity_archive'):
        folder, name = ROOT / 'queries' / protocol, rest
    else:
        folder, name = ROOT / 'queries' / ('_probes' if key.startswith('probe_') else 'pilot'), key
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{piece['query_id']}_{name}.sql"
    header = (f"-- Query: https://dune.com/queries/{piece['query_id']}\n"
              f"-- Matview: {piece.get('matview')}   cron: {piece.get('cron')}\n"
              f"-- Última ejecución: {piece.get('last_execution')}\n"
              f"-- Costo: {piece.get('credits')} cr; filas: {piece.get('rows')}; engine medium\n")
    path.write_text(header + piece['sql'].rstrip() + '\n')
    piece['file'] = str(path.relative_to(ROOT))


def finish(client, state, key, execution_id):
    result = client.call('getExecutionResults', {'executionId': execution_id, 'timeout': 240, 'limit': 20})
    print(json.dumps({'key': key, 'execution': result}), flush=True)
    logs = ROOT / 'logs'
    logs.mkdir(exist_ok=True)
    (logs / f'scf-{key}-execution.json').write_text(json.dumps(result, indent=2))
    meta = result.get('resultMetadata') or {}
    cost = float(meta['executionCostCredits']) if meta.get('executionCostCredits') is not None else None
    row_count = meta.get('totalRowCount')
    rows = (result.get('data') or {}).get('rows') or []
    if len(rows) == 1 and set(rows[0]) == {'rows'}:
        row_count = rows[0]['rows']
    record = {'key': key, 'execution_id': execution_id, 'credits': cost, 'metadata': meta,
              'state': result.get('state') or result.get('executionState')}
    state['executions'] = [e for e in state['executions'] if e['execution_id'] != execution_id] + [record]
    piece = state['pieces'][key]
    piece.update(last_execution=execution_id, credits=cost, rows=row_count)
    mirror(key, piece)
    save(state)
    if 'FAILED' in str(record['state']) or result.get('error'):
        raise RuntimeError(f'Falló {key}')
    if record['state'] != 'COMPLETED':
        raise RuntimeError(f'Ejecución pendiente: usar finish {key} antes de continuar')
    if cost is not None and cost > state.get('execution_alert_credits', 80):
        raise RuntimeError('La ejecución superó el aviso por ejecución; revisar antes de continuar')
    return result


def run(client, state, key, piece, matview=None, cron=None):
    budget(state)
    if matview and not piece.get('matview'):
        result = client.call('createMaterializedView', {'query_id': piece['query_id'],
                   'name': matview, 'performance': 'medium', 'cron_expression': cron})
        piece.update(matview='dune.paltalabs.' + matview, cron=cron)
    elif matview:
        # Existing matview: refresh re-executes the (already synced) query and rewrites the table.
        result = client.call('refreshMaterializedView', {'name': piece['matview'], 'performance': 'medium'})
    else:
        result = client.call('executeQueryById', {'query_id': piece['query_id'], 'performance': 'medium'})
    print(json.dumps({'started': key, 'result': result}), flush=True)
    execution_id = result.get('execution_id') or result.get('executionId')
    piece['pending_execution'] = execution_id
    save(state)
    if not execution_id:
        raise RuntimeError('Inspeccionar respuesta: falta execution ID')
    return finish(client, state, key, execution_id)


def next_day(day):
    import datetime
    return (datetime.date.fromisoformat(day) + datetime.timedelta(days=1)).isoformat()


def record_probe(client, state, key, result):
    preview = result.get('result_preview') or {}
    execution_id = result['execution']['execution_id']
    if preview.get('state') != 'COMPLETED':
        preview = client.call('getExecutionResults', {'executionId': execution_id, 'timeout': 280, 'limit': 1})
    meta = preview.get('resultMetadata') or {}
    cost = float(meta.get('executionCostCredits') or 0)
    state['executions'].append({'key': key, 'query_id': result['query']['query_id'], 'execution_id': execution_id,
                                'credits': cost, 'state': preview.get('state'), 'metadata': meta})
    save(state)
    print(json.dumps({'key': key, 'state': preview.get('state'), 'rows': meta.get('totalRowCount'), 'credits': cost,
                      'error': preview.get('error')}), flush=True)


def export_registry(client, state):
    # Registry snapshot in the repo: the literal contract lists are generated from it (rule 5).
    result = client.call('createAndExecuteQuery', {'name': '[SCF35 probe] export contract registry', 'is_temp': True,
                         'query': 'SELECT protocol, kind, contract_id, token_a, token_b, first_seen FROM dune.paltalabs.result_scf_contracts ORDER BY 1, 2, 6, 3',
                         'performance': 'medium', 'timeout': 200, 'max_rows_returned': 32000})
    record_probe(client, state, 'export_registry', result)
    rows = result['result_preview']['data']['rows']
    import csv
    with open(activity_sql.REGISTRY_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['protocol', 'kind', 'contract_id', 'token_a', 'token_b', 'first_seen'])
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) or '' for k in writer.fieldnames})
    print(json.dumps({'registry_rows': len(rows)}), flush=True)


def adopt_step1_query(client, state, protocol, key):
    # The live layer reuses the step-1 query (queries/<p>/<id>_activity.sql); verify it first.
    path = next((ROOT / 'queries' / protocol).glob('*_activity.sql'))
    query_id = int(path.name.split('_')[0])
    remote = client.call('getDuneQuery', {'query_id': query_id})
    norm = lambda s: '\n'.join(x.strip() for x in s.splitlines() if x.strip() and not x.lstrip().startswith('--'))
    if norm(remote['query']) != norm(path.read_text()):
        raise RuntimeError(f'SQL remoto de {query_id} cambió fuera del repo')
    state['pieces'][key] = {'query_id': query_id, 'sql': remote['query'], 'matview': None, 'cron': None}
    save(state)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['inspect', 'probe', 'archive', 'live', 'metric', 'chart', 'refresh-charts', 'history', 'history-incremental', 'set-cron', 'finish',
                                            'registry', 'export-registry', 'test-activity', 'activity-archive', 'activity-live',
                                            'activity-archive-incremental'])
    parser.add_argument('target', nargs='?')
    parser.add_argument('cron', nargs='?')
    args = parser.parse_args()
    client, state = DuneMCP(), load()
    if args.command == 'inspect':
        state['initial_usage'] = client.call('getUsage', {})
        state['dashboard_before'] = client.call('getDashboard', {'ownerHandle': 'paltalabs', 'slug': 'stellar-defi'})
        for protocol in pilot_sql.PROTOCOLS:
            path = next((ROOT / 'queries' / protocol).glob('*_activity.sql'))
            remote = client.call('getDuneQuery', {'query_id': int(path.name.split('_')[0])})
            norm = lambda s: '\n'.join(x.strip() for x in s.splitlines() if x.strip() and not x.lstrip().startswith('--'))
            if norm(remote['query']) != norm(path.read_text()):
                raise RuntimeError(f'Diferencia en SQL de {protocol}')
        save(state)
        print('Seis queries verificadas; dashboard guardado; presupuesto comprobado.')
        return
    if args.command == 'refresh-charts':
        # Daily re-run of the chart queries after the matviews refresh (validation cron 10:00 UTC).
        # Operating cost, not construction: logged to stdout, not to pilot.json.
        for key in pilot_sql.CHARTS:
            query_id = state['pieces'][key]['query_id']
            started = client.call('executeQueryById', {'query_id': query_id, 'performance': 'medium'})
            execution_id = started.get('execution_id') or started.get('executionId')
            result = client.call('getExecutionResults', {'executionId': execution_id, 'timeout': 240, 'limit': 0})
            meta = result.get('resultMetadata') or {}
            print(json.dumps({'key': key, 'query_id': query_id, 'execution_id': execution_id,
                              'state': result.get('state'), 'rows': meta.get('totalRowCount'),
                              'credits': meta.get('executionCostCredits')}), flush=True)
            if float(meta.get('executionCostCredits') or 0) > 80:
                raise RuntimeError('La ejecución superó 80 créditos; revisar antes de continuar')
        return
    if args.command == 'registry':
        piece = sync_query(client, state, 'contracts', activity_sql.registry(incremental='contracts' in state['pieces']),
                           'SCF35 · contract registry')
        run(client, state, 'contracts', piece, 'result_scf_contracts', '0 2 * * 1')
        export_registry(client, state)
        return
    if args.command == 'export-registry':
        export_registry(client, state)
        return
    if args.command == 'test-activity':
        # One-day test in a temporary query: cost and rows before creating an archive.
        day = args.cron
        sql = activity_sql.layer(args.target, 'test', (day, next_day(day)))
        # create + execute + results(limit 0): createAndExecuteQuery responses got truncated for Blend.
        created = client.call('createDuneQuery', {'name': f'[SCF35 probe] activity {args.target} {day}',
                              'query': sql, 'is_temp': True, 'is_private': False})
        query_id = created.get('query_id') or created.get('queryId')
        started = client.call('executeQueryById', {'query_id': query_id, 'performance': 'medium'})
        record_probe(client, state, f'probe_activity_{args.target}',
                     {'query': {'query_id': query_id}, 'execution': {'execution_id': started.get('execution_id')}})
        return
    if args.command == 'activity-archive-incremental':
        # After the first full build: swap to the self-reading SQL and refresh once to verify it.
        key = f'{args.target}_activity_archive'
        piece = sync_query(client, state, key, activity_sql.archive_incremental(args.target),
                           f'SCF35 · {args.target.title()} activity archive')
        if args.cron != 'norefresh':
            run(client, state, key, piece, 'result_scf_' + key, piece.get('cron'))
        return
    if args.command in ('activity-archive', 'activity-live'):
        kind = args.command.split('-')[1]
        key = f"{args.target}_activity{'_archive' if kind == 'archive' else ''}"
        # Protocols from step 1 reuse their query; one added later (sushiswap) gets a new one.
        if key not in state['pieces'] and kind == 'live' and list((ROOT / 'queries' / args.target).glob('*_activity.sql')):
            adopt_step1_query(client, state, args.target, key)
        name = f"SCF35 · {args.target.title()} activity{' archive' if kind == 'archive' else ''}"
        piece = sync_query(client, state, key, activity_sql.layer(args.target, kind), name)
        run(client, state, key, piece, 'result_scf_' + key, '0 3 * * 1' if kind == 'archive' else '0 5 * * *')
        return
    if args.command == 'set-cron':
        piece = state['pieces'][args.target]
        cron = None if args.cron in (None, 'none') else args.cron
        result = client.call('updateMaterializedView', {'query_id': piece['query_id'], 'performance': 'medium',
                                                        'cron_expression': cron})
        piece['cron'] = cron
        mirror(args.target, piece)
        save(state)
        print(json.dumps({'set_cron': args.target, 'cron': cron, 'result': result}), flush=True)
        return
    if args.command in ('history', 'history-incremental'):
        key = args.target + '_users_history'
        if args.command == 'history':
            if key in state['pieces']:
                raise RuntimeError('History ya existe; usar history-incremental')
            sql = pilot_sql.history_bootstrap(args.target)
        else:
            sql = pilot_sql.history_incremental(args.target)
        piece = sync_query(client, state, key, sql, 'SCF35 · ' + args.target.title() + ' users history')
        # Bootstrap without cron; the daily cron is set only after the incremental SQL works.
        run(client, state, key, piece, 'result_scf_' + key, piece.get('cron'))
        return
    if args.command == 'finish':
        finish(client, state, args.target, state['pieces'][args.target]['pending_execution'])
        return
    if args.command == 'probe':
        days = 180 if args.target == 'fxdao' else 7
        source = pilot_sql.users_source(args.target, f"CURRENT_DATE - INTERVAL '{days}' DAY", 'CURRENT_DATE')
        sql = f"""WITH source AS ({source})
SELECT protocol, role, substr(user_address, 1, 1) AS address_type,
       COUNT(*) AS parsed_rows, COUNT(DISTINCT user_address) AS addresses,
       COUNT_IF(user_address IS NULL OR NOT regexp_like(user_address, '^[GC][A-Z2-7]{{55}}$')) AS invalid_addresses,
       MIN(closed_at) AS first_event, MAX(closed_at) AS last_event
FROM source GROUP BY 1,2,3 ORDER BY 1,2,3"""
        key = 'probe_' + args.target
        piece = sync_query(client, state, key, sql, '[SCF35 probe] T1 users ' + args.target, True)
        run(client, state, key, piece)
    elif args.command in ('archive', 'live'):
        if args.command == 'archive' and args.target != 'etherfuse':
            raise RuntimeError('Piloto: solo Etherfuse archive; los demás se despliegan gradualmente.')
        key = args.target + '_users_' + args.command
        sql = pilot_sql.daily_users(args.target, args.command)
        piece = sync_query(client, state, key, sql, 'SCF35 · ' + args.target.title() + ' users ' + args.command)
        # Archive: one-time build, no cron (paused 2026-09-21; the history layer replaces it).
        cron = None if args.command == 'archive' else '0 5 * * *'
        run(client, state, key, piece, 'result_scf_' + key, cron)
    elif args.command == 'chart':
        # Plain query over matviews, no matview of its own. Refresh mechanism pending decision.
        key = args.target
        names = {'chart_weekly_protocol': 'weekly active addresses by protocol',
                 'chart_monthly_protocol': 'monthly active addresses by protocol',
                 'chart_roles_weekly': 'weekly active addresses by role',
                 'chart_roles_monthly': 'monthly active addresses by role',
                 'chart_health': 'data coverage and health',
                 'chart_ecosystem_weekly': 'weekly active addresses, all protocols',
                 'chart_ecosystem_monthly': 'monthly active addresses, all protocols',
                 'chart_integrity': 'activity concentration by protocol'}
        piece = sync_query(client, state, key, pilot_sql.CHARTS[key](), 'SCF35 · ' + names[key])
        run(client, state, key, piece)
    else:
        functions = {'users': activity_sql.users, 'users_health': pilot_sql.health,
                     'integrity': activity_sql.integrity,
                     'users_weekly': lambda: pilot_sql.periods('week'),
                     'users_monthly': lambda: pilot_sql.periods('month'),
                     'users_roles_weekly': lambda: pilot_sql.periods('week', True),
                     'users_roles_monthly': lambda: pilot_sql.periods('month', True),
                     'users_validation': pilot_sql.validation}
        key = args.target
        names = {'integrity': 'activity concentration (data integrity)'}
        piece = sync_query(client, state, key, functions[key](), 'SCF35 · ' + names.get(key, key.replace('_', ' ')))
        cron = {'users': '0 8 * * *', 'users_validation': '0 10 * * *'}.get(key, '0 9 * * *')
        run(client, state, key, piece, 'result_scf_' + key, cron)


if __name__ == '__main__':
    main()
