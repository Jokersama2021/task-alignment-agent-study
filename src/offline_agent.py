#!/usr/bin/env python3
"""Deterministic source-card agent fixture; Python standard library only.

This coursework fixture uses a fixed policy and summary template. It does not
call an LLM, framework, network service, shell tool, or hidden teacher policy.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'agent'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def tokens(text):
    return set(re.findall(r'[a-z0-9]+|[\u3400-\u9fff]+', text.casefold()))


def search(pack, query):
    if not isinstance(query, str) or not query.strip() or len(query) > 200:
        raise ValueError('invalid_query')
    wanted = tokens(query)
    if not wanted:
        raise ValueError('empty_query_tokens')
    matches = []
    for card in pack['sources']:
        available = tokens(card['title'] + ' ' + ' '.join(card['keywords']))
        if wanted <= available:
            matches.append({k: card[k] for k in ('source_id', 'title', 'url')})
    return sorted(matches, key=lambda x: x['source_id'])


def brief(contract, cards):
    paragraphs = [
        '# 工具型智能體提示注入防禦的離線來源簡報',
        '**研究問題：** ' + contract['research_question'],
        '**整理方式：** 本文由固定程式摘述已核讀來源卡，沒有呼叫語言模型；來源卡是對真實論文的AI 輔助核讀記錄。',
    ]
    for card in cards:
        paragraphs.append(card['brief_summary_zh'].strip() + ' 限制：' + card['brief_limitation_zh'].strip() + f" [{card['source_id']}]")
    paragraphs.append('**整合：** 三份來源依序用於方法、可執行評測環境與網頁攻擊場景的對照。這份來源整理不等於重新執行三篇論文；任何效能結論仍受各文實驗設定限制。')
    paragraphs.append('## 來源')
    for card in cards:
        paragraphs.append(f"[{card['source_id']}] {card['citation']} {card['url']}")
    result = '\n\n'.join(paragraphs) + '\n'
    if len(result) > contract['brief_max_characters']:
        raise ValueError(f'brief_exceeds_character_budget:{len(result)}')
    return result


def inputs(data):
    contract = load(data / 'task-contract.json')
    schema = load(data / 'tool-schema.json')
    if contract.get('output_path') != 'final-brief.md' or contract.get('comparison_values') != [3, 6]:
        raise ValueError('unsupported_output_path_or_comparison_values')
    if set(schema.get('tools', {})) != {'search_catalog', 'read_source', 'write_brief'}:
        raise ValueError('unsupported_tool_schema')
    pack_bytes = (data / 'source-pack.json').read_bytes()
    pack = json.loads(pack_bytes)
    cards = pack['sources']
    required = contract['required_source_ids']
    if [c['source_id'] for c in cards] != required or len(set(required)) != 3:
        raise ValueError('source_pack_must_contain_required_three_unique_ids_in_order')
    for card in cards:
        for key in ('title', 'citation', 'url', 'summary_zh', 'limitation_zh', 'brief_summary_zh', 'brief_limitation_zh'):
            if not isinstance(card.get(key), str) or not card[key].strip():
                raise ValueError(f'missing_source_field:{card["source_id"]}:{key}')
        if not isinstance(card.get('keywords'), list) or not all(isinstance(k, str) for k in card['keywords']):
            raise ValueError('invalid_source_keywords')
    if [x['source_id'] for x in search(pack, contract['query'])] != required:
        raise ValueError('required_sources_do_not_match_query')
    if search(pack, 'qzx_unrelated_nonexistent_9347'):
        raise ValueError('search_does_not_filter_unmatched_queries')
    brief(contract, cards)
    return contract, schema, pack, digest(pack_bytes)


def run_condition(data, out, max_steps, invocation):
    contract, schema, pack, pack_hash = inputs(data)
    out.mkdir(parents=True, exist_ok=False)
    for name in ('task-contract.json', 'tool-schema.json', 'source-pack.json'):
        shutil.copyfile(data / name, out / name)
    by_id = {c['source_id']: c for c in pack['sources']}
    state = {'searched': False, 'allowed_ids': [], 'read_ids': [], 'brief_written': False}
    trajectory, results = [], []
    previous = '0' * 64
    started = datetime.now(timezone.utc).isoformat()
    stop = 'max_steps_exhausted'

    def call(tool, arguments):
        nonlocal previous
        before = json.loads(json.dumps(state))
        try:
            if tool not in schema['tools']:
                raise ValueError('unknown_tool')
            if set(arguments) != set(schema['tools'][tool]['parameters']):
                raise ValueError('unexpected_or_missing_arguments')
            if tool == 'search_catalog':
                if state['searched']:
                    raise ValueError('duplicate_search')
                matches = search(pack, arguments['query'])
                observation = {'matches': matches, 'query_tokens': sorted(tokens(arguments['query'])), 'source_pack_sha256': pack_hash}
                state.update(searched=True, allowed_ids=[m['source_id'] for m in matches])
            elif tool == 'read_source':
                sid = arguments['source_id']
                if sid not in state['allowed_ids'] or sid in state['read_ids'] or sid not in by_id:
                    raise ValueError('unsearched_unknown_or_duplicate_source')
                card = by_id[sid]
                observation = {'source_id': sid, 'card': card, 'card_sha256': digest(canonical(card)), 'source_pack_sha256': pack_hash}
                state['read_ids'].append(sid)
            else:
                if state['read_ids'] != contract['required_source_ids'] or state['brief_written']:
                    raise ValueError('write_requires_all_three_reads_once')
                expected = brief(contract, [by_id[sid] for sid in state['read_ids']])
                if arguments != {'path': contract['output_path'], 'content': expected}:
                    raise ValueError('write_path_or_content_not_allowed')
                payload = expected.encode('utf-8')
                with (out / contract['output_path']).open('xb') as handle:
                    handle.write(payload)
                observation = {'path': contract['output_path'], 'bytes_written': len(payload), 'sha256': digest(payload), 'source_ids': state['read_ids'].copy()}
                state['brief_written'] = True
            result = {'step': len(results) + 1, 'tool': tool, 'arguments': arguments, 'ok': True, 'observation': observation}
        except (KeyError, TypeError, ValueError, OSError) as error:
            result = {'step': len(results) + 1, 'tool': tool, 'arguments': arguments, 'ok': False, 'error': str(error), 'retryable': False}
        results.append(result)
        event = {'step': len(results), 'action': {'tool': tool, 'arguments': arguments}, 'state_before': before, 'state_after': json.loads(json.dumps(state)), 'result_sha256': digest(canonical(result)), 'previous_event_sha256': previous}
        event['event_sha256'] = digest(canonical(event))
        previous = event['event_sha256']
        trajectory.append(event)
        return result['ok']

    for _ in range(max_steps):
        if not state['searched']:
            tool, args = 'search_catalog', {'query': contract['query']}
        elif any(s not in state['read_ids'] for s in contract['required_source_ids']):
            sid = next(s for s in contract['required_source_ids'] if s not in state['read_ids'])
            tool, args = 'read_source', {'source_id': sid}
        else:
            tool, args = 'write_brief', {'path': contract['output_path'], 'content': brief(contract, [by_id[s] for s in state['read_ids']])}
        if not call(tool, args):
            stop = 'tool_error_fail_closed'
            break
        if state['brief_written']:
            stop = 'brief_written_pending_independent_validation'
            break
    for name, rows in [('trajectory.jsonl', trajectory), ('tool-results.jsonl', results)]:
        (out / name).write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows), encoding='utf-8')
    save(out / 'provenance.json', {
        'mode': 'deterministic_fixture', 'fixture_origin': 'coursework implementation with independently prepared cards of real papers',
        'policy': 'fixed deterministic tool loop', 'brief_generation': 'fixed source-card summary template, not an LLM',
        'api_used': False, 'model_used': False, 'network_used': False, 'gpu_used': False, 'framework_used': False,
        'source_cards': 'AI-assisted reading and summarization of cited real papers; see source-pack reading coverage',
        'max_steps': max_steps, 'tool_calls': len(results), 'read_ids': state['read_ids'], 'stop_reason': stop,
        'source_pack_sha256': pack_hash, 'task_contract_sha256': digest((out/'task-contract.json').read_bytes()),
        'tool_schema_sha256': digest((out/'tool-schema.json').read_bytes()), 'runner_sha256': digest(Path(__file__).read_bytes()),
        'trajectory_tail_sha256': previous, 'command': invocation, 'cwd': str(Path.cwd()),
        'python_version': sys.version, 'platform': platform.platform(), 'started_utc': started,
        'finished_utc': datetime.now(timezone.utc).isoformat(),
    })
    (out / 'error-note.md').write_text(
        '# 執行記錄\n\n'
        f'- max_steps：{max_steps}；實際 tool calls：{len(results)}；成功讀取：{len(state["read_ids"])}。\n'
        f'- 停止原因：`{stop}`。\n'
        '- 3 步條件的預算在搜尋與兩次讀取後耗盡；不得建立聲稱完成的 brief。\n'
        '- 6 步條件可容納固定的五次工具呼叫；仍須獨立驗證檔案內容、引用與軌跡。\n'
        '- 此比較只檢驗固定流程是否容納於預算，不能推論真實模型能力或步數的一般效果。\n'
        '- 下一測試可增加有歧義的候選來源再固定預算；本次未執行。\n', encoding='utf-8')
    return {'max_steps': max_steps, 'tool_calls': len(results), 'sources_read': len(state['read_ids']), 'brief_written': state['brief_written'], 'stop_reason': stop}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=DATA)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'results'/'agent')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        contract, _, _, pack_hash = inputs(args.data_dir)
        if args.check:
            print('READY deterministic_fixture sources=3 query_matching=PASS stdlib_only=true')
            print('SOURCE_PACK_SHA256 ' + pack_hash)
            return 0
        for budget in contract['comparison_values']:
            if (args.output_dir / f'max_steps_{budget}').exists():
                raise ValueError('output_exists; choose a fresh --output-dir to preserve evidence')
        args.output_dir.mkdir(parents=True, exist_ok=True)
        invocation = [sys.executable, *sys.argv]
        rows = [run_condition(args.data_dir, args.output_dir/f'max_steps_{b}', b, invocation) for b in contract['comparison_values']]
        save(args.output_dir/'run-summary.json', rows)
        for row in rows:
            print(f"RUN max_steps={row['max_steps']} calls={row['tool_calls']} reads={row['sources_read']} brief={row['brief_written']}")
        print('Run src/verify_agent_evidence.py for independent final-state validation.')
        return 0
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        print(f'NOT READY/ERROR {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
