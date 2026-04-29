"""
UI Routes — added on top of existing API, zero changes to existing routes.
GET /data_generation/v1/home        — job submission frontend
GET /data_generation/v1/jobs/ui     — jobs history (PostgreSQL)
GET /data_generation/v1/download/{job_id} — stream CSV to browser
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from config import OUTPUT_DIR
import db

router = APIRouter(prefix="/data_generation/v1")

@router.get("/download/{job_id}")
async def download_csv(job_id: str):
    path = OUTPUT_DIR / f"generated_{job_id}.csv"
    if not path.exists():
        raise HTTPException(404, "CSV not found")
    def stream():
        with open(path, "rb") as f:
            while chunk := f.read(65536): yield chunk
    return StreamingResponse(stream(), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="generated_{job_id}.csv"'})

# ── Home UI ──────────────────────────────────────────────────────────────────
HOME = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>NeMo Data Designer</title>
<style>
:root{--bg:#0f1117;--card:#1a1d27;--border:#2a2d3e;--accent:#7c3aed;--accent2:#06b6d4;--text:#e2e8f0;--muted:#64748b;--success:#10b981;--danger:#ef4444;--warn:#f59e0b}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:system-ui,sans-serif;min-height:100vh}
header{background:var(--card);border-bottom:1px solid var(--border);padding:1rem 2rem;display:flex;align-items:center;justify-content:space-between}
header h1{font-size:1.2rem;font-weight:700;background:linear-gradient(135deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
header a{color:var(--accent2);text-decoration:none;font-size:.85rem;border:1px solid var(--accent2);padding:.3rem .75rem;border-radius:.4rem}
header a:hover{background:var(--accent2);color:#000}
main{max-width:860px;margin:2rem auto;padding:0 1.5rem}
.card{background:var(--card);border:1px solid var(--border);border-radius:.75rem;padding:1.5rem;margin-bottom:1.25rem}
h2{font-size:.75rem;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:1rem}
label{display:block;font-size:.78rem;color:var(--muted);margin:.8rem 0 .25rem}
label:first-child{margin-top:0}
input,select,textarea{width:100%;background:#0f1117;border:1px solid var(--border);color:var(--text);border-radius:.4rem;padding:.5rem .7rem;font-size:.85rem;outline:none}
input:focus,select:focus,textarea:focus{border-color:var(--accent)}
textarea{resize:vertical;min-height:80px;font-family:monospace;font-size:.78rem}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem}
.btn{padding:.6rem 1.2rem;border:none;border-radius:.45rem;font-size:.85rem;font-weight:600;cursor:pointer}
.btn-primary{background:linear-gradient(135deg,var(--accent),#5b21b6);color:#fff}
.btn-primary:hover{opacity:.85}
.btn-secondary{background:var(--border);color:var(--text)}
.actions{display:flex;gap:.75rem;margin-top:1.25rem}
.col-entry{background:#0f1117;border:1px solid var(--border);border-radius:.45rem;padding:.75rem;margin-top:.5rem;position:relative}
.col-entry button.rm{position:absolute;top:.5rem;right:.5rem;background:none;border:none;color:var(--danger);cursor:pointer;font-size:.8rem}
.add-btn{width:100%;background:none;border:1px dashed var(--border);color:var(--muted);border-radius:.4rem;padding:.35rem;font-size:.8rem;cursor:pointer;margin-top:.5rem}
.add-btn:hover{border-color:var(--accent);color:var(--accent)}
#sbox{display:none;margin-top:1rem;padding:.9rem;border-radius:.5rem;font-size:.85rem;border:1px solid var(--border)}
#sbox.processing{border-color:var(--warn);background:#1c1000}
#sbox.completed{border-color:var(--success);background:#001c10}
#sbox.failed{border-color:var(--danger);background:#1c0000}
code{font-size:.75rem;opacity:.6}
</style></head><body>
<header><h1>🧬 NeMo Data Designer</h1><a href="/synth-data-gen/data_generation/v1/jobs/ui">📋 All Jobs</a></header>
<main>

<div class="card">
  <h2>Model</h2>
  <div class="row2">
    <div><label>Provider</label>
      <select id="model_provider">
        <option value="nvidiabuild">NVIDIA Build</option>
        <option value="openai">OpenAI</option>
        <option value="anthropic">Anthropic</option>
        <option value="groq">Groq</option>
        <option value="google">Google</option>
        <option value="deepseek">DeepSeek</option>
        <option value="mistral">Mistral</option>
        <option value="microsoft">Microsoft Azure</option>
      </select>
    </div>
    <div><label>Model ID</label><input id="model_id" placeholder="qwen/qwen2.5-coder-32b-instruct"/></div>
  </div>
  <label>API Key</label><input id="api_key" type="password" placeholder="nvapi-..."/>
</div>

<div class="card">
  <h2>Settings</h2>
  <div class="row3">
    <div><label>Records</label><input id="num_records" type="number" value="10" min="1"/></div>
    <div><label>Temperature</label><input id="temperature" type="number" value="0.8" step="0.05" min="0" max="2"/></div>
    <div><label>Top P</label><input id="top_p" type="number" value="0.95" step="0.05" min="0" max="1"/></div>
  </div>
  <label>Max Tokens</label><input id="max_tokens" type="number" value="1024"/>
  <label>Seed CSV <span style="opacity:.5">(optional)</span></label>
  <input id="seed" type="file" accept=".csv"/>
</div>

<div class="card">
  <h2>Sampler Columns</h2>
  <div id="samplers"></div>
  <button class="add-btn" onclick="addSampler()">+ Add Sampler Column</button>
</div>

<div class="card">
  <h2>Expression Columns</h2>
  <div id="exprs"></div>
  <button class="add-btn" onclick="addExpr()">+ Add Expression Column</button>
</div>

<div class="card">
  <h2>LLM Text Columns</h2>
  <div id="llmtexts"></div>
  <button class="add-btn" onclick="addLLMText()">+ Add LLM Text Column</button>
</div>

<div class="card">
  <h2>LLM Structured Columns</h2>
  <div id="llmstructs"></div>
  <button class="add-btn" onclick="addLLMStruct()">+ Add LLM Structured Column</button>
</div>

<div class="card">
  <h2>LLM Judge Columns</h2>
  <div id="llmjudges"></div>
  <button class="add-btn" onclick="addLLMJudge()">+ Add LLM Judge Column</button>
</div>

<div class="actions">
  <button class="btn btn-secondary" onclick="submit('preview')">👁 Preview</button>
  <button class="btn btn-primary" onclick="submit('create')">🚀 Create Dataset</button>
</div>
<div id="sbox"></div>
</main>

<script>
const SAMPLER_TYPES=["category","gaussian","uniform","bernoulli","poisson","uuid","datetime","person","person_from_faker","binomial","subcategory","timedelta"];
const v=id=>document.getElementById(id).value.trim();

function addSampler(){
  const id=Date.now(),d=document.createElement('div');
  d.className='col-entry';d.id='s'+id;
  d.innerHTML=`<button class="rm" onclick="this.parentElement.remove()">✕</button>
  <div class="row2"><div><label>Name</label><input id="sn${id}" placeholder="topic"/></div>
  <div><label>Type</label><select id="st${id}">${SAMPLER_TYPES.map(t=>`<option>${t}</option>`).join('')}</select></div></div>
  <label>Params (JSON)</label><textarea id="sp${id}" rows="2" placeholder='{"values":["A","B"]}'></textarea>`;
  document.getElementById('samplers').appendChild(d);
}
function getSamplers(){
  return [...document.querySelectorAll('[id^="sn"]')].map(el=>{
    const id=el.id.slice(2),name=el.value.trim(),type=document.getElementById('st'+id).value,ps=document.getElementById('sp'+id).value.trim();
    if(!name)return null;
    const c={name,sampler_type:type};
    if(ps){try{c.params=JSON.parse(ps)}catch{alert('Bad JSON in sampler: '+name);throw 0}}
    return c;
  }).filter(Boolean);
}

function addExpr(){
  const id=Date.now(),d=document.createElement('div');
  d.className='col-entry';
  d.innerHTML=`<button class="rm" onclick="this.parentElement.remove()">✕</button>
  <div class="row2"><div><label>Name</label><input id="en${id}" placeholder="full_name"/></div>
  <div><label>Expression</label><input id="ee${id}" placeholder="{{ first_name }} {{ last_name }}"/></div></div>`;
  document.getElementById('exprs').appendChild(d);
}
function getExprs(){
  return [...document.querySelectorAll('[id^="en"]')].map(el=>{
    const id=el.id.slice(2),name=el.value.trim(),expr=document.getElementById('ee'+id).value.trim();
    return name&&expr?{name,expr}:null;
  }).filter(Boolean);
}

function addLLMText(){
  const id=Date.now(),d=document.createElement('div');
  d.className='col-entry';
  d.innerHTML=`<button class="rm" onclick="this.parentElement.remove()">✕</button>
  <label>Name</label><input id="ltn${id}" placeholder="generated_content"/>
  <label>Prompt</label><textarea id="ltp${id}" placeholder="Write a {{ format }} about {{ topic }}."></textarea>
  <label>System Prompt <span style="opacity:.5">(optional)</span></label><input id="lts${id}"/>`;
  document.getElementById('llmtexts').appendChild(d);
}
function getLLMText(){
  return [...document.querySelectorAll('[id^="ltn"]')].map(el=>{
    const id=el.id.slice(3),name=el.value.trim(),prompt=document.getElementById('ltp'+id).value.trim(),sys=document.getElementById('lts'+id).value.trim();
    if(!name||!prompt)return null;
    const c={name,prompt};if(sys)c.system_prompt=sys;return c;
  }).filter(Boolean);
}

function addLLMStruct(){
  const id=Date.now(),d=document.createElement('div'),ex=JSON.stringify({type:"object",properties:{sentiment:{type:"string"},score:{type:"integer"}},required:["sentiment","score"]},null,2);
  d.className='col-entry';
  d.innerHTML=`<button class="rm" onclick="this.parentElement.remove()">✕</button>
  <label>Name</label><input id="lsn${id}" placeholder="metadata"/>
  <label>Prompt</label><textarea id="lsp${id}" rows="2" placeholder="Analyze {{ topic }}."></textarea>
  <label>Output Schema (JSON)</label><textarea id="lsf${id}" rows="4">${ex}</textarea>`;
  document.getElementById('llmstructs').appendChild(d);
}
function getLLMStruct(){
  return [...document.querySelectorAll('[id^="lsn"]')].map(el=>{
    const id=el.id.slice(3),name=el.value.trim(),prompt=document.getElementById('lsp'+id).value.trim(),fs=document.getElementById('lsf'+id).value.trim();
    if(!name||!prompt)return null;
    let fmt;try{fmt=JSON.parse(fs)}catch{alert('Bad JSON schema: '+name);throw 0}
    return{name,prompt,output_format:fmt};
  }).filter(Boolean);
}

function addLLMJudge(){
  const id=Date.now(),d=document.createElement('div'),eo=JSON.stringify({"High":"Perfect","Medium":"OK","Low":"Poor"});
  d.className='col-entry';
  d.innerHTML=`<button class="rm" onclick="this.parentElement.remove()">✕</button>
  <label>Name</label><input id="ljn${id}" placeholder="quality_score"/>
  <label>Prompt</label><textarea id="ljp${id}" rows="2" placeholder="Evaluate: {{ generated_content }}"></textarea>
  <div class="row2">
    <div><label>Score Name</label><input id="ljsn${id}" placeholder="relevance"/></div>
    <div><label>Score Description</label><input id="ljsd${id}" placeholder="Does it match the topic?"/></div>
  </div>
  <label>Options (JSON)</label><textarea id="ljso${id}" rows="2">${eo}</textarea>`;
  document.getElementById('llmjudges').appendChild(d);
}
function getLLMJudge(){
  return [...document.querySelectorAll('[id^="ljn"]')].map(el=>{
    const id=el.id.slice(3),name=el.value.trim(),prompt=document.getElementById('ljp'+id).value.trim();
    const sn=document.getElementById('ljsn'+id).value.trim(),sd=document.getElementById('ljsd'+id).value.trim(),os=document.getElementById('ljso'+id).value.trim();
    if(!name||!prompt)return null;
    let opts;try{opts=JSON.parse(os)}catch{alert('Bad JSON options: '+name);throw 0}
    return{name,prompt,scores:[{name:sn,description:sd,options:opts}]};
  }).filter(Boolean);
}

async function submit(mode){
  const payload={
    model_provider:v('model_provider'),model_id:v('model_id'),provider_api_key:v('api_key'),
    num_records:parseInt(v('num_records'))||10,temperature:parseFloat(v('temperature'))||0.8,
    top_p:parseFloat(v('top_p'))||0.95,max_tokens:parseInt(v('max_tokens'))||1024,
  };
  const s=getSamplers(),e=getExprs(),t=getLLMText(),st=getLLMStruct(),j=getLLMJudge();
  if(s.length)payload.sampler_columns=s;
  if(e.length)payload.expression_columns=e;
  if(t.length)payload.llm_text_columns=t;
  if(st.length)payload.llm_structured_columns=st;
  if(j.length)payload.llm_judge_columns=j;
  if(!payload.model_id||!payload.provider_api_key){alert('Model ID and API Key required');return}
  const fd=new FormData();
  fd.append('generate_request',JSON.stringify(payload));
  const sf=document.getElementById('seed').files[0];
  if(sf)fd.append('seed_data',sf);
  show('processing',`Submitting ${mode} job...`);
  try{
    const r=await fetch(`/synth-data-gen/data_generation/v1/${mode}`,{method:'POST',body:fd});
    if(!r.ok){show('failed','Submit failed: '+(await r.text()));return}
    const {job_id}=await r.json();
    show('processing',`Job ID: ${job_id} — polling...`);
    const t0=Date.now();
    while(true){
      await new Promise(r=>setTimeout(r,4000));
      const jr=await fetch(`/synth-data-gen/data_generation/v1/jobs/${job_id}`);
      const jd=await jr.json();
      const sec=Math.round((Date.now()-t0)/1000);
      if(jd.status==='completed'){
        const dl=mode==='create'?`<br/><a href="/synth-data-gen/data_generation/v1/download/${job_id}" style="color:var(--accent2);font-weight:600">⬇ Download CSV</a>`:'';
        show('completed',`✅ Done in ${sec}s — ${jd.result?.num_records||'?'} records${dl}`);return;
      }else if(jd.status==='failed'){show('failed','❌ '+jd.error);return;}
      else show('processing',`${jd.status.toUpperCase()} (${sec}s)...`);
    }
  }catch(e){show('failed','Error: '+e.message)}
}
function show(cls,msg){const b=document.getElementById('sbox');b.style.display='block';b.className=cls;b.innerHTML=msg}
</script></body></html>"""

@router.get("/home", response_class=HTMLResponse)
async def home_page():
    return HTMLResponse(HOME)

@router.get("/jobs/ui", response_class=HTMLResponse)
async def jobs_ui():
    jobs = await db.list_jobs(200)
    rows = ""
    if not jobs:
        rows = '<tr><td colspan="7" style="text-align:center;padding:2rem;color:var(--muted)">No jobs yet. <a href="/synth-data-gen/data_generation/v1/home" style="color:var(--accent2)">Submit one →</a></td></tr>'
    for j in jobs:
        st = j.get("status","?")
        sc = {"completed":"completed","failed":"failed","processing":"processing"}.get(st,"processing")
        cr = j.get("created_at")
        cs = cr.strftime("%Y-%m-%d %H:%M UTC") if cr else "—"
        jid = j.get("job_id","")
        csv = j.get("csv_filename") or ""
        dl = f'<a href="/synth-data-gen/data_generation/v1/download/{jid}" style="color:var(--accent2);font-weight:600">⬇ CSV</a>' if st=="completed" and csv else (f'<span style="color:var(--danger);font-size:.75rem" title="{j.get("error_message","")[:80]}">failed</span>' if st=="failed" else "—")
        rows += f"""<tr>
          <td><code>{jid[:20]}…</code></td>
          <td><span class="tag {sc}">{st}</span></td>
          <td>{j.get('job_type','—')}</td>
          <td>{j.get('model_provider','—')}</td>
          <td>{j.get('num_records','—')}</td>
          <td>{cs}</td>
          <td>{dl}</td></tr>"""
    total=len(jobs); comp=sum(1 for j in jobs if j.get('status')=='completed')
    fail=sum(1 for j in jobs if j.get('status')=='failed')
    running=sum(1 for j in jobs if j.get('status')=='processing')
    has_running = str(running > 0).lower()
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/><title>Jobs</title>
<style>
:root{{--bg:#0f1117;--card:#1a1d27;--border:#2a2d3e;--accent:#7c3aed;--accent2:#06b6d4;--text:#e2e8f0;--muted:#64748b;--success:#10b981;--danger:#ef4444;--warn:#f59e0b}}
*{{box-sizing:border-box;margin:0;padding:0}}body{{background:var(--bg);color:var(--text);font-family:system-ui,sans-serif}}
header{{background:var(--card);border-bottom:1px solid var(--border);padding:1rem 2rem;display:flex;align-items:center;justify-content:space-between}}
header h1{{font-size:1.2rem;font-weight:700;background:linear-gradient(135deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
header a{{color:var(--accent2);text-decoration:none;font-size:.85rem;border:1px solid var(--accent2);padding:.3rem .75rem;border-radius:.4rem}}
header a:hover{{background:var(--accent2);color:#000}}
main{{max-width:1100px;margin:2rem auto;padding:0 1.5rem}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1.5rem}}
.stat{{background:var(--card);border:1px solid var(--border);border-radius:.75rem;padding:1rem 1.25rem}}
.stat .n{{font-size:1.75rem;font-weight:700}}.stat .l{{font-size:.75rem;color:var(--muted);text-transform:uppercase}}
.green{{color:var(--success)}}.red{{color:var(--danger)}}.yellow{{color:var(--warn)}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:.75rem;overflow:hidden}}
table{{width:100%;border-collapse:collapse}}
th{{background:#12141e;padding:.7rem 1rem;text-align:left;font-size:.72rem;color:var(--muted);text-transform:uppercase;border-bottom:1px solid var(--border)}}
td{{padding:.7rem 1rem;border-bottom:1px solid var(--border);font-size:.84rem;vertical-align:middle}}
tr:last-child td{{border-bottom:none}}tr:hover td{{background:#1e2130}}
.tag{{display:inline-block;padding:.12rem .45rem;border-radius:.25rem;font-size:.68rem;font-weight:600;text-transform:uppercase}}
.tag.processing{{background:#1c1000;color:var(--warn)}}.tag.completed{{background:#001c10;color:var(--success)}}.tag.failed{{background:#1c0000;color:var(--danger)}}
code{{font-size:.73rem;color:var(--accent2)}}
.ref{{display:flex;justify-content:space-between;align-items:center;margin-bottom:.75rem}}
button.ref-btn{{background:var(--card);border:1px solid var(--border);color:var(--text);padding:.35rem .8rem;border-radius:.4rem;cursor:pointer;font-size:.82rem}}
button.ref-btn:hover{{border-color:var(--accent2);color:var(--accent2)}}
</style></head><body>
<header><h1>📋 Job History</h1><a href="/synth-data-gen/data_generation/v1/home">+ New Job</a></header>
<main>
<div class="stats">
  <div class="stat"><div class="n">{total}</div><div class="l">Total</div></div>
  <div class="stat"><div class="n green">{comp}</div><div class="l">Completed</div></div>
  <div class="stat"><div class="n red">{fail}</div><div class="l">Failed</div></div>
  <div class="stat"><div class="n yellow">{running}</div><div class="l">Running</div></div>
</div>
<div class="ref"><span style="color:var(--muted);font-size:.82rem">Last {total} jobs — newest first</span>
<button class="ref-btn" onclick="location.reload()">↻ Refresh</button></div>
<div class="card"><table>
<thead><tr><th>Job ID</th><th>Status</th><th>Type</th><th>Provider</th><th>Records</th><th>Created</th><th>Download</th></tr></thead>
<tbody>{rows}</tbody>
</table></div>
</main>
<script>if({has_running})setTimeout(()=>location.reload(),15000)</script>
</body></html>""")
