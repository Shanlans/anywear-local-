"""Offline fake CLI processes only. No upstream model or account calls."""
import json
from pathlib import Path
import sys
import time
import pytest

from lab import model as transport

class FixtureGuard:
    def __init__(self,prompt,schema,model):
        self.url='http://127.0.0.1/never-contacted-fixture';self.nonce='fixture-only'
        self.evidence={'requests':1,'actual_model':model,'http_status':200,'tools_forwarded':0,'input_messages_forwarded':1}
    def __enter__(self):return self
    def __exit__(self,*args):pass

@pytest.fixture(autouse=True)
def no_network(monkeypatch):monkeypatch.setattr(transport,'RequestGuard',FixtureGuard)

def fake_command(monkeypatch,script):
    def command(folder,schema,answer,*args):return [sys.executable,'-u','-c',script,str(answer)]
    monkeypatch.setattr(transport,'cli_command',command)

def test_partial_stdout_cannot_block_timeout(monkeypatch):
    fake_command(monkeypatch,'import sys,time;sys.stdout.write("{");sys.stdout.flush();time.sleep(3)')
    started=time.monotonic();model=transport.CodexModel(timeout=.25)
    with pytest.raises(transport.ModelFailure) as error:model.sample_text('offline fixture')
    assert error.value.code=='TIMEOUT_UNKNOWN' and error.value.unknown
    assert time.monotonic()-started<1.5

def test_child_not_reading_large_stdin_cannot_block_timeout(monkeypatch):
    fake_command(monkeypatch,'import time;time.sleep(3)')
    started=time.monotonic();model=transport.CodexModel(timeout=.25)
    with pytest.raises(transport.ModelFailure) as error:model.sample_text('x'*2_000_000)
    assert error.value.code=='TIMEOUT_UNKNOWN' and error.value.unknown
    assert time.monotonic()-started<1.5

def test_fragmented_utf8_and_last_line_without_newline(monkeypatch):
    decision={'action':'leave','sku':'','reason_code':'budget','reason_zh':'预算不足。','reason_en':'Budget insufficient.'}
    script='''import sys,json,time
from pathlib import Path
sys.stdin.buffer.read()
answer='''+repr(decision)+'''
Path(sys.argv[1]).write_text(json.dumps(answer,ensure_ascii=False))
events=[{'type':'thread.started','thread_id':'offline-fixture-session'}, {'type':'item.completed','item':{'type':'agent_message','text':'中文分片'}}, {'type':'turn.completed','usage':{'input_tokens':42,'output_tokens':8}}]
payload='\\n'.join(json.dumps(e,ensure_ascii=False) for e in events).encode()
for byte in payload:
 sys.stdout.buffer.write(bytes([byte]));sys.stdout.buffer.flush()
'''
    fake_command(monkeypatch,script);model=transport.CodexModel(timeout=3)
    assert json.loads(model.sample_text('offline fixture'))==decision
    assert model.metadata['session_id']=='offline-fixture-session'
    assert model.metadata['cli_usage']=={'input_tokens':42,'output_tokens':8}
    assert model.metadata['tool_event'] is False
    assert 'text' not in model.metadata

def test_unterminated_output_has_memory_bound(monkeypatch):
    fake_command(monkeypatch,'import sys,time;sys.stdout.buffer.write(b"x"*1_100_000);sys.stdout.flush();time.sleep(3)')
    model=transport.CodexModel(timeout=3)
    with pytest.raises(transport.ModelFailure) as error:model.sample_text('offline fixture')
    assert error.value.code=='CLI_OUTPUT_LIMIT_UNKNOWN' and error.value.unknown

@pytest.mark.parametrize('observed_model',[None,'unexpected-fixture-model'])
def test_missing_or_mismatched_model_identity_rejects_action(monkeypatch,observed_model):
    class IdentityGuard(FixtureGuard):
        def __init__(self,*args):
            super().__init__(*args);self.evidence['actual_model']=observed_model
    monkeypatch.setattr(transport,'RequestGuard',IdentityGuard)
    decision={'action':'leave','sku':'','reason_code':'budget','reason_zh':'预算不足。','reason_en':'Budget insufficient.'}
    fake_command(monkeypatch,'import sys,json;from pathlib import Path;sys.stdin.buffer.read();Path(sys.argv[1]).write_text(json.dumps('+repr(decision)+'))')
    model=transport.CodexModel(timeout=3)
    with pytest.raises(transport.ModelFailure) as error:model.sample_text('offline fixture')
    assert error.value.code=='MODEL_MISMATCH'
    assert model.metadata['actual_model']==observed_model
