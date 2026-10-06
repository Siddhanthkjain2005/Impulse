'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {api,Data,fmt} from '@/lib/api';
import {Badge,Empty,PageHeading,Panel} from './workspace';

const trialSources:Record<string,string>={synthetic_benchmark:'synthetic_benchmark',generated_demo:'generated_demo',generated_stress_test:'generated_demo',measured_lab:'measured_lab'};
export function trialSourceType(trial:Data):string {
  if(typeof trial.evidence?.source_type==='string')return trialSources[trial.evidence.source_type]||'unknown';
  // Historical records lack the backend evidence snapshot. Embedded non-lab origin
  // still defeats a measured declaration, matching the backend admission policy.
  const embedded=trial.provenance?.embedded_metadata?.source_type;
  if(embedded!=null&&trialSources[embedded]!=='measured_lab')return trialSources[embedded]||'unknown';
  return trialSources[trial.source_type]||'unknown';
}
export function SourceBadge({trial}:{trial:Data}) {
  const source=trialSourceType(trial);
  const label=source==='measured_lab'?'MEASURED LAB':source==='synthetic_benchmark'?'SYNTHETIC BENCHMARK':['generated_demo','generated_stress_test'].includes(source)?'GENERATED DEMO':'UNKNOWN SOURCE';
  return <Badge tone={source==='measured_lab'?'cyan':'amber'}>{label}</Badge>;
}

export function EvidenceCard({evidence}:{evidence?:Data}) {
  if(!evidence)return <p className="panel-note">Evidence classification not recorded for this saved recommendation.</p>;
  return <div className="evidence-card"><div className="evidence-level"><span>LEVEL {evidence.level}</span><h3>{evidence.label}</h3></div>
    <div className="evidence-checks">{evidence.checks.map((row:Data)=><div key={row.label}><span>{row.label}</span><Badge tone={row.status==='FAIL'?'red':row.status==='PASS'?'green':'amber'}>{row.status==='PASS'?'✓ ':row.status==='FAIL'?'! ':''}{row.status}</Badge></div>)}</div>
    <p className="panel-note">{evidence.scope}</p></div>;
}

export default function EvidencePage({kind}:{kind:'laboratory'|'hardware'|'timeline'|'search'}) {
  const [data,setData]=useState<any>(null),[error,setError]=useState(''),[profile,setProfile]=useState(0);
  const endpoint={laboratory:'laboratory-evidence',hardware:'hardware-integrity',timeline:'experiment-timeline',search:'search-quality'}[kind];
  const titles={laboratory:'Laboratory Evidence',hardware:'Hardware Verification',timeline:'Experiment Timeline',search:'Search Quality'};
  const descriptions={laboratory:'Trace each capture to its source, saved prediction and acquisition review.',hardware:'Inspect supplied values, derived ratings and the hardware facts still needing confirmation.',timeline:'Five saved model studies. One active default. Every decision retains its evidence.',search:'Compare bounded search with exhaustive enumeration on declared small synthetic spaces.'};
  useEffect(()=>{let alive=true;api(`/api/${endpoint}`).then(d=>{if(alive){setData(d);if(kind==='hardware')setProfile(Math.max(0,d.findIndex((p:Data)=>p.profile_id==='cpri_problem_brief_profile')))}}).catch(e=>{if(alive)setError(e.message)});return()=>{alive=false}},[endpoint]);
  return <><PageHeading title={titles[kind]} description={descriptions[kind]} tag="INSPECTABLE EVIDENCE"/>
    {error&&<div role="alert" className="alert">{error}</div>}{!data&&!error&&<Empty title="Loading saved evidence"/>}
    {data&&kind==='laboratory'&&<>
      <div className="evidence-stats">{[['Measured captures',data.measured_captures],['Usable for calibration',data.usable_for_calibration],['Evaluation eligible',data.eligible_for_independent_evaluation],['Excluded from evaluation',data.excluded_captures]].map(([label,value])=><div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
      {data.empty_message&&<div className="evidence-empty"><Badge tone="cyan">READY FOR FUTURE MEASUREMENTS</Badge><h2>No laboratory measurements have been loaded.</h2><p>Synthetic performance does not establish laboratory accuracy.</p><Link className="button secondary" href="/trial-calibrator/">Import and review a waveform</Link></div>}
      <Panel title="Capture provenance" action={<Link className="button secondary" href="/trial-calibrator/">Upload / evaluate captures</Link>}><p className="panel-note">{data.scope}</p><div className="table-wrap"><table><thead><tr><th>Source</th><th>Capture / setup</th><th>Quality</th><th>Calibration</th><th>Evaluation / exclusions</th></tr></thead><tbody>{data.captures.map((r:Data)=><tr key={r.source_id}><td><SourceBadge trial={r}/></td><td>{r.source_id}<small className="evidence-detail">{r.impulse_type||'Unknown impulse'} · {r.generator_profile||'Unknown profile'}<br/>{r.layout_id||'Unknown layout'} · {r.model_version||'Unknown model'}</small></td><td>{r.quality_status}</td><td>{r.eligible_for_calibration?'ELIGIBLE':'EXCLUDED'}</td><td>{r.eligible_for_external_accuracy?'ELIGIBLE':r.exclusion_reasons.join(' ')}</td></tr>)}</tbody></table></div></Panel>
      <div className="evidence-group-grid">{[['Impulse',data.by_impulse],['Profile',data.by_profile],['Layout',data.by_layout],['Model version',data.by_model]].map(([name,values])=><Panel key={name} title={`Measured captures by ${name.toLowerCase()}`}><dl className="evidence-groups">{Object.entries(values).map(([k,v])=><div key={k}><dt>{k}</dt><dd>{String(v)}</dd></div>)}{!Object.keys(values).length&&<p>No measured captures.</p>}</dl></Panel>)}</div>
    </>}
    {data&&kind==='hardware'&&<><label className="field">Generator profile<select value={profile} onChange={e=>setProfile(Number(e.target.value))}>{data.map((p:Data,i:number)=><option value={i} key={p.profile_id}>{p.profile_name}</option>)}</select></label>
      <div className="alert evidence-conflict"><strong>SEPARATE PHYSICAL AND SYNTHETIC PROFILES</strong><p>Workbook: {data[profile].conflict.workbook.max_stages} stages, {data[profile].conflict.workbook.stage_c_uf} µF/stage. Problem statement: {data[profile].conflict.problem_statement.max_stages} stages, {data[profile].conflict.problem_statement.stage_c_uf} µF/stage.</p><p>{data[profile].conflict.message}</p></div>
      <Panel title={data[profile].profile_name} action={<Badge tone="amber">PHYSICAL VERIFICATION PENDING</Badge>}><p className="panel-note">{data[profile].scope}</p>{data[profile].inventory_override_required&&<p className="alert compact">Stock quantities are unknown. Optimization requires an explicit operator inventory with provenance.</p>}<div className="table-wrap"><table><thead><tr><th>Parameter</th><th>Value</th><th>Status</th><th>Source / interpretation</th></tr></thead><tbody>{data[profile].parameters.map((r:Data)=><tr key={r.parameter}><td>{r.label}</td><td>{r.value===null||Array.isArray(r.value)&&!r.value.length?'Unknown':Array.isArray(r.value)?r.value.join(', '):String(r.value)}</td><td><Badge tone={r.status==='UNKNOWN'?'amber':'neutral'}>{r.status}</Badge></td><td>{r.source||'Not supplied'}<small className="evidence-detail">Profile v{r.profile_version} · Source date {r.source_date||'unknown'}{r.note&&<><br/>{r.note}</>}</small></td></tr>)}</tbody></table></div></Panel></>}
    {data&&kind==='timeline'&&<><p className="alert compact">{data.scope}</p><div className="experiment-timeline">{data.experiments.map((e:Data)=><Panel key={e.name} title={`${e.name} · ${e.version||'No saved artifact'}`} action={<Badge tone={e.status==='PROMOTED'?'green':e.status==='REJECTED'?'amber':'cyan'}>{e.status}</Badge>}><div className="timeline-content"><Badge>{e.evidence_type}</Badge><h3>{e.hypothesis}</h3><p>{e.protocol}</p><dl><div><dt>Comparator</dt><dd>{e.baseline||'Not recorded'}</dd></div>{e.performance_change_pct!=null&&<div><dt>Macro error reduction</dt><dd>{fmt(e.performance_change_pct,4)}% under this development comparison</dd></div>}<div><dt>Promotion criterion</dt><dd>{e.promotion_criterion}</dd></div><div><dt>Decision</dt><dd>{e.decision}</dd></div></dl><details><summary>Saved artifact identity</summary><p>{e.evidence_path}</p><code>{e.evidence_sha256}</code><p>Dataset SHA-256</p><code>{e.dataset}</code>{e.protocol_hash_matches!=null&&<p>Protocol hash: {e.protocol_hash_matches?'MATCH':'MISMATCH'}</p>}</details></div></Panel>)}</div></>}
    {data&&kind==='search'&&(data.status==='PENDING'?<Empty title="Search quality benchmark pending"/>:<><Badge tone="amber">SYNTHETIC ENGINEERING BENCHMARK</Badge><p className="panel-note">{data.scope}</p><div className="evidence-stats">{[['Top-1 match',`${fmt(data.top1_match_rate*100,0)}%`],['Top-3 containment',`${fmt(data.top3_containment_rate*100,0)}%`],['Worst objective gap',fmt(data.worst_objective_gap,5)],['Median runtime speedup',`${fmt(data.median_runtime_speedup,2)}×`]].map(([k,v])=><div key={k}><span>{k}</span><strong>{v}</strong></div>)}</div><Panel title="Bounded vs exhaustive results"><div className="table-wrap"><table><thead><tr><th>Fixed case</th><th>Exhaustive rank of bounded winner</th><th>Objective gap</th><th>Waveform error difference</th><th>Part difference</th><th>Evaluated bounded / exhaustive</th><th>Seconds bounded / exhaustive</th></tr></thead><tbody>{data.cases.map((c:Data)=><tr key={c.id}><td>{c.id}</td><td>{c.bounded_winner_exhaustive_rank??'Not found'}</td><td>{fmt(c.objective_gap,5)}</td><td>{fmt(c.waveform_error_difference,5)}</td><td>{c.component_count_difference}</td><td>{c.bounded_evaluated} / {c.exhaustive_evaluated}</td><td>{fmt(c.bounded_seconds)} / {fmt(c.exhaustive_seconds)}</td></tr>)}</tbody></table></div><p className="panel-note">{data.limitation}</p></Panel></>)}
  </>;
}
