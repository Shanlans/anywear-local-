"""Audit a completed real-model run and export evidence without calling a model.

Run with the experiment's recorded engine version and its local data directory.
No credentials, prompts, reasoning or raw model streams are exported.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab.common import NATURAL, WORLDS, canonical, digest
from lab.engine import Engine
from lab.reports import build_report, csv_bytes, export_zip, html_report, replay
from lab.store import Store


def verify(store, run, output):
    row = store.get(run)
    report = build_report(store, run)
    assert report['formal_comparison_eligible'], 'Run is incomplete or excluded from formal comparison'
    assert not row['manifest']['dirty'], 'Experiment started from an uncommitted tree'
    attempts, jobs = store.attempts(run), store.jobs(run)
    assert attempts and all(a['status'] == 'responded' for a in attempts), 'Unresolved or historical failed/unknown attempt'
    assert all(j['status'] == 'committed' for j in jobs), 'Uncommitted decision'
    metadata = [a['metadata'] for a in attempts]
    sessions = [m['session_id'] for m in metadata]
    assert len(set(sessions)) == len(sessions) and all(sessions), 'Session reuse or missing identity'
    assert all(m['actual_model'] == row['config']['model'] for m in metadata), 'Observed model mismatch'
    assert all(m['tools_forwarded'] == 0 and not m['tool_event'] for m in metadata), 'Tool isolation failed'
    assert all(m['input_messages_forwarded'] == 1 and m['requests'] == 1 for m in metadata), 'Context or request isolation failed'
    assert all(m['concordia_version'] == '2.4.0' and m['phase'] == 'READY' and m['sample_text_calls'] == 1 for m in metadata)
    expected = {(w, a) for w in WORLDS for a in row['state']['personas']}
    assert {(j['world'], j['agent']) for j in jobs} == expected, 'Missing private consumer context'
    for aid in row['state']['personas']:
        hashes = {j['metadata']['component_hashes']['persona'] for j in jobs if j['agent'] == aid}
        assert len(hashes) == 1, 'Persona changed between decisions or conditions'
    Engine(row['state']).invariants()
    events = store.event_list(run, 0, 1_000_000)
    assert [e['seq'] for e in events] == list(range(1, row['state']['seq'] + 1)), 'Event sequence gap'
    assert sum(e['kind'] == 'DECISION' for e in events) == len(jobs)
    inventory = {}
    funnel = []
    for world in WORLDS:
        state = row['state']['worlds'][world]
        assert all(a['status'] in NATURAL for a in state['agents'].values())
        assert all(not r['busy'] and not r['queue'] for r in state['resources'].values())
        sold = sum(s['sold'] for s in state['stock'].values())
        paid_events = sum(e['kind'] == 'PURCHASED' and e['world_id'] == world for e in events)
        assert sold == paid_events == len(state['sales'])
        assert all(s['reserved'] == 0 for s in state['stock'].values())
        assert all(s['price_cents'] == row['config']['price_cents'] for s in state['sales'])
        inventory[world] = {'initial_units': sum(s['initial'] for s in state['stock'].values()),
                            'available_units': sum(s['available'] for s in state['stock'].values()),
                            'reserved_units': 0, 'sold_units': sold, 'payment_events': paid_events}
        for kind in ('ARRIVED', 'BROWSED', 'PHYSICAL_RESULT', 'PREVIEW_RESULT', 'PURCHASED', 'GOAL_MET', 'LEFT', 'TIME_LIMIT'):
            selected = [e for e in events if e['world_id'] == world and e['kind'] == kind]
            funnel.append({'world': world, 'stage': kind, 'unique_consumers': len({e['agent_id'] for e in selected}),
                           'event_count': len(selected), 'planned_denominator': row['config']['n_agents']})
    with store.connect() as db:
        assert db.execute('PRAGMA quick_check').fetchone()[0] == 'ok', 'SQLite integrity failed'
        checkpoint = db.execute('SELECT hash FROM checkpoints WHERE run=? ORDER BY seq DESC LIMIT 1', (run,)).fetchone()
        assert checkpoint[0] == row['state_hash'], 'Checkpoint hash mismatch'
    replayed = replay(store, run)
    assert replayed['matched_saved_state'] and replayed['replay_calls'] == 0
    assert store.get(run)['state_hash'] == row['state_hash'], 'Run changed during audit'
    proof = {'run_id': run, 'observed_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
             'formal_eligible': True, 'complete': True, 'logical_contexts': len(expected),
             'cli_attempts': len(attempts), 'unique_sessions': len(set(sessions)),
             'all_tools_zero': True, 'all_input_one': True, 'requests_per_attempt': 1,
             'actual_model': row['config']['model'], 'concordia_version': '2.4.0',
             'failed_attempts': 0, 'unknown_attempts': 0, 'censored': 0,
             'replay_matches': True, 'replay_calls': 0, 'sqlite_quick_check': 'ok',
             'inventory': inventory, 'state_hash': row['state_hash'],
             'code_commit': row['manifest']['git_commit'], 'source_fingerprint': row['manifest']['source_fingerprint'],
             'config_hash': digest(row['config']), 'event_hash': digest(events), 'usage': report['usage'],
             'funnel': funnel, 'statistical_unit': 'one paired shared-store run', 'real_market_evidence': False}
    output.mkdir(parents=True, exist_ok=True)
    (output / f'{run}-verification.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2))
    (output / f'{run}-funnel.csv').write_bytes(csv_bytes(funnel))
    (output / f'{run}-report.zip').write_bytes(export_zip(store, run))
    (output / f'{run}-report.html').write_text(html_report(report))
    print(json.dumps({k: proof[k] for k in ('run_id', 'complete', 'logical_contexts', 'cli_attempts', 'unique_sessions', 'replay_matches')}))
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id')
    parser.add_argument('--output', type=Path, default=Path('.lab-data/deliverables'))
    args = parser.parse_args()
    verify(Store(), args.run_id, args.output)
