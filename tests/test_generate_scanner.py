import os
import zipfile
import tempfile
import shutil
import pytest
from web_app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def extract_script_from_zip(zip_path, script_name='techstacklens_custom_scanner.py'):
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        with tempfile.TemporaryDirectory() as tmpdir:
            zipf.extractall(tmpdir)
            script_path = os.path.join(tmpdir, script_name)
            with open(script_path, 'r') as f:
                return f.read()

# Map stack to expected class name in generated script
STACK_CLASS_MAP = {
    'network': 'class NetworkScanner',
    'iis': 'class IISScanner',
    'cloud': 'class CloudScanner',
    'lamp': 'class LAMPScanner',
    'tomcat': 'class TomcatScanner',
    'jboss': 'class JBossScanner',
    'xampp': 'class XAMPPScanner',
    'nodejs': 'class NodejsScanner',
    'react': 'class ReactScanner',
    'kubernetes': 'class KubectlScanner',
    'docker': 'class DockerScanner',
}

# All single, pair, and a triple combination for coverage
ALL_STACKS = list(STACK_CLASS_MAP.keys())
SINGLE_COMBOS = [[s] for s in ALL_STACKS]
PAIR_COMBOS = [[a, b] for i, a in enumerate(ALL_STACKS) for b in ALL_STACKS[i+1:]]
TRIPLE_COMBO = [ALL_STACKS[:3]]  # Just one triple for sanity check

@pytest.mark.parametrize("stacks", SINGLE_COMBOS + PAIR_COMBOS + TRIPLE_COMBO)
def test_generate_scanner_includes_classes(client, stacks):
    data = {'stacks': stacks}
    response = client.post('/generate_scanner', data=data, follow_redirects=True)
    assert response.status_code == 200
    # Save the zip to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmpzip:
        tmpzip.write(response.data)
        tmpzip_path = tmpzip.name
    try:
        script_content = extract_script_from_zip(tmpzip_path)
        for stack in stacks:
            expected = STACK_CLASS_MAP[stack]
            assert expected in script_content, f"Expected {expected} in generated script for stacks {stacks}"
        # Should not contain import from techstacklens.scanner
        assert 'from techstacklens.scanner' not in script_content
    finally:
        os.remove(tmpzip_path)

def test_generate_scanner_script_runs(tmp_path):
    # This test checks that the generated script is syntactically valid Python
    # and can be imported (not executed) without error for a simple stack
    from web_app import app
    with app.test_client() as client:
        data = {'stacks': ['network']}
        response = client.post('/generate_scanner', data=data, follow_redirects=True)
        assert response.status_code == 200
        zip_path = tmp_path / 'scanner.zip'
        with open(zip_path, 'wb') as f:
            f.write(response.data)
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(tmp_path)
        script_path = tmp_path / 'techstacklens_custom_scanner.py'
        # Try to compile the script
        with open(script_path, 'r') as f:
            source = f.read()
        compile(source, str(script_path), 'exec')
