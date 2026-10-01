"""Shared interpolation-based analyzer for simulated and uploaded waveforms."""
import numpy as np
from scipy.optimize import brentq

def crossing(t,v,level,start=0,rising=True):
    a=v[start:-1]; b=v[start+1:]
    match=(a<=level)&(b>=level) if rising else (a>=level)&(b<=level)
    indices=np.flatnonzero(match)
    if not len(indices): raise ValueError(f'Waveform does not contain a {level:g} kV crossing.')
    i=int(indices[0])+start
    if v[i+1]==v[i]: return float(t[i])
    return float(t[i]+(t[i+1]-t[i])*(level-v[i])/(v[i+1]-v[i]))

def analyze(time_us,voltage_kv,impulse_type='Lightning',baseline_kv=0.,time_origin_us=0.):
    t=np.asarray(time_us,float); raw=np.asarray(voltage_kv,float)
    if len(t)<10 or len(t)!=len(raw): raise ValueError('Waveform requires at least 10 paired samples.')
    if not np.isfinite(t).all() or not np.isfinite(raw).all(): raise ValueError('Waveform contains non-finite samples.')
    if not np.isfinite(baseline_kv) or not np.isfinite(time_origin_us): raise ValueError('Baseline and time origin must be finite.')
    if impulse_type not in ['Lightning','Switching']: raise ValueError('Unknown impulse type.')
    if not (np.diff(t)>0).all(): raise ValueError('Time must be strictly increasing without duplicate samples.')
    v=raw-baseline_kv; polarity=1 if abs(v.max())>=abs(v.min()) else -1; v*=polarity
    peak=int(np.argmax(v)); crest=float(v[peak])
    if crest<=0 or peak in (0,len(v)-1): raise ValueError('A resolved interior crest and both waveform limbs are required.')
    t30=crossing(t[:peak+1],v[:peak+1],crest*.3)
    t90=crossing(t[:peak+1],v[:peak+1],crest*.9)
    t50=crossing(t,v,crest*.5,peak,False)
    virtual=t30-.5*(t90-t30)
    if impulse_type=='Switching' and not t[0]<=time_origin_us<t30:
        raise ValueError('Switching impulse onset must be inside the captured time range and before the rising 30% crossing. Set time_origin_us explicitly.')
    front=1.67*(t90-t30) if impulse_type=='Lightning' else float(t[peak]-time_origin_us)
    tail=t50-(virtual if impulse_type=='Lightning' else time_origin_us)
    dif=np.diff(v); reversals=int(np.sum((dif[:-1]>0)&(dif[1:]<0)))
    return {'front_us':float(front),'tail_us':float(tail),'crest_kv':crest,'peak_time_us':float(t[peak]),
            't30_us':t30,'t90_us':t90,'t50_us':t50,'virtual_origin_us':float(virtual),
            'polarity':polarity,'local_maxima_count':reversals,'ringing_detected':reversals>1,
            'baseline_kv':float(baseline_kv),'time_origin_us':float(time_origin_us),'definition':'virtual front/origin' if impulse_type=='Lightning' else 'challenge time to peak/from explicit onset'}

def waveform_from_metrics(front_us,tail_us,crest_kv,impulse_type='Lightning',points=700):
    """Double-exponential metric reconstruction, not a circuit/ML waveform solver."""
    def unit(r):
        tp=np.log(r)/(r-1); peak=np.exp(-tp)-np.exp(-r*tp)
        f=lambda t: (np.exp(-t)-np.exp(-r*t))/peak
        a=brentq(lambda t:f(t)-.3,0,tp,xtol=1e-14)
        b=brentq(lambda t:f(t)-.9,0,tp,xtol=1e-14)
        half=brentq(lambda t:f(t)-.5,tp,100,xtol=1e-14)
        tf=1.67*(b-a) if impulse_type=='Lightning' else tp
        tt=half-(a-.5*(b-a)) if impulse_type=='Lightning' else half
        return tf,tt,tp,peak
    ratio=front_us/tail_us
    lo,hi=np.log(1.0001),np.log(1e7)
    try: logr=brentq(lambda lr:unit(np.exp(lr))[0]/unit(np.exp(lr))[1]-ratio,lo,hi)
    except ValueError: raise ValueError('Requested front/tail ratio cannot be represented by a double exponential.')
    r=np.exp(logr); tf,tt,tp,peak=unit(r); scale=tail_us/tt
    t=np.unique(np.r_[np.linspace(0,tp*scale*3,points//2),np.linspace(tp*scale,tail_us*5,points//2),tp*scale])
    # Remove numerically coincident samples from our generated grids before export.
    # Uploaded waveforms are still strictly validated and never silently deduplicated.
    t=t[np.r_[True,np.diff(t)>max(1e-12,tail_us*1e-12)]]
    v=crest_kv*(np.exp(-t/scale)-np.exp(-r*t/scale))/peak
    return {'time_us':t.tolist(),'voltage_kv':v.tolist(),'kind':'metric_reconstruction',
            'note':'Double-exponential curve fitted to predicted metrics; not an independently predicted waveform.'}
