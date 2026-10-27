#!/usr/bin/env python3
"""Independently inspect materialized agent evidence; never import the runner."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def encoded(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def lines(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def validate(folder, data):
    """Reconstruct order and independently verify every successful observation."""
    contract, schema, pack = [read(folder/name) for name in ('task-contract.json', 'tool-schema.json', 'source-pack.json')]
    provenance = read(folder/'provenance.json')
    events, results = lines(folder/'trajectory.jsonl'), lines(folder/'tool-results.jsonl')
    cards = {x['source_id']: x for x in pack['sources']}
    required = contract['required_source_ids']
    checks = {
        'fixed_inputs_match': all((folder/n).read_bytes() == (data/n).read_bytes() for n in ('task-contract.json', 'tool-schema.json', 'source-pack.json')),
        'provenance_hashes_match': all(provenance[k] == sha((folder/n).read_bytes()) for k,n in [('source_pack_sha256','source-pack.json'),('task_contract_sha256','task-contract.json'),('tool_schema_sha256','tool-schema.json')]),
        'runner_hash_matches_shipped_code': provenance.get('runner_sha256') == sha((ROOT/'src'/'offline_agent.py').read_bytes()),
        'deterministic_fixture_disclosed': provenance.get('mode') == 'deterministic_fixture' and all(provenance.get(k) is False for k in ('api_used','model_used','network_used','gpu_used','framework_used')),
        'step_budget': 0 < len(events) <= provenance['max_steps'] and len(events) == provenance['tool_calls'],
        'logs_and_hash_chain': len(events) == len(results),
        'search_matches_query': False,
        'source_content_hashes': True,
        'state_and_call_order': True,
        'all_three_sources_read': False,
        'write_after_reads': False,
        'brief_exists': False,
        'write_receipt_matches_file': False,
        'citations_match_read_sources': False,
        'card_summaries_and_limits_preserved': False,
        'brief_character_budget': False,
    }
    state = {'searched': False, 'allowed_ids': [], 'read_ids': [], 'brief_written': False}
    tail = '0' * 64
    writes = []
    if len(events) != len(results):
        return {'success': False, 'checks': checks, 'failed_checks': [k for k,v in checks.items() if not v]}
    for number, (event,result) in enumerate(zip(events,results), 1):
        original = dict(event)
        logged_hash = original.pop('event_sha256', None)
        checks['logs_and_hash_chain'] &= (
            event.get('step') == number == result.get('step') and
            event.get('previous_event_sha256') == tail and logged_hash == sha(encoded(original)) and
            event.get('result_sha256') == sha(encoded(result)) and
            event.get('action') == {'tool': result.get('tool'), 'arguments': result.get('arguments')}
        )
        tail = logged_hash
        checks['state_and_call_order'] &= event.get('state_before') == state and result.get('ok') is True
        tool, args, observation = result.get('tool'), result.get('arguments',{}), result.get('observation',{})
        checks['state_and_call_order'] &= tool in schema['tools'] and set(args) == set(schema['tools'].get(tool,{}).get('parameters',{}))
        if tool == 'search_catalog':
            wanted = set(re.findall(r'[a-z0-9]+|[\u3400-\u9fff]+', contract['query'].casefold()))
            expected = []
            for sid, card in sorted(cards.items()):
                words = set(re.findall(r'[a-z0-9]+|[\u3400-\u9fff]+', (card['title']+' '+' '.join(card['keywords'])).casefold()))
                if wanted <= words:
                    expected.append({k:card[k] for k in ('source_id','title','url')})
            checks['search_matches_query'] = (
                number == 1 and not state['searched'] and args == {'query':contract['query']} and
                observation.get('matches') == expected and [x['source_id'] for x in expected] == required and
                observation.get('query_tokens') == sorted(wanted) and observation.get('source_pack_sha256') == provenance['source_pack_sha256']
            )
            state.update(searched=True, allowed_ids=[x['source_id'] for x in expected])
        elif tool == 'read_source':
            sid = args.get('source_id')
            checks['state_and_call_order'] &= (
                state['searched'] and not state['brief_written'] and sid in state['allowed_ids'] and sid not in state['read_ids'] and
                len(state['read_ids']) < len(required) and sid == required[len(state['read_ids'])]
            )
            checks['source_content_hashes'] &= (
                sid in cards and observation.get('source_id') == sid and observation.get('card') == cards.get(sid) and
                observation.get('card_sha256') == sha(encoded(cards.get(sid))) and
                observation.get('source_pack_sha256') == provenance['source_pack_sha256']
            )
            state['read_ids'].append(sid)
        elif tool == 'write_brief':
            writes.append(result)
            checks['write_after_reads'] = state['read_ids'] == required and not state['brief_written'] and len(writes) == 1
            checks['state_and_call_order'] &= checks['write_after_reads'] and args.get('path') == contract['output_path']
            state['brief_written'] = True
        else:
            checks['state_and_call_order'] = False
        checks['state_and_call_order'] &= event.get('state_after') == state
    checks['logs_and_hash_chain'] &= tail == provenance.get('trajectory_tail_sha256')
    checks['all_three_sources_read'] = state['read_ids'] == required and provenance.get('read_ids') == required
    brief_path = folder / contract['output_path']
    checks['brief_exists'] = brief_path.is_file()
    if checks['brief_exists']:
        payload = brief_path.read_bytes()
        text = payload.decode('utf-8')
        checks['brief_character_budget'] = len(text) <= contract['brief_max_characters']
        citations = set(re.findall(r'\[(S\d+)\]', text))
        checks['citations_match_read_sources'] = citations == set(required) == set(state['read_ids'])
        checks['card_summaries_and_limits_preserved'] = all(
            c['brief_summary_zh'].strip() + ' 限制：' + c['brief_limitation_zh'].strip() + f' [{sid}]' in text
            and f"[{sid}] {c['citation']} {c['url']}" in text for sid,c in cards.items()
        )
        if len(writes) == 1:
            action, receipt = writes[0]['arguments'], writes[0]['observation']
            checks['write_receipt_matches_file'] = (
                action == {'path':contract['output_path'],'content':text} and
                receipt == {'path':contract['output_path'], 'bytes_written':len(payload), 'sha256':sha(payload), 'source_ids':required}
            )
    return {'success': all(checks.values()), 'checks': checks, 'failed_checks': [k for k,v in checks.items() if not v],
            'max_steps': provenance['max_steps'], 'tool_calls': len(results), 'sources_read':len(state['read_ids']),
            'source_ids':state['read_ids'], 'brief_sha256':sha(brief_path.read_bytes()) if brief_path.is_file() else None}


def safe_validate(folder, data):
    try:
        return validate(folder, data)
    except (ValueError, KeyError, TypeError, OSError, UnicodeError) as error:
        return {'success':False, 'failed_checks':['malformed_or_missing_evidence'], 'error':str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', type=Path, default=ROOT/'results'/'agent')
    parser.add_argument('--data-dir', type=Path, default=ROOT/'data'/'agent')
    args = parser.parse_args()
    rows, reports = [], {}
    for budget in (3,6):
        folder = args.results_dir/f'max_steps_{budget}'
        report = safe_validate(folder,args.data_dir)
        reports[str(budget)] = report
        write(folder/'validation.json', report)
        row = {'max_steps':budget, 'tool_calls':report.get('tool_calls',-1), 'sources_read':report.get('sources_read',-1),
               'validator': 'PASS' if report['success'] else 'FAIL', 'failed_checks':';'.join(report['failed_checks'])}
        rows.append(row)
        with (folder/'evaluation.csv').open('w',newline='',encoding='utf-8') as handle:
            writer = csv.DictWriter(handle,fieldnames=list(row));writer.writeheader();writer.writerow(row)
    with (args.results_dir/'comparison.csv').open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    expected = (not reports['3']['success'] and reports['6']['success'] and
                reports['3'].get('max_steps') == 3 and reports['6'].get('max_steps') == 6 and
                reports['3'].get('tool_calls') == 3 and reports['6'].get('tool_calls') == 5)
    negative = []
    # Quality checks of one completed evidence pack; not comparison conditions.
    if reports['6']['success']:
        parent = args.results_dir/'qa-negative'
        parent.mkdir(exist_ok=True)
        for name, mutate, gate in [
            ('tampered-brief',lambda text:text+'\n未記錄的追加內容。\n','write_receipt_matches_file'),
            ('citation-mismatch',lambda text:text.replace('[S03]','[S99]'),'citations_match_read_sources'),
        ]:
            target=parent/name
            if not target.exists():
                shutil.copytree(args.results_dir/'max_steps_6',target)
                (target/'evaluation.csv').unlink(missing_ok=True)
                path=target/'final-brief.md';path.write_text(mutate(path.read_text(encoding='utf-8')),encoding='utf-8')
                write(target/'qa-case.json',{'role':'negative validator quality check','mutation':name,'not_an_experiment_condition':True})
            result=safe_validate(target,args.data_dir)
            write(target/'validation.json',result)
            detected=not result['success'] and gate in result['failed_checks']
            negative.append({'case':name,'role':'validator quality check, not experimental factor','detected':detected,'failed_checks':result['failed_checks']})
    summary={'independent_validator':True,'runner_imported':False,'comparison_as_expected':expected,'conditions':reports,'negative_quality_checks':negative,
             'all_quality_checks_passed':expected and len(negative)==2 and all(n['detected'] for n in negative),
             'validator_sha256':sha(Path(__file__).read_bytes())}
    write(args.results_dir/'verification.json',summary)
    print(json.dumps({'max_steps_3':rows[0]['validator'],'max_steps_6':rows[1]['validator'],'negative_checks':negative,'PASS':summary['all_quality_checks_passed']},ensure_ascii=False))
    return 0 if summary['all_quality_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
