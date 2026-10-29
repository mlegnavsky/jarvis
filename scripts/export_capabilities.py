"""Export implemented Admin field schemas without importing HA/runtime dependencies."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['jarvis/app/admin.py', 'jarvis/app/workspace_admin.py', 'jarvis/app/firmware.py', 'jarvis/app/operations.py','jarvis/app/deployments.py']

def export():
    operations = {}
    for source in SOURCES:
        tree = ast.parse((ROOT / source).read_text())
        field_map = next(n.value for n in tree.body if isinstance(n, ast.Assign)
                         and any(isinstance(t, ast.Name) and t.id == 'FIELDS' for t in n.targets))
        for key, value in zip(field_map.keys, field_map.values):
            if key is None:  # merged modules are exported separately
                continue
            fields = [] if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'set' and not value.args else sorted(ast.literal_eval(value))
            operations[ast.literal_eval(key)] = {'arguments': fields, 'source': source}
    return {'schema_version': 1, 'scope': 'implemented_source_contract_not_live_authorization',
            'repository': 'mlegnavsky/jarvis', 'deployment_branch': 'feat/jarvis-addon',
            'entrypoint': {'service': 'jarvis.admin', 'entity_id': 'jarvis.system'},
            'completion_state': 'verified', 'unknown_outcome': 'reconcile_before_retry',
            'operations': dict(sorted(operations.items())),
            'known_missing': ['hosted_container_runtime_access', 'verified_discovery_channel_link'],
            'workflow': 'docs/WORK-MANIFEST.md', 'open_work': 'docs/OPEN-WORK.md'}

if __name__ == '__main__':
    output = ROOT / 'docs/operations-manifest.json'
    output.write_text(json.dumps(export(), ensure_ascii=False, indent=2) + '\n')
    print(f'{output.relative_to(ROOT)}: {len(export()["operations"])} implemented operations')
