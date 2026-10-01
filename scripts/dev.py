"""Start the single-origin offline application from the repository root."""
import os
from pathlib import Path
import sys
import uvicorn

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT); sys.path.insert(0,str(ROOT))
os.environ.setdefault('LOKY_MAX_CPU_COUNT','4')
os.environ.setdefault('OMP_NUM_THREADS','1')
if not (ROOT/'frontend/out/index.html').exists():
    raise SystemExit('Frontend export missing. Run make build first (Node.js 22+ required).')
if not (ROOT/'artifacts/models/residual_models.joblib').exists():
    raise SystemExit('Frozen models missing. Run make train first.')
print('ImpulseTwin AI: http://127.0.0.1:8000  |  Ctrl+C to stop',flush=True)
uvicorn.run('backend.app.main:app',host='127.0.0.1',port=8000,log_level='warning')
