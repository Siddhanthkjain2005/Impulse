import numpy as np
import pandas as pd
from backend.app.data.workbook_reference import calculate
from backend.app.ml.reference_knn import WorkbookKNN, data, metrics, PHYSICS, OBSERVED

def test_golden_case():
    c=calculate()
    assert c['stages']==9 and c['front_r_stage']==50 and c['tail_r_stage']==25
    assert abs(c['charge_kv_stage']-193.08943089430895)<1e-10
    np.testing.assert_allclose([c['front_us'],c['tail_us'],c['crest_kv']],
                               [1.2100299583068181,52.20888749999999,1425],rtol=1e-12)
    q=pd.DataFrame([{'Impulse_Type':'Lightning','Test_kV':1425,'Load_C_pF':850,'Divider_C_pF':500,
                     'Stray_C_pF':150,'L_uH':18.5,'Efficiency':.82,'Front_R_Stage':50,'Tail_R_Stage':25}])
    hybrid=np.array([c['front_us'],c['tail_us'],c['crest_kv']])+WorkbookKNN().predict(q)[0]
    np.testing.assert_allclose(hybrid,[1.204896648838928,51.963708586038585,1432.94658495185],rtol=1e-11)

def test_recomputed_validation_metrics_source_discrepancy_recorded():
    df=data(); v=df[df.Split=='Validation']
    pred=v[PHYSICS].to_numpy()+WorkbookKNN().predict(v)
    actual=metrics(v[OBSERVED].to_numpy(),pred)
    # Published cells are hardcoded, not linked to Validation predictions. Their
    # provenance is unresolved; these are independently recomputed formula results.
    expected={'mae':[.8153730289623604,12.114165288224175,4.039247248702057],
              'rmse':[1.3346134941786894,19.913511096430508,4.844687368114069],
              'mape_pct':[.6198201138622919,1.0812152328067108,.3293284843349127],
              'r2':[.999885667099204,.9997362821308691,.9994302467618357]}
    for k in expected: np.testing.assert_allclose(actual[k],expected[k],rtol=1e-9,atol=1e-10)

def test_every_golden_helper_distance_and_weight():
    import json
    from pathlib import Path
    snap=json.loads((Path(__file__).parents[1]/'artifacts/reference_workbook_snapshot.json').read_text())
    cells=snap['sheets']['ML Helper']['cells']; k=WorkbookKNN()
    q=np.array([1425,850,500,150,18.5,.82,50,25])
    d=np.sum(((k.x-q)/k.scale)**2,axis=1)+(k.types!='Lightning')
    expected=np.array([cells[f'J{i}']['value'] for i in range(2,1402)])
    np.testing.assert_allclose(d,expected,rtol=1e-10,atol=1e-12)
    use=d<=np.partition(d,6)[6]
    weights=np.where(use,1/(d+1e-6),0)
    expected_weights=np.array([cells[f'O{i}']['value'] for i in range(2,1402)])
    np.testing.assert_allclose(weights,expected_weights,rtol=1e-10,atol=1e-12)

def test_source_split_and_columns():
    df=data()
    assert len(df)==2000 and len(df.columns)==22
    assert df.groupby('Split').size().to_dict()=={'Hidden Test':300,'Train':1400,'Validation':300}
    assert set(WorkbookKNN().train.Split)=={'Train'}
