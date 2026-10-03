import hashlib
import importlib
import json
from pathlib import Path
import pytest
from scripts.verify_release import integrity, static_assets


def test_integrity_good_missing_and_changed(tmp_path):
    (tmp_path/'config').mkdir(); path=tmp_path/'frozen.json'; path.write_bytes(b'original evidence')
    manifest={'baseline_commit':'fixture','files':{'frozen.json':hashlib.sha256(path.read_bytes()).hexdigest()}}
    (tmp_path/'config/release_integrity.json').write_text(json.dumps(manifest))
    assert integrity(tmp_path)['status']=='PASS'
    path.write_bytes(b'changed evidence'); assert integrity(tmp_path)['status']=='FAIL'
    path.unlink(); assert integrity(tmp_path)['mismatches']==['frozen.json']


@pytest.mark.parametrize('url,expected',[('/app.js','PASS'),('/missing.js','FAIL'),('https://example.invalid/font.js','FAIL'),('//example.invalid/font.js','FAIL')])
def test_assets_detect_missing_and_remote(tmp_path,url,expected):
    folder=tmp_path/'frontend/out'; folder.mkdir(parents=True)
    (folder/'app.js').write_text('/* local fixture */')
    (folder/'index.html').write_text(f'<script src="{url}"></script>')
    assert static_assets(tmp_path)['status']==expected


def test_empty_export_fails(tmp_path):
    assert static_assets(tmp_path)['status']=='FAIL'


def test_missing_frozen_model_fails_clearly(tmp_path,monkeypatch):
    module=importlib.import_module('backend.app.ml.registry')
    module.registry.cache_clear(); monkeypatch.setattr(module,'ROOT',tmp_path)
    try:
        with pytest.raises(ValueError,match='Restore the committed artifacts'):
            module.registry()
    finally:module.registry.cache_clear()
