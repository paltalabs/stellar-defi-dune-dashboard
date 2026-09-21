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
    folder = ROOT / 'queries' / ('_probes' if key.startswith('probe_') else 'pilot')
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{piece['query_id']}_{key}.sql"
    header = (f"-- Query: https://dune.com/queries/{piece['query_id']}\n"
              f"-- Matview: {piece.get('matview')}   cron: {piece.get('cron')}\n"
              f"-- Última ejecución: {piece.get('last_execution')}\n"
              f"-- Costo: {piece.get('credits')} cr; filas: {piece.get('rows')}; engine medium\n")
    path.write_text(header + piece['sql'].rstrip() + '\n')
    piece['file'] = str(path.relative_to(ROOT))


def finish(client, state, key, execution_id):
    result = client.call('getExecutionResults', {'executionId': execution_id, 'timeout': 240, 'limit': 20})
    print(json.dumps({'key': key, 'execution': result}), flush=True)
    (Path('/tmp/opencode') / f'scf-{key}-execution.json').write_text(json.dumps(result, indent=2))
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
    if cost is not None and cost > 80:
        raise RuntimeError('La ejecución superó 80 créditos; revisar antes de continuar')
    return result


def run(client, state, key, piece, matview=None, cron=None):
    budget(state)
    if matview and not piece.get('matview'):
        result = client.call('createMaterializedView', {'query_id': piece['query_id'],
                   'name': matview, 'performance': 'medium', 'cron_expression': cron})
        piece.update(matview='dune.paltalabs.' + matview, cron=cron)
    else:
        if matview:
            raise RuntimeError('La matview ya existe; usar refresh explícito tras revisar su estado')
        result = client.call('executeQueryById', {'query_id': piece['query_id'], 'performance': 'medium'})
    print(json.dumps({'started': key, 'result': result}), flush=True)
    execution_id = result.get('execution_id') or result.get('executionId')
    piece['pending_execution'] = execution_id
    save(state)
    if not execution_id:
        raise RuntimeError('Inspeccionar respuesta: falta execution ID')
    return finish(client, state, key, execution_id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['inspect', 'probe', 'archive', 'live', 'metric', 'chart', 'refresh-charts', 'finish'])
    parser.add_argument('target', nargs='?')
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
        cron = '0 1 * * 0' if args.command == 'archive' else '0 5 * * *'
        run(client, state, key, piece, 'result_scf_' + key, cron)
    elif args.command == 'chart':
        # Plain query over matviews, no matview of its own. Refresh mechanism pending decision.
        key = args.target
        names = {'chart_weekly_protocol': 'weekly active addresses by protocol',
                 'chart_monthly_protocol': 'monthly active addresses by protocol',
                 'chart_roles_weekly': 'weekly active addresses by role',
                 'chart_roles_monthly': 'monthly active addresses by role',
                 'chart_health': 'data coverage and health'}
        piece = sync_query(client, state, key, pilot_sql.CHARTS[key](), 'SCF35 · ' + names[key])
        run(client, state, key, piece)
    else:
        functions = {'users': pilot_sql.combined, 'users_health': pilot_sql.health,
                     'users_weekly': lambda: pilot_sql.periods('week'),
                     'users_monthly': lambda: pilot_sql.periods('month'),
                     'users_roles_weekly': lambda: pilot_sql.periods('week', True),
                     'users_roles_monthly': lambda: pilot_sql.periods('month', True),
                     'users_validation': pilot_sql.validation}
        key = args.target
        piece = sync_query(client, state, key, functions[key](), 'SCF35 · ' + key.replace('_', ' '))
        cron = '0 8 * * *' if key == 'users' else ('0 10 * * *' if key == 'users_validation' else '0 9 * * *')
        run(client, state, key, piece, 'result_scf_' + key, cron)


if __name__ == '__main__':
    main()
