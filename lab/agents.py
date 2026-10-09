"""Real Concordia entities with explicit, rebuildable private components."""
import json
import numpy as np
from concordia.agents.entity_agent import EntityAgent
from concordia.associative_memory.basic_associative_memory import AssociativeMemoryBank
from concordia.typing import entity, entity_component as ec
from .common import canonical, digest, Decision

def hash_embed(text):
    vector=np.zeros(512,dtype=np.float64)
    text=text.casefold()
    for i in range(max(1,len(text)-2)):
        key=int(digest(text[i:i+3])[:8],16)
        vector[key%512] += 1 if key&512 else -1
    norm=np.linalg.norm(vector)
    return vector/norm if norm else vector

class FixedContext(ec.ContextComponent):
    def __init__(self,value): self.value=value
    def pre_act(self,action_spec): return canonical(self.value)
    def get_state(self): return {'schema':1,'hash':digest(self.value),'value':self.value}
    def set_state(self,state):
        if state['schema']!=1 or digest(state['value'])!=state['hash']: raise ValueError('COMPONENT_HASH')
        self.value=state['value']

class Observation(FixedContext):
    def pre_observe(self,observation): self.value=json.loads(observation); return ''

class PrivateMemory(ec.ContextComponent):
    def __init__(self,records):
        self.records=records
        if len({r['id'] for r in records})!=len(records): raise ValueError('DUPLICATE_MEMORY_ID')
        self.bank=AssociativeMemoryBank(sentence_embedder=hash_embed,allow_duplicates=True)
        for record in records: self.bank.add(canonical(record))
    def pre_act(self,action_spec):
        observation=self.get_entity().get_component('observation').value
        retrieved=self.bank.retrieve_associative(canonical(observation),k=min(4,len(self.records))) if self.records else []
        selected={r['id']:r for r in self.records[-12:]}
        for text in retrieved:
            record=json.loads(text); selected[record['id']]=record
        return canonical(sorted(selected.values(),key=lambda r:(r['time'],r['id'])))
    def get_state(self): return {'schema':1,'records':self.records,'hash':digest(self.records)}
    def set_state(self,state):
        if state['schema']!=1 or digest(state['records'])!=state['hash']: raise ValueError('MEMORY_HASH')
        self.__init__(state['records'])

class ShopperAction(ec.ActingComponent):
    def __init__(self,model): self.model=model; self.calls=0; self.prompt_hash=None
    def get_action_attempt(self,context,action_spec):
        payload={key:json.loads(value) for key,value in context.items()}
        prompt=canonical(payload); self.prompt_hash=digest(prompt); self.calls+=1
        return self.model.sample_text(prompt)
    def get_state(self): return {'schema':1,'calls':self.calls,'prompt_hash':self.prompt_hash}
    def set_state(self,state):
        if state['schema']!=1: raise ValueError('ACTION_SCHEMA')
        self.calls=state['calls']; self.prompt_hash=state['prompt_hash']

def decide(observation,memory,model):
    current=dict(observation); persona=current.pop('persona')
    components={'persona':FixedContext(persona),'observation':Observation({}),'memory':PrivateMemory(memory)}
    acting=ShopperAction(model)
    agent=EntityAgent(agent_name=persona['id'],act_component=acting,context_components=components)
    agent.observe(canonical(current))
    output=agent.act(entity.free_action_spec(call_to_action='Choose one allowed shopping action.'))
    if agent.get_phase()!=ec.Phase.READY or acting.calls!=1: raise ValueError('CONCORDIA_LIFECYCLE')
    states={key:component.get_state() for key,component in components.items()}
    # Rebuild validation is explicit; EntityAgent.set_state can swallow errors.
    for key,state in states.items():
        clone=PrivateMemory([]) if key=='memory' else FixedContext({})
        clone.set_state(state)
        if digest(clone.get_state())!=digest(state): raise ValueError('RESTORE_HASH_MISMATCH')
    return Decision.model_validate_json(output).model_dump(),{
        'concordia_version':'2.4.0','phase':'READY','component_hashes':{k:digest(v) for k,v in states.items()},
        'prompt_hash':acting.prompt_hash,'sample_text_calls':acting.calls,'embedder':'character-trigram-sha256-512-v1'}

class DeterministicGM(ec.ActingComponent):
    def get_action_attempt(self,context,action_spec):
        resolution=json.loads(context['rules'])
        d=Decision.model_validate(resolution['decision']).model_dump()
        if {'action':d['action'],'sku':d['sku']} not in resolution['allowed']:
            raise ValueError('INVALID_ACTION')
        return canonical(d)
    def get_state(self): return {'schema':1}
    def set_state(self,state):
        if state!={'schema':1}: raise ValueError('GM_SCHEMA')

def resolve_decision(decision,allowed):
    gm=EntityAgent('Deterministic retail Game Master',DeterministicGM(),
        context_components={'rules':FixedContext({'decision':decision,'allowed':allowed})})
    result=gm.act(entity.free_action_spec(call_to_action='Validate the intended action under frozen rules.'))
    if gm.get_phase()!=ec.Phase.READY: raise ValueError('GM_NOT_READY')
    return json.loads(result)
