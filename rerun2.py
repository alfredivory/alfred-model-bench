import json, sys
sys.path.insert(0, '.')
from src.runner import BenchmarkRunner, load_all_scenarios

r = BenchmarkRunner()
scenarios = {s['_file']: s for s in load_all_scenarios()}

# Run everything EXCEPT R1 tool_orchestration first
tasks = [
    ('deepseek/deepseek-chat-v3-0324', 'long_context'),
    ('qwen/qwen3-30b-a3b', 'instruction_following'),
    ('qwen/qwen3-30b-a3b', 'judgment_calls'),
    ('qwen/qwen3-30b-a3b', 'long_context'),
    ('qwen/qwen3-30b-a3b', 'structured_output'),
    ('qwen/qwen3-30b-a3b', 'tool_orchestration'),
]

new_results = []
for model_id, scenario_name in tasks:
    scenario = scenarios[scenario_name]
    print(f"Running {model_id} × {scenario_name}...", flush=True)
    result = r.run_single({'id': model_id, 'provider': 'openrouter'}, scenario)
    new_results.append(result)
    if result.get('error'):
        print(f"  ERROR: {result['error'][:80]}")
    else:
        print(f"  Score: {result['score']}/100 ({result['duration_s']}s)")

# Now try R1 tool_orchestration
print("\nRunning deepseek/deepseek-r1-0528 × tool_orchestration...", flush=True)
result = r.run_single({'id': 'deepseek/deepseek-r1-0528', 'provider': 'openrouter'}, scenarios['tool_orchestration'])
new_results.append(result)
if result.get('error'):
    print(f"  ERROR: {result['error'][:80]}")
else:
    print(f"  Score: {result['score']}/100 ({result['duration_s']}s)")

# Merge
existing = json.load(open('docs/results.json'))
rerun_keys = {(r['model'], r['scenario']) for r in new_results}
existing['results'] = [r for r in existing['results'] if (r['model'], r['scenario']) not in rerun_keys]
existing['results'].extend(new_results)

from src.report import generate_report
import shutil
report_path = generate_report(existing['results'])
shutil.copy(report_path, 'docs/results.json')
print(f"\nSaved updated results to docs/results.json")

r.close()

by_model = {}
for res in existing['results']:
    by_model.setdefault(res['model'], []).append((res['scenario'], res['score']))
for m in ['deepseek/deepseek-chat-v3-0324', 'deepseek/deepseek-r1-0528', 'qwen/qwen3-30b-a3b']:
    scores = by_model.get(m, [])
    avg = sum(s for _, s in scores) / len(scores) if scores else 0
    print(f"\n{m} ({len(scores)} scenarios, avg {avg:.1f}):")
    for sc, s in sorted(scores):
        print(f"  {sc}: {s}")
