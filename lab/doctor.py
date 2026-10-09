import os
import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path
from .common import ROOT,DATA,digest
from .model import CodexModel,CAPABILITIES,guarded_body

def fingerprint():
    executable=os.environ.get('ANYWEAR_CODEX') or shutil.which('codex') or ''
    try: version=subprocess.check_output([executable,'--version'],text=True).strip()
    except Exception: version='unavailable'
    return {'adapter_hash':digest((ROOT/'lab/model.py').read_text()),
            'components_hash':digest((ROOT/'lab/agents.py').read_text()),'cli_version':version,
            'gateway_version':1}

def gate_valid():
    path=DATA/'isolation-gate.json'
    if not path.exists(): return False
    gate=json.loads(path.read_text())
    return gate.get('passed') is True and gate.get('fingerprint')==fingerprint()

def probe():
    model=CodexModel()
    answer=model.sample_text('Synthetic isolation acceptance probe. Only allowed action: leave; sku empty; '
        'reason_code no_options. Private canary is THIS_SHOPPER_ONLY; no other shopper data. Brief Chinese/English reason.')
    meta=model.metadata
    if meta['tools_forwarded']!=0 or meta['input_messages_forwarded']!=1 or not meta['requests'] or meta['tool_event']:
        raise RuntimeError('ISOLATION_PROBE_FAILED')
    evidence={'passed':True,'observed_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'decision':json.loads(answer),'capabilities':CAPABILITIES,'fingerprint':fingerprint(),'metadata':meta}
    DATA.mkdir(parents=True,exist_ok=True)
    (DATA/'isolation-gate.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    return evidence

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--probe',action='store_true'); args=parser.parse_args()
    print(json.dumps(probe() if args.probe else {'fingerprint':fingerprint(),'gate_valid':gate_valid(),
        'python':shutil.which('python'),'capabilities':CAPABILITIES},ensure_ascii=False,indent=2))
