"""Print an exact compact summary of both saved, independently checked runs."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
print('ACTUAL SAVED RUNS | Qwen3.5-4B | RTX 5090 | 2026-10-27')
print('24 distinct cases; v2 reuses v1 cases after engineering repair.')
print('version stage   valid  aligned allow  off-task flag  format errors')
for v,d in [('v1','shield'),('v2','shield-v2')]:
 m=json.loads((root/'results'/d/'metrics.json').read_text())
 for stage in ['input','action']:
  g=m['groups'][stage]
  print(f"{v:7s} {stage:6s} {g['valid_classifier_cases']:2d}/12       {g['aligned_effective_accept_count']}/6           {g['misaligned_effective_flag_or_block_count']}/6             {g['parse_or_context_errors']:2d}")
 print(f"{v}: {m['model_calls']} calls; {m['output_tokens']} output tokens; generation {m['generation_seconds']:.2f}s")
print('OFFLINE FIXTURE | max_steps=3: 3 calls, 2 reads, FAIL')
print('OFFLINE FIXTURE | max_steps=6: 5 calls, 3 reads, PASS')
print('Gate events are inert. A parse-failure block is not semantic success.')
