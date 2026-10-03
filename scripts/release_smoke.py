"""Launch a fresh local audit store and deny external network access in-process."""
import json
import os
from pathlib import Path
import socket
import tempfile


def main():
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='impulse-release-') as folder:
        os.environ['IMPULSETWIN_DB']=str(Path(folder)/'fresh.sqlite3')
        original_connect=socket.socket.connect
        original_dns=socket.getaddrinfo
        def connect(sock,address):
            if isinstance(address,tuple) and address[0] not in ('127.0.0.1','::1','localhost'):
                raise RuntimeError('External network forbidden during release smoke')
            return original_connect(sock,address)
        def dns(host,*args,**kwargs):
            if host not in ('127.0.0.1','::1','localhost',None):
                raise RuntimeError('External DNS forbidden during release smoke')
            return original_dns(host,*args,**kwargs)
        socket.socket.connect=connect; socket.getaddrinfo=dns
        from fastapi.testclient import TestClient
        from backend.app.main import app
        from backend.app import storage
        from scripts.verify_release import static_assets
        try:
            with TestClient(app) as client:
                assert client.get('/api/health').status_code==200
                assert client.get('/api/runs').json()==[]
                assert client.get('/api/laboratory-evidence').json()['measured_captures']==0
                for route in ['/','/judge/','/laboratory-evidence/','/hardware-verification/','/experiment-timeline/','/search-quality/','/docs']:
                    assert client.get(route).status_code==200,route
                assets=static_assets(root); assert assets['status']=='PASS',assets
                for asset in assets['local_assets']:assert client.get(asset).status_code==200,asset
                response=client.post('/api/optimize',json={'stage_min':9,'stage_max':9,'monte_carlo_samples':8})
                assert response.status_code==200,response.text
                run=response.json()
                assert client.get(f"/api/runs/{run['id']}/judge").status_code==200
                assert client.get(f"/api/runs/{run['id']}/report").status_code==200
                assert client.get('/api/source-status').json()['dataset_hash_matches_frozen_model']
                print(json.dumps({'status':'PASS','fresh_database':True,'external_network_denied':True,
                                  'local_assets':len(assets['local_assets']),'saved_recommendation':True}))
        finally:
            storage.engine.dispose()
            socket.socket.connect=original_connect; socket.getaddrinfo=original_dns


if __name__=='__main__':main()
