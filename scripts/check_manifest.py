from pathlib import Path
import ast
import yaml

for name in ('jarvis', 'jarvis_updater'):
    directory = Path(name)
    config = yaml.safe_load((directory / 'config.yaml').read_text())
    assert config['slug'] == name
    assert 'aarch64' in config['arch']
    assert config['init'] is False
    assert not config.get('privileged')
    assert not config.get('docker_api')
    assert not config.get('host_network')
    assert set(config['options']) == set(config['schema'])
    assert all('==' in line for line in (directory / 'requirements.txt').read_text().splitlines() if line.strip())
    for source in directory.rglob('*.py'):
        ast.parse(source.read_text())
main = yaml.safe_load(Path('jarvis/config.yaml').read_text())
assert main['options']['writes_enabled'] is False
assert main['options']['maintenance_enabled'] is False
assert main['hassio_role'] == 'default'
updater = yaml.safe_load(Path('jarvis_updater/config.yaml').read_text())
assert updater['hassio_role'] == 'manager'
assert updater['options']['updates_enabled'] is False
assert 'ports' not in updater
print('Manifests, permissions, pinned dependencies and Python syntax: OK')
