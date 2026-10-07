'use client';
import {ArrowUpRight} from 'lucide-react';
import {apiUrl,Data,fmt} from '@/lib/api';
import {Badge,Panel} from './workspace';

function CrestStudy({study,version,description}:{study:Data;version:string;description:string}){
 return <Panel title={`Switching crest · ${version.toUpperCase()} focused study`} eyebrow="REPEATED NESTED DEVELOPMENT COMPARISON" action={<Badge tone="amber">{study.promotion_eligible?'Independent check needed':'Gate not met · serving unchanged'}</Badge>}>
  <p className="panel-note">{description} Each of three fold arrangements reserves its own held rows.</p>
  <div className="table-wrap"><table><thead><tr><th>Repeated development comparison</th><th>RMSE (kV)</th><th>95th percentile error (kV)</th><th>Worst error (kV)</th></tr></thead><tbody>{Object.entries(study.combined_repeated_development_metrics||{}).map(([name,m]:[string,any])=><tr key={name}><td>{name}</td><td>{fmt(m.rmse_kv,5)}</td><td>{fmt(m.p95_absolute_error_kv,5)}</td><td>{fmt(m.worst_absolute_error_kv,5)}</td></tr>)}</tbody></table></div>
  <p className="panel-note">The search beat both baselines in {study.folds_beating_both_baselines} / 15 folds. The fixed gate requires at least 2% lower error against both baselines in every fold arrangement. {study.decision}</p>
  <p className="panel-note">{study.scope}</p>
  <a className="button text-button" href={apiUrl(`/api/documents/accuracy_${version}_results`)} target="_blank" rel="noreferrer">Read the {version.toUpperCase()} crest study <ArrowUpRight size={14}/></a>
 </Panel>;
}

export default function BenchmarkComparison({data}:{data:Data}){
 const saved=data.benchmark_scorecard;
 if(!saved)return null;
 const frozen=saved.frozen_v1?.comparisons||[];
 const physics=frozen.find((c:Data)=>c.baseline==='Physics only');
 const knn=frozen.find((c:Data)=>c.baseline==='Exact workbook kNN');
 const development=saved.development_v2?.comparisons?.find((c:Data)=>c.baseline==='Matched exact kNN');
 return <>
 <Panel title="Which baseline do the six outputs beat?" eyebrow="SAVED RESULTS · DIFFERENT EVALUATIONS" action={<Badge>Lower RMSE counts</Badge>}>
  <div className="summary-cards">
   <div><span>V1 · FROZEN TEST VS PHYSICS</span><strong>{physics?.lower_error_targets??'—'} / 6</strong><small>Outputs with lower error</small></div>
   <div><span>V1 · FROZEN TEST VS WORKBOOK</span><strong>{knn?.lower_error_targets??'—'} / 6</strong><small>Switching crest remains higher</small></div>
   <div><span>V2 · DEVELOPMENT CV VS WORKBOOK</span><strong>{development?.lower_error_targets??'—'} / 6</strong><small>Experimental · separate from the test</small></div>
  </div>
  <div className="table-wrap"><table><thead><tr><th>Frozen V1 output</th><th>V1 RMSE</th><th>Workbook kNN RMSE</th><th>Compared with workbook</th></tr></thead><tbody>{knn?.targets?.map((row:Data)=><tr key={`${row.impulse_type}-${row.target}`}><td>{row.impulse_type} · {row.target}</td><td>{fmt(row.model_rmse,5)} {row.unit}</td><td>{fmt(row.baseline_rmse,5)} {row.unit}</td><td className={row.verdict==='LOWER ERROR'?'positive':row.verdict==='HIGHER ERROR'?'negative':'muted'}>{row.verdict==='NOT RECORDED'?'Not recorded':row.verdict==='TIE'?'Equal error':`${fmt(Math.abs(row.rmse_reduction_pct),2)}% ${row.verdict==='LOWER ERROR'?'lower':'higher'} error`}</td></tr>)}</tbody></table></div>
  <p className="panel-note">These counts compare error across six outputs; they are not percentages of correct shots. V2’s 6 / 6 result uses development folds and does not change V1’s saved test result. {saved.frozen_v1?.scope}</p>
 </Panel>
 {data.experiment_v6&&<CrestStudy study={data.experiment_v6} version="v6" description="The study compares smooth relative corrections, voltage-weighted fits and local residual averaging against both V2 and exact workbook kNN."/>}
 {data.experiment_v7&&<CrestStudy study={data.experiment_v7} version="v7" description="The follow-up compares regularized spline envelopes, quantile centers and Bayesian fits against the same baselines and a fixed compact spline control. Observed extremes are not proven noise bounds."/>}
 </>;
}
