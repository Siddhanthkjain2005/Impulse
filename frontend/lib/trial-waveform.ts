import {Data} from './api';

export function comparisonWaveform(trial:Data|null|undefined):Data|undefined {
  if(!trial)return undefined;
  if(trial.comparison_waveform)return trial.comparison_waveform;
  const wave=trial.waveform;
  if(!wave)return undefined;
  const baseline=trial.processing?.baseline_kv??trial.measured?.baseline_kv??0;
  const origin=trial.processing?.time_origin_us??trial.measured?.time_origin_us??0;
  const polarity=trial.processing?.polarity??trial.measured?.polarity??1;
  return {...wave,time_us:wave.time_us.map((t:number)=>t-origin),
    voltage_kv:wave.voltage_kv.map((v:number)=>(v-baseline)*polarity)};
}
