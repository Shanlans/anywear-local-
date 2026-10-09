"""Codex transport with an enforced, single-consumer, tool-free request gateway.

No credentials or raw request/response streams are persisted. Authentication is
supplied by the CLI's existing login. The gateway has one fixed upstream host.
"""
from __future__ import annotations
import json
import os
import selectors
import secrets
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import httpx
from concordia.language_model import language_model as lm
from .common import Decision, canonical, digest

SYSTEM = ('You simulate ONE synthetic shopper. The supplied JSON is your entire private context. '
          'Never invent observations, payment success or other people\'s private state. '
          'Choose only a listed action and SKU. Balance your own preference, budget, time and privacy; '
          'you are not rewarded for spending. Anywear may help, harm or do nothing. '
          'Return the schema with a brief stated reason in Chinese and English, not hidden reasoning. '
          'Ordinary mirrors do not show clothes you have not put on. '
          'Previously failed three trials are given history, not remaining catalogue items.')
DISABLED = ('shell_tool','unified_exec','apps','plugins','remote_plugin','multi_agent',
            'browser_use','browser_use_external','computer_use','in_app_browser','view_image',
            'image_generation','memories','hooks','shell_snapshot','goals','sleep_tool',
            'workspace_dependencies','unbounded_connection_retries','code_mode_host')
CAPABILITIES = {'provider':'Codex CLI with fixed-upstream isolation gateway',
    'tools_forwarded':0, 'history':'exactly one supplied consumer prompt',
    'sample_choice':False,'temperature':False,'top_p':False,'top_k':False,
    'max_tokens':False,'llm_seed':False,'monetary_cost':'unknown', 'version':1}

class ModelFailure(Exception):
    def __init__(self, code, unknown=False, usage=None):
        self.code, self.unknown, self.usage = code, unknown, usage
        super().__init__(code)

def guarded_body(body, prompt, schema, model):
    # Do not forward CLI-injected project/global instructions, histories or tools.
    clean = {k:body[k] for k in ('reasoning','text') if k in body}
    clean.update(model=model, instructions=SYSTEM,
        input=[{'role':'user','content':[{'type':'input_text','text':prompt}]}],
        tools=[], tool_choice='none', parallel_tool_calls=False, store=False, stream=True)
    clean['text'] = {'format':{'type':'json_schema','name':'anywear_decision',
                             'strict':True,'schema':schema}}
    if clean.get('reasoning'):
        clean['reasoning'].pop('summary', None)
    return clean

class RequestGuard:
    def __init__(self, prompt, schema, model):
        self.prompt, self.schema, self.model = prompt, schema, model
        self.nonce=secrets.token_hex(24)
        self.evidence = {'version':1,'requests':0,'tools_forwarded':0,
                         'private_prompt_hash':digest(prompt),'input_messages_forwarded':1,
                         'upstream':'https://chatgpt.com/backend-api/codex/responses',
                         'actual_model':None, 'usage':None, 'http_status':None}
        owner = self
        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
            def log_message(self, *args): pass
            def do_GET(self):
                self.send_error(404)
            def do_POST(self):
                if (self.path != '/responses' or self.client_address[0] != '127.0.0.1'
                    or not secrets.compare_digest(self.headers.get('x-anywear-guard',''),owner.nonce)):
                    self.send_error(403); return
                try:
                    length = int(self.headers.get('Content-Length','0'))
                    if not 0 < length < 8_000_000:
                        self.send_error(413); return
                    body = json.loads(self.rfile.read(length))
                    safe = guarded_body(body, owner.prompt, owner.schema, owner.model)
                    headers = {k:v for k,v in self.headers.items() if k.lower() in
                        {'authorization','chatgpt-account-id','openai-beta','user-agent','originator'}}
                    headers.update({'content-type':'application/json','accept':'text/event-stream'})
                    owner.evidence['requests'] += 1
                    if owner.evidence['requests']>1:
                        self.send_error(409,'One upstream request per attempt'); return
                    with httpx.Client(timeout=httpx.Timeout(180,connect=20),trust_env=True) as client:
                        with client.stream('POST',owner.evidence['upstream'],headers=headers,json=safe) as response:
                            owner.evidence['http_status'] = response.status_code
                            self.send_response(response.status_code)
                            self.send_header('Content-Type',response.headers.get('content-type','text/event-stream'))
                            self.send_header('Connection','close'); self.end_headers()
                            # Inspect safe metadata only; never save reasoning or auth.
                            for line in response.iter_lines():
                                if line.startswith('data: '):
                                    try:
                                        event=json.loads(line[6:]); data=event.get('response',{})
                                        if data.get('model'): owner.evidence['actual_model']=data['model']
                                        if data.get('usage'):
                                            u=data['usage']
                                            owner.evidence['usage']={k:u[k] for k in
                                                ('input_tokens','output_tokens','total_tokens','input_tokens_details','output_tokens_details') if k in u}
                                    except (ValueError,AttributeError): pass
                                self.wfile.write((line+'\n').encode()); self.wfile.flush()
                except (BrokenPipeError,ConnectionResetError): pass
                except Exception:
                    owner.evidence['transport_error']='GATEWAY_TRANSPORT'
                    try: self.send_error(502,'Upstream transport failed')
                    except Exception: pass
                self.close_connection=True
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.daemon_threads=True
    def __enter__(self):
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        return self
    def __exit__(self,*args):
        self.server.shutdown(); self.server.server_close()

def cli_command(cwd, schema_path, answer_path, guard_url, model,nonce):
    executable=os.environ.get('ANYWEAR_CODEX') or shutil.which('codex')
    if not executable: raise ModelFailure('CODEX_NOT_FOUND')
    cmd=[executable,'--ask-for-approval','never']
    for flag in DISABLED: cmd += ['--disable',flag]
    cmd += ['exec','--ephemeral','--ignore-user-config','--skip-git-repo-check',
        '--sandbox','read-only','--color','never','--json','--model',model,
        '--cd',str(cwd),'--output-schema',str(schema_path),'--output-last-message',str(answer_path)]
    settings={'model_provider':'anywear_guard',
        'model_providers.anywear_guard.name':'Anywear isolation gateway',
        'model_providers.anywear_guard.base_url':guard_url,
        'model_providers.anywear_guard.requires_openai_auth':True,
        'model_providers.anywear_guard.wire_api':'responses',
        'model_providers.anywear_guard.supports_websockets':False,
        'model_providers.anywear_guard.request_max_retries':0,
        'model_providers.anywear_guard.stream_max_retries':0,
        'model_providers.anywear_guard.http_headers.x-anywear-guard':nonce,
        'web_search':'disabled','project_doc_max_bytes':0,'agents.enabled':False,
        'tools.view_image':False,'model_reasoning_summary':'none',
        'apps._default.enabled':False,'analytics.enabled':False}
    for key,value in settings.items(): cmd += ['-c',key+'='+json.dumps(value)]
    return cmd+['-']

def kill_group(proc):
    if proc.poll() is None:
        try: os.killpg(proc.pid,signal.SIGTERM)
        except ProcessLookupError: return
        try: proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try: os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError: pass

class CodexModel(lm.LanguageModel):
    def __init__(self, model='gpt-6.1-sol', timeout=180, cancel=None,on_spawn=None):
        self.model,self.timeout,self.cancel=model,timeout,cancel
        self.on_spawn=on_spawn
        self.metadata={}
    def sample_choice(self,*args,**kwargs):
        raise NotImplementedError('sample_choice is unsupported by the Codex adapter')
    def sample_text(self,prompt,*,max_tokens=5000,terminators=(),temperature=1.0,
                    top_p=.95,top_k=64,timeout=60,seed=None):
        if (max_tokens,tuple(terminators),temperature,top_p,top_k,seed)!=(5000,(),1.0,.95,64,None):
            raise ValueError('Unsupported sampling parameter; defaults are not token limits')
        schema=Decision.model_json_schema()
        # Strict Responses schema requires all properties; no defaults in Decision.
        with tempfile.TemporaryDirectory(prefix='anywear-consumer-') as tmp:
            folder=Path(tmp); schema_path=folder/'schema.json'; answer=folder/'answer.json'
            schema_path.write_text(canonical(schema),encoding='utf-8')
            with RequestGuard(prompt,schema,self.model) as guard:
                cmd=cli_command(folder,schema_path,answer,guard.url,self.model,guard.nonce)
                proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,bufsize=0,start_new_session=True)
                started=time.monotonic()
                if self.on_spawn:
                    try: self.on_spawn(proc.pid)
                    except Exception:
                        kill_group(proc); raise ModelFailure('SPAWN_RECORD_FAILED',True)
                selector=selectors.DefaultSelector()
                os.set_blocking(proc.stdout.fileno(),False)
                os.set_blocking(proc.stdin.fileno(),False)
                selector.register(proc.stdout,selectors.EVENT_READ)
                pending_input=prompt.encode('utf-8'); input_offset=0; pending_output=b''; output_closed=False
                if pending_input: selector.register(proc.stdin,selectors.EVENT_WRITE)
                else: proc.stdin.close()
                usage=None; session_id=None; tool=False; item_types=set()
                def consume(line):
                    nonlocal usage,session_id,tool
                    try: event=json.loads(line.decode('utf-8',errors='replace'))
                    except ValueError: return
                    if event.get('type')=='thread.started': session_id=event.get('thread_id')
                    if event.get('type')=='turn.completed': usage=event.get('usage')
                    item=event.get('item',{})
                    if item.get('type'): item_types.add(item['type'])
                    if item.get('type') not in (None,'agent_message','reasoning','error'): tool=True
                    # Reasoning, tool bodies and error strings are discarded.
                try:
                    while True:
                        if time.monotonic()-started>self.timeout or (self.cancel and self.cancel()):
                            kill_group(proc); raise ModelFailure('TIMEOUT_UNKNOWN',True,usage)
                        for key,_ in selector.select(.2):
                            if key.fileobj is proc.stdin:
                                try: written=os.write(proc.stdin.fileno(),pending_input[input_offset:input_offset+65536])
                                except BrokenPipeError: written=0
                                input_offset+=written
                                if not written or input_offset==len(pending_input):
                                    selector.unregister(proc.stdin); proc.stdin.close()
                            else:
                                chunk=os.read(proc.stdout.fileno(),65536)
                                if not chunk:
                                    output_closed=True; selector.unregister(proc.stdout)
                                    if pending_output: consume(pending_output); pending_output=b''
                                else:
                                    pending_output+=chunk
                                    if len(pending_output)>1_048_576:
                                        raise ModelFailure('CLI_OUTPUT_LIMIT_UNKNOWN',True,usage)
                                    while b'\n' in pending_output:
                                        line,pending_output=pending_output.split(b'\n',1); consume(line)
                        if output_closed and proc.poll() is not None: break
                    proc.wait(timeout=3)
                    self.metadata={**guard.evidence,'session_id':session_id,'cli_usage':usage,
                        'wall_seconds':round(time.monotonic()-started,3),'tool_event':tool,
                        'item_types':sorted(item_types)}
                    if tool: raise ModelFailure('UNEXPECTED_TOOL',False,usage)
                    status=guard.evidence.get('http_status')
                    if status in (401,403,429): raise ModelFailure(f'PROVIDER_{status}',False,usage)
                    if not guard.evidence['requests']:
                        raise ModelFailure('NO_GUARDED_REQUEST',False,usage)
                    if proc.returncode or not answer.exists():
                        raise ModelFailure('CLI_FAILED',True,usage)
                    response=Decision.model_validate_json(answer.read_text(encoding='utf-8'))
                    if guard.evidence.get('actual_model')!=self.model:
                        raise ModelFailure('MODEL_MISMATCH',False,usage)
                    return response.model_dump_json()
                finally:
                    if not self.metadata:
                        self.metadata={**guard.evidence,'session_id':session_id,'cli_usage':usage,
                            'wall_seconds':round(time.monotonic()-started,3),'tool_event':tool,
                            'item_types':sorted(item_types)}
                    kill_group(proc); selector.close(); proc.stdout.close()
                    if not proc.stdin.closed: proc.stdin.close()
