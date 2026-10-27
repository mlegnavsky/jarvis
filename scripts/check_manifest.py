from pathlib import Path
import ast
import re
import yaml

for name in ('jarvis', 'jarvis_updater'):
    directory = Path(name)
    config = yaml.safe_load((directory / 'config.yaml').read_text())
    version = config['version']
    assert isinstance(version, str) and re.fullmatch(r'\d+\.\d+\.\d+', version), f'{name}: invalid release version'
    changelog = (directory / 'CHANGELOG.md').read_text()
    headings = [line for line in changelog.splitlines() if line.startswith('# ')]
    assert headings and headings[0] == f'# {version}', f'{name}: changelog must start with exact manifest version'
    assert all(re.fullmatch(r'# \d+\.\d+\.\d+', line) for line in headings), f'{name}: changelog version headings must have no suffix'
    assert len(headings) == len(set(headings)), f'{name}: duplicate changelog version'
    assert config['slug'] == name
    assert 'aarch64' in config['arch']
    assert config['init'] is False
    assert not config.get('privileged')
    assert not config.get('docker_api')
    assert not config.get('host_network')
    assert not config.get('full_access')
    assert not config.get('host_pid')
    assert not config.get('host_dbus')
    assert set(config['options']) == set(config['schema'])
    assert all('==' in line for line in (directory / 'requirements.txt').read_text().splitlines() if line.strip())
    for source in directory.rglob('*.py'):
        ast.parse(source.read_text())
main = yaml.safe_load(Path('jarvis/config.yaml').read_text())
runtime = ast.parse(Path('jarvis/app/__init__.py').read_text())
runtime_versions = [ast.literal_eval(node.value) for node in runtime.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'VERSION' for target in node.targets)]
assert runtime_versions == [main['version']], 'Jarvis runtime version must match manifest version'
assert main['options']['writes_enabled'] is False
assert main['options']['maintenance_enabled'] is False
assert main['hassio_role'] == 'manager', 'Office administration requires the explicit Supervisor manager role'
assert main.get('map') == [{'type': 'homeassistant_config', 'read_only': False, 'path': '/homeassistant'}], 'Only HA configuration may be mounted'
updater = yaml.safe_load(Path('jarvis_updater/config.yaml').read_text())
assert updater['hassio_role'] == 'manager'
assert updater['options']['updates_enabled'] is False
assert updater.get('ports') == {'8100/tcp': None}, 'Gateway starts internal-only until explicit verified handover'
assert Path('jarvis_updater/gateway/oauth.py').read_text() == Path('jarvis/app/oauth.py').read_text(), 'OAuth source parity must be preserved'
gateway_runtime = ast.parse(Path('jarvis_updater/gateway/__init__.py').read_text())
gateway_versions = [ast.literal_eval(node.value) for node in gateway_runtime.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'GATEWAY_VERSION' for target in node.targets)]
assert gateway_versions == [updater['version']], 'Gateway runtime version must match Updater manifest'
print('Release versions, HA changelogs, manifests, permissions, pinned dependencies and Python syntax: OK')
