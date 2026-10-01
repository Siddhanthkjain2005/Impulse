"""Workbook asymmetric squared distance, RANK<=7 tie semantics and weights."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
FEATURES=['Test_kV','Load_C_pF','Divider_C_pF','Stray_C_pF','L_uH','Efficiency','Front_R_Stage','Tail_R_Stage']
PHYSICS=['Physics_FrontPeak_us','Physics_Tail_us','Physics_Crest_kV']
OBSERVED=['Observed_FrontPeak_us','Observed_Tail_us','Observed_Crest_kV']
RESIDUAL=['Residual_FrontPeak','Residual_Tail','Residual_Crest']

def data():
    return pd.read_csv(ROOT/'data/processed/synthetic_dataset.csv')

class WorkbookKNN:
    def __init__(self, train=None):
        if train is None:
            df=data(); train=df[df.Split=='Train']
        self.train=train.reset_index(drop=True)
        self.x=self.train[FEATURES].to_numpy(float)
        self.types=self.train.Impulse_Type.to_numpy()
        self.y=self.train[RESIDUAL].to_numpy(float)
        self.scale=np.tile(np.array([1500.,1300.,800.,350.,30.,1.,100.,100.]),(len(train),1))
        self.scale[self.types=='Switching',6:]=30000.

    def predict(self, queries, return_neighbors=False):
        predictions=[]; neighbors=[]
        for _, q in queries.iterrows():
            d=np.sum(((self.x-q[FEATURES].to_numpy(float))/self.scale)**2,axis=1)+(self.types!=q.Impulse_Type)
            cutoff=np.partition(d,6)[6]
            indices=np.flatnonzero(d<=cutoff)
            weights=1/(d[indices]+1e-6)
            predictions.append(np.average(self.y[indices],weights=weights,axis=0))
            order=indices[np.argsort(d[indices])]
            neighbors.append([{'id':str(self.train.iloc[i].ID),'distance_squared':float(d[i]),'split':'Train'} for i in order])
        result=np.array(predictions)
        return (result,neighbors) if return_neighbors else result

def metrics(y,p):
    err=p-y
    ss=np.sum((y-y.mean(axis=0))**2,axis=0)
    return {'mae':np.mean(abs(err),axis=0).tolist(),'rmse':np.sqrt(np.mean(err**2,axis=0)).tolist(),
            'mape_pct':(np.mean(abs(err)/np.maximum(abs(y),1e-12),axis=0)*100).tolist(),
            'r2':(1-np.sum(err**2,axis=0)/ss).tolist()}
