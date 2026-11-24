from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import pandas as pd, sqlite3, os, json
from dotenv import load_dotenv
from openai import OpenAI
from openai import APIStatusError, APIConnectionError, APITimeoutError


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'rideops_support_tickets.csv'
DB = ROOT / 'data' / 'rideops.db'

load_dotenv(ROOT / '.env')

app = FastAPI(title='RideOps Intelligence API', version='1.0.0')

# CORS configuration for local development and Vercel deployment
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://ride-ops-intelligence.vercel.app",
]

# FRONTEND_URL may hold one URL or several comma-separated URLs
for _u in os.getenv("FRONTEND_URL", "").split(","):
    _u = _u.strip().rstrip("/")
    if _u and _u not in allowed_origins:
        allowed_origins.append(_u)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # Lets Vercel preview deployments of this project call the API too
    allow_origin_regex=r"https://ride-ops-intelligence-[a-z0-9-]+\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TIME_COLS=['created_at','first_response_at','first_closed_at','final_closed_at']
def load_data():
    df=pd.read_csv(DATA)
    for c in TIME_COLS: df[c]=pd.to_datetime(df[c], errors='coerce')
    for c in ['eng_handoffs','reopen_count','csat_score']: df[c]=pd.to_numeric(df[c],errors='coerce')
    df['is_escalated']=df['escalated_to_eng'].astype(str).str.lower().eq('yes')
    df['is_open']=df['status'].astype(str).str.lower().str.startswith('open')
    df['reopened']=df['reopen_count'].fillna(0).gt(0)
    df['first_response_hours']=(df.first_response_at-df.created_at).dt.total_seconds()/3600
    df['final_resolution_hours']=(df.final_closed_at-df.created_at).dt.total_seconds()/3600
    df['month']=df.created_at.dt.strftime('%b %Y')
    df['created_date']=df.created_at.dt.strftime('%Y-%m-%d')
    df['open_age_hours']=((pd.Timestamp('2026-09-30 23:59:59')-df.created_at).dt.total_seconds()/3600).where(df.is_open)
    return df

def db_conn(): return sqlite3.connect(DB)

def init_db():
    df=load_data(); db= db_conn()
    out=df.copy()
    for c in TIME_COLS: out[c]=out[c].dt.strftime('%Y-%m-%d %H:%M:%S')
    out.to_sql('tickets',db,if_exists='replace',index=False)
    db.execute('CREATE INDEX IF NOT EXISTS idx_ticket_category ON tickets(category)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_ticket_status ON tickets(status)')
    db.execute('CREATE TABLE IF NOT EXISTS llm_cache (cache_key TEXT PRIMARY KEY, response_json TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    db.commit(); db.close()

@app.on_event('startup')
def startup(): init_db()

def groq_client():
    key=os.getenv('GROQ_API_KEY','').strip()
    if not key or key in {'your_groq_api_key_here','gsk_your_key_here'}:
        return None
    return OpenAI(api_key=key, base_url=os.getenv('GROQ_BASE_URL','https://api.groq.com/openai/v1'), max_retries=0, timeout=35.0)


def loud_llm_error(kind, detail, status=None):
    line='='*88
    print('\n'+line, flush=True)
    print('🚨🚨🚨 RIDEOPS GROQ LLM FAILURE 🚨🚨🚨', flush=True)
    print(f'FAILURE TYPE: {kind}', flush=True)
    if status is not None: print(f'HTTP STATUS: {status}', flush=True)
    print(f'DETAIL: {detail}', flush=True)
    if kind == 'CREDIT_OR_BILLING_EXHAUSTED':
        print('ACTION: Check Groq Console billing/credits/usage limits. Do NOT keep retrying.', flush=True)
    elif kind == 'RATE_LIMIT_OR_QUOTA':
        print('ACTION: Check Groq model RPM/TPM/TPD limits and retry window. This may be a rate cap, not a billing failure.', flush=True)
    else:
        print('ACTION: Check API key, model ID, network, and Groq service status.', flush=True)
    print(line+'\n', flush=True)


@app.get('/api/health')
def health():
    key=os.getenv('GROQ_API_KEY','').strip()
    configured=bool(key and key not in {'your_groq_api_key_here','gsk_your_key_here'})
    return {'status':'ok','database':str(DB.name),'llm_configured':configured,'llm_provider':'groq','llm_model':os.getenv('GROQ_MODEL','openai/gpt-oss-20b'),'llm_mode':'groq' if configured else 'rules-based-demo'}


@app.post('/api/llm-test')
def llm_test():
    """One explicit, tiny live request. Not run automatically on startup."""
    client=groq_client()
    if client is None:
        loud_llm_error('MISSING_API_KEY','GROQ_API_KEY is empty or still a placeholder.')
        raise HTTPException(400,'GROQ_API_KEY is not configured. Add it to backend .env and restart the backend.')
    model=os.getenv('GROQ_MODEL','openai/gpt-oss-20b').strip()
    try:
        response=client.chat.completions.create(
            model=model,
            messages=[{'role':'user','content':'Reply with exactly: GROQ CONNECTION OK'}],
            max_tokens=12
        )
        usage=getattr(response,'usage',None)
        print(f'[RideOps][Groq] CONNECTION OK | model={model} | prompt_tokens={getattr(usage,"prompt_tokens",None)} | completion_tokens={getattr(usage,"completion_tokens",None)}',flush=True)
        return {'ok':True,'provider':'Groq','model':model,'reply':response.choices[0].message.content,'usage':usage.model_dump() if usage else None}
    except APIStatusError as e:
        body=str(getattr(e,'body',None) or e.message or str(e))[:900]
        lower=body.lower()
        if any(x in lower for x in ['credit_balance','insufficient_quota','billing','payment required','credits exhausted','account balance']): kind='CREDIT_OR_BILLING_EXHAUSTED'
        elif e.status_code==429: kind='RATE_LIMIT_OR_QUOTA'
        else: kind='API_ERROR'
        loud_llm_error(kind,body,e.status_code)
        raise HTTPException(502,f'Groq connection test failed ({kind}, HTTP {e.status_code}). See loud backend terminal log.')
    except (APIConnectionError,APITimeoutError) as e:
        loud_llm_error('CONNECTION_OR_TIMEOUT',str(e))
        raise HTTPException(502,'Could not connect to Groq. See backend terminal log.')
    except Exception as e:
        loud_llm_error(type(e).__name__,str(e)[:900])
        raise HTTPException(502,f'Groq test failed: {type(e).__name__}. See backend terminal log.')

@app.get('/api/overview')
def overview():
    d=load_data(); n=len(d); esc=int(d.is_escalated.sum()); opened=d[d.is_open]
    focus=d[d.category.isin(['Roster / booking not syncing','Live tracking / GPS incorrect'])]
    eng=d[d.is_escalated]; ret=eng.eng_outcome.astype(str).str.lower().str.contains('insufficient info|config issue',regex=True).sum()
    return {'total':n,'escalated':esc,'escalation_rate':round(esc/n*100,1),'open':len(opened),'open_l1':int((opened.status=='Open - with L1').sum()),'open_eng':int((opened.status=='Open - with Engineering').sum()),'reopened':int(d.reopened.sum()),'csat':round(d.csat_score.mean(),2),'csat_n':int(d.csat_score.notna().sum()),'csat_coverage':round(d.csat_score.notna().mean()*100,1),'focus_tickets':len(focus),'focus_open':int(focus.is_open.sum()),'engineering_returns':int(ret),'engineering_total':len(eng),'engineering_return_rate':round(ret/len(eng)*100,1),'multi_handoff':int(eng.eng_handoffs.fillna(0).ge(2).sum()),'multi_handoff_rate':round(eng.eng_handoffs.fillna(0).ge(2).mean()*100,1),'date_start':d.created_at.min().strftime('%d %b %Y'),'date_end':d.created_at.max().strftime('%d %b %Y')}

@app.get('/api/trends')
def trends():
    d=load_data(); g=d.groupby('month',sort=False).agg(tickets=('ticket_id','size'),response=('first_response_hours','median'),escalated=('is_escalated','sum')).reset_index()
    return g.where(pd.notnull(g),None).to_dict('records')

@app.get('/api/categories')
def categories():
    d=load_data(); g=d.groupby('category').agg(tickets=('ticket_id','size'),escalated=('is_escalated','sum'),open=('is_open','sum'),reopened=('reopened','sum'),resolution=('final_resolution_hours','median'),csat=('csat_score','mean'),csat_n=('csat_score','count')).reset_index()
    g['escalation_rate']=(g.escalated/g.tickets*100).round(1); g['reopen_rate']=(g.reopened/g.tickets*100).round(1); g['csat']=g.csat.round(2)
    return g.sort_values('tickets',ascending=False).where(pd.notnull(g),None).to_dict('records')

@app.get('/api/tickets')
def tickets(q:str='',category:str='',status:str='',priority:str='',limit:int=100):
    d=load_data()
    if q:
        mask=d.astype(str).apply(lambda col: col.str.contains(q,case=False,na=False)).any(axis=1); d=d[mask]
    if category: d=d[d.category==category]
    if status: d=d[d.status==status]
    if priority: d=d[d.priority==priority]
    cols=['ticket_id','created_at','category','priority','description','client_name','assigned_agent','status','escalated_to_eng','eng_outcome','eng_handoffs','reopen_count','csat_score']
    d=d.sort_values('created_at',ascending=False).head(max(1,min(limit,500)))
    d=d[cols].copy(); d['created_at']=d.created_at.dt.strftime('%d %b %Y %H:%M')
    return d.astype(object).where(pd.notnull(d),None).to_dict('records')

@app.get('/api/tickets/{ticket_id}')
def ticket(ticket_id:str):
    d=load_data(); r=d[d.ticket_id==ticket_id]
    if r.empty: raise HTTPException(404,'Ticket not found')
    x=r.iloc[0].to_dict()
    for k,v in list(x.items()):
        if pd.isna(v): x[k]=None
        elif isinstance(v,pd.Timestamp): x[k]=v.strftime('%Y-%m-%d %H:%M')
        elif hasattr(v,'item'): x[k]=v.item()
    return x

PLAYBOOKS={
'Roster / booking not syncing':{'title':'Roster & booking sync','purpose':'Check the sync path and collect evidence before escalating.','checks':['Confirm affected client, roster date, shift and employee/booking identifiers.','Check whether the roster upload/import completed and note its timestamp.','Compare source roster values with the values visible in RideOps.','Check for duplicate employee IDs, missing mandatory fields or invalid shift mappings.','Confirm whether the issue affects one employee, one shift, one client or multiple clients.','Capture a redacted screenshot, sample record IDs and exact error text.'],'evidence':['Client + roster date','Affected employee/booking IDs','Upload/import timestamp and result','Expected vs actual values','Scope of impact','Screenshot or exact error']},
'Live tracking / GPS incorrect':{'title':'GPS & live tracking','purpose':'Separate device/connectivity symptoms from mapping or trip-state issues.','checks':['Confirm trip ID, vehicle/driver ID and the time the location stopped updating.','Check whether the trip is active and the driver app/device is online.','Compare last GPS update time with the time reported by the client.','Check whether the issue affects one vehicle, one route or multiple trips.','Record whether the marker is frozen, missing, delayed or at an incorrect location.','Capture a redacted map screenshot, trip ID and relevant timestamps.'],'evidence':['Trip ID + vehicle/driver ID','Last location update timestamp','Trip state','Symptom type: frozen/missing/delayed/wrong','Scope across trips','Screenshot or exact error']}}

@app.get('/api/playbooks')
def playbooks(): return PLAYBOOKS

class AnalyzeRequest(BaseModel):
    ticket_id:str

@app.post('/api/analyze')
def analyze(req:AnalyzeRequest):
    d=load_data(); r=d[d.ticket_id==req.ticket_id]
    if r.empty: raise HTTPException(404,'Ticket not found')
    t=r.iloc[0]; category=t.category; pb=PLAYBOOKS.get(category)
    summary=f"{t.priority} ticket for {t.client_name}: {t.description}. Current status: {t.status}."
    diagnosis='Clarify impact, reproduce the issue and collect exact timestamps, identifiers and error evidence before routing.'
    if category=='Roster / booking not syncing': diagnosis='Establish the affected roster date, source-vs-platform mismatch and import result before deciding whether this is a configuration/data issue or a product defect.'
    elif category=='Live tracking / GPS incorrect': diagnosis='Establish trip state, last location update and whether the symptom is isolated or widespread before escalating.'
    next_steps=(pb['checks'][:4] if pb else ['Confirm impact and scope.','Collect relevant IDs and timestamps.','Reproduce the issue and capture exact error text.','Document checks already performed before escalation.'])
    missing=(pb['evidence'] if pb else ['Relevant IDs','Timestamps','Expected vs actual behaviour','Exact error','Reproduction steps'])

    api_key=os.getenv('GROQ_API_KEY','').strip()
    client=groq_client()
    if client is not None:
        model=os.getenv('GROQ_MODEL','openai/gpt-oss-20b').strip()
        # Cache by ticket + model + prompt version. Reopening/re-running the same analysis costs zero tokens.
        cache_key=f'{req.ticket_id}|{model}|prompt-v1'
        db=db_conn(); cached=db.execute('SELECT response_json FROM llm_cache WHERE cache_key=?',(cache_key,)).fetchone(); db.close()
        if cached:
            result=json.loads(cached[0])
            return {**result,'cached':True,'usage_note':'Served from local SQLite cache; no Groq request was made.'}
        ticket_context={
            'ticket_id':str(t.ticket_id),'description':str(t.description)[:700],'category':str(t.category),
            'priority':str(t.priority),'client':str(t.client_name),'status':str(t.status),
            'handoffs':int(t.eng_handoffs) if pd.notna(t.eng_handoffs) else 0,
            'reopens':int(t.reopen_count) if pd.notna(t.reopen_count) else 0
        }
        playbook_context=pb or {'title':'General support investigation','checks':next_steps,'evidence':missing}
        system_prompt=("You are RideOps L1 support copilot. Use only supplied facts. Do not invent tests, logs, timestamps, root causes or completed checks. "
            "Treat category as a label, not proof. Distinguish facts from hypotheses. Give at most 4 concise checks and at most 4 missing evidence items. "
            "The playbook is proposed demo guidance, not a verified RideOps procedure. Return compact JSON with keys: summary, diagnosis, next_steps, missing_information, escalation_guidance.")
        user_prompt='Ticket: '+json.dumps(ticket_context,separators=(',',':'))+'\nChecklist: '+json.dumps({'checks':playbook_context.get('checks',[])[:6],'evidence':playbook_context.get('evidence',[])[:6]},separators=(',',':'))
        try:
            # Chat Completions is Groq's documented OpenAI-compatible endpoint.
            response=client.chat.completions.create(
                model=model,
                messages=[{'role':'system','content':system_prompt},{'role':'user','content':user_prompt}],
                max_tokens=420, response_format={'type':'json_object'}
            )
            content=response.choices[0].message.content or '{}'
            result=json.loads(content)
            # Clamp output lengths so malformed/verbose model output cannot bloat UI or cache.
            result['next_steps']=[str(x)[:240] for x in result.get('next_steps',[])[:4]]
            result['missing_information']=[str(x)[:180] for x in result.get('missing_information',[])[:4]]
            result.setdefault('summary',summary); result.setdefault('diagnosis',diagnosis); result.setdefault('escalation_guidance','Complete the listed checks and collect missing evidence before escalation.')
            payload={'mode':'groq-llm','model':model,'summary':str(result['summary'])[:500],'classification':category,'priority':t.priority,
                'diagnosis':str(result['diagnosis'])[:700],'next_steps':result['next_steps'],'missing_information':result['missing_information'],
                'escalation_guidance':str(result['escalation_guidance'])[:500],'playbook_available':bool(pb),
                'guardrail':'Groq-generated decision support, not a verified root-cause finding. Verify every check and observation before acting.'}
            db=db_conn(); db.execute('INSERT OR REPLACE INTO llm_cache(cache_key,response_json) VALUES (?,?)',(cache_key,json.dumps(payload))); db.commit(); db.close()
            usage=getattr(response,'usage',None)
            print(f'[RideOps][Groq] ANALYSIS OK | ticket={req.ticket_id} | model={model} | prompt_tokens={getattr(usage,"prompt_tokens",None)} | completion_tokens={getattr(usage,"completion_tokens",None)} | cached=NO',flush=True)
            return {**payload,'cached':False,'usage':usage.model_dump() if usage else None}
        except APIStatusError as e:
            body=str(getattr(e,'body',None) or e.message or str(e))[:900]; lower=body.lower()
            if any(x in lower for x in ['credit_balance','insufficient_quota','billing','payment required','credits exhausted','account balance']): kind='CREDIT_OR_BILLING_EXHAUSTED'
            elif e.status_code==429: kind='RATE_LIMIT_OR_QUOTA'
            else: kind='API_ERROR'
            loud_llm_error(kind,body,e.status_code)
            raise HTTPException(502,f'Groq analysis failed: {kind} (HTTP {e.status_code}). See backend terminal log. No rules-based result was substituted.')
        except (APIConnectionError,APITimeoutError) as e:
            loud_llm_error('CONNECTION_OR_TIMEOUT',str(e))
            raise HTTPException(502,'Groq connection failed. See backend terminal log. No rules-based result was substituted.')
        except Exception as e:
            loud_llm_error(type(e).__name__,str(e)[:900])
            raise HTTPException(502,f'Groq analysis failed: {type(e).__name__}. See backend terminal log.')

    return {'mode':'rules-based-demo','summary':summary,'classification':category,'priority':t.priority,'diagnosis':diagnosis,'next_steps':next_steps,'missing_information':missing,'escalation_guidance':'Complete the relevant checks and collect the listed evidence before escalating.','playbook_available':bool(pb),'guardrail':'Rules-based demo output, not an LLM response or verified root-cause finding. Add GROQ_API_KEY to enable Groq.'}

class HandoffRequest(BaseModel):
    ticket_id:str
    completed_checks:list[str]=[]
    notes:str=''
@app.post('/api/handoff')
def handoff(req:HandoffRequest):
    d=load_data(); r=d[d.ticket_id==req.ticket_id]
    if r.empty: raise HTTPException(404,'Ticket not found')
    t=r.iloc[0]; pb=PLAYBOOKS.get(t.category,{})
    body=f"""# Engineering handoff — {t.ticket_id}\n\n## Summary\n{t.description}\n\n## Context\n- Client: {t.client_name} ({t.client_tier})\n- Category / priority: {t.category} / {t.priority}\n- Created: {t.created_at}\n- Current status: {t.status}\n- Previous Engineering handoffs: {int(t.eng_handoffs) if pd.notna(t.eng_handoffs) else 0}\n- Reopened: {int(t.reopen_count) if pd.notna(t.reopen_count) else 0} time(s)\n\n## Checks completed\n""" + ('\n'.join('- [x] '+x for x in req.completed_checks) if req.completed_checks else '- No checks marked complete yet') + f"""\n\n## Agent notes\n{req.notes or 'No additional notes supplied.'}\n\n## Evidence still required\n""" + ('\n'.join('- '+x for x in pb.get('evidence',[])) if pb else '- Relevant IDs, timestamps, expected vs actual behaviour, exact error and reproduction steps') + "\n\n## Engineering ask\nPlease investigate the reproducible behaviour, confirm root cause, and return the fix/mitigation or the additional evidence required.\n\n> Draft generated from ticket metadata and agent inputs. Verify all facts and remove sensitive data before sharing."
    return {'markdown':body}