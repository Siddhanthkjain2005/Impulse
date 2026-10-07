export type Data = Record<string, any>;
export const workbookInputs:Data = {profile_id:'workbook_reference_profile',impulse_type:'Lightning',test_kv:1425,load_c_pf:850,divider_c_pf:500,stray_c_pf:150,l_uh:18.5,efficiency:.82,solver:'reference',model_mode:'hybrid',require_model_agreement:false,connection_mode:'series_marx_equivalent',layout_id:'default-layout',uncertainty_pct:5,monte_carlo_samples:32,max_components_per_network:24,include_base_c:false};
// Physical reference first. Parasitics are editable example inputs; stock remains unknown.
export const initialInputs:Data = {...workbookInputs,profile_id:'cpri_problem_brief_profile',load_c_pf:650,divider_c_pf:250,stray_c_pf:55,l_uh:12,efficiency:.83,solver:'circuit',model_mode:'physics',include_base_c:true};
export function profileInputs(values:Data,profileId:string):Data {
  const workbook=profileId==='workbook_reference_profile';
  return {...values,profile_id:profileId,solver:workbook?'reference':'circuit',model_mode:workbook?'hybrid':'physics',include_base_c:!workbook,require_model_agreement:false,inventory_override:null,calibration_id:null,confirm_reference_mismatch:false};
}
export function solverInputs(values:Data,solver:string):Data {
  return {...values,solver,model_mode:solver==='circuit'||values.profile_id!=='workbook_reference_profile'?'physics':values.model_mode,require_model_agreement:solver==='reference'&&!!values.require_model_agreement};
}
export function apiUrl(path:string) { return `${typeof window !== 'undefined' && window.location.port==='3000' ? 'http://127.0.0.1:8000' : ''}${path}`; }
export async function api(path:string, options:RequestInit={}) {const res=await fetch(apiUrl(path),{...options,headers:{...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),...options.headers}});if(!res.ok){let body;try{body=await res.json()}catch{throw new Error(`Service returned ${res.status}. Check the local backend.`)} const d=body.detail;throw new Error(typeof d==='string'?d:Array.isArray(d)?d.map((e:Data)=>`${e.loc?.slice(1).join('.')}: ${e.msg}`).join('; '):`Request failed (${res.status})`)}return res.json();}
export const post=(path:string,body:unknown)=>api(path,{method:'POST',body:JSON.stringify(body)});
export const fmt=(v:unknown,digits=2)=>typeof v==='number'&&Number.isFinite(v)?(Number(v.toFixed(digits))===0?0:v).toLocaleString('en-US',{maximumFractionDigits:digits,minimumFractionDigits:digits}):'—';
export const human=(s:string)=>s?.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
