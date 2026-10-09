"""Authoritative discrete-event worlds; model latency never advances this clock."""
from __future__ import annotations
import copy
from collections import deque
from .common import (RunConfig, Decision, CATALOG, WORLDS, NATURAL, TERMINAL,
                     canonical, digest, uniform, personas, truth)

DEST = {'fitting':(26,5),'preview':(21,12),'checkout':(26,17),'exit':(30,18)}

def route(start, target):
    start=tuple(map(round,start)); target=tuple(map(round,target))
    blocked={(x,y) for sku in CATALOG for x in range(sku['x']-1,sku['x']+2) for y in (3,4)}
    queue=deque([start]); parent={start:None}
    while queue:
        cell=queue.popleft()
        if cell==target: break
        for dx,dy in ((1,0),(0,1),(-1,0),(0,-1)):
            nxt=(cell[0]+dx,cell[1]+dy)
            if 1<=nxt[0]<=30 and 1<=nxt[1]<=18 and nxt not in blocked and nxt not in parent:
                parent[nxt]=cell; queue.append(nxt)
    if target not in parent: raise ValueError('UNREACHABLE_ZONE')
    path=[]; cell=target
    while cell is not None: path.append(list(cell)); cell=parent[cell]
    return list(reversed(path))

class Engine:
    def __init__(self,state):
        self.s=state
        self.events=[]
    @classmethod
    def create(cls,config):
        c=RunConfig.model_validate(config).model_dump()
        people=personas(c['seed'])[:c['n_agents']]
        state={'schema_version':1,'config':c,'t':0,'order':0,'seq':0,'agenda':[],
               'personas':{p['id']:p for p in people},'latent':{},'worlds':{}}
        engine=cls(state)
        for p in people:
            state['latent'][p['id']]={sku['id']:truth(c['seed'],p['id'],sku['id']) for sku in CATALOG}
        for world in WORLDS:
            resources={key:{'capacity':cap,'busy':{},'queue':[],
                           'external_until':c['initial_fitting_delay'] if key=='fitting' else 0}
                       for key,cap in [('fitting',c['fitting_rooms']),
                           ('preview',c['preview_devices'] if world=='anywear' else 0),
                           ('checkout',c['checkout_desks'])]}
            state['worlds'][world]={'agents':{},'resources':resources,'waits':[],
                'stock':{sku['id']:{'initial':c['stock_per_sku'],'available':c['stock_per_sku'],
                    'reserved':0,'sold':0} for sku in CATALOG},'sales':[], 'services':[], 'heat':{}}
            for i,p in enumerate(people):
                arrival=i*c['arrival_seconds']
                state['worlds'][world]['agents'][p['id']]={
                    'id':p['id'],'status':'NOT_ARRIVED','position':[3,14], 'movement':None,
                    'arrival':arrival,'deadline':arrival+p['remaining_seconds'],'ready':False,
                    'decisions':0,'known':{},'memory':[],'last_decision':None,'reserved_sku':None,
                    'reserved_price':None,'queue':None,'suitable':False,'ended_at':None}
                engine.schedule(arrival,world,p['id'],'arrival')
                engine.schedule(arrival+p['remaining_seconds'],world,p['id'],'deadline')
            if c['initial_fitting_delay']:
                engine.schedule(c['initial_fitting_delay'],world,None,'external_release',{'resource':'fitting'})
        return engine
    @property
    def c(self): return self.s['config']
    def hash(self): return digest(self.s)
    def schedule(self,ts,world,aid,kind,data=None):
        self.s['order']+=1
        priority={'service_done':0,'move_done':0,'external_release':0,'arrival':1,'deadline':2,'reminder':3}[kind]
        self.s['agenda'].append({'t':int(ts),'priority':priority,
            'tie':uniform(self.c['seed'],aid or '',kind,'tie'), 'order':self.s['order'],
            'world':world,'agent':aid,'kind':kind,'data':data or {}})
    def emit(self,kind,world,aid=None,**data):
        self.s['seq']+=1
        event={'schema_version':1,'seq':self.s['seq'],'virtual_time':self.s['t'],
               'world_id':world,'agent_id':aid,'kind':kind,'data':data}
        self.events.append(event)
        if aid:
            agent=self.s['worlds'][world]['agents'][aid]
            memory={'id':digest([world,aid,event['seq']]),'time':self.s['t'],
                    'kind':kind,'data':copy.deepcopy(data)}
            agent['memory'].append(memory)
        return event
    def ready(self):
        # Single-event stepping must not split simultaneous observations.
        if any(e['t']==self.s['t'] for e in self.s['agenda']): return []
        return sorted([(w,a['id']) for w in WORLDS for a in self.s['worlds'][w]['agents'].values()
                       if a['ready'] and a['status'] not in TERMINAL],
                      key=lambda pair:(uniform(self.c['seed'],pair[1],'frontier'),pair[0]))
    def complete(self):
        return all(a['status'] in TERMINAL for w in self.s['worlds'].values() for a in w['agents'].values())
    def advance(self,one_event=False,breakpoints=()):
        self.events=[]
        if self.ready() or self.complete(): return self.ready()
        count=0
        while self.s['agenda']:
            self.s['agenda'].sort(key=lambda e:(e['t'],e['priority'],e['tie'],e['order'],e['world']))
            event=self.s['agenda'].pop(0)
            self.s['t']=event['t']; self.handle(event); count+=1
            # Even an expired/no-op agenda entry changes authoritative state.
            self.emit('WORLD_ADVANCED',event['world'],agenda_kind=event['kind'],agenda_order=event['order'])
            if one_event or any(e['kind'] in breakpoints for e in self.events): break
            next_t=min((e['t'] for e in self.s['agenda']),default=None)
            if self.ready() and next_t!=self.s['t']: break
            if self.complete(): break
        if not self.s['agenda'] and not self.ready() and not self.complete():
            raise ValueError('NO_PROGRESS')
        self.invariants()
        return self.ready()
    def handle(self,event):
        w,aid,kind,data=event['world'],event['agent'],event['kind'],event['data']
        world=self.s['worlds'][w]
        if kind=='external_release':
            self.grant(w,data['resource']); return
        agent=world['agents'][aid]
        if agent['status'] in TERMINAL: return
        if kind=='arrival':
            agent.update(status='DECIDING',ready=True)
            self.emit('ARRIVED',w,aid,given_history=True); return
        if kind=='deadline':
            self.finish(w,aid,'TIME_LIMIT'); return
        if kind=='move_done':
            if not agent['movement'] or agent['movement']['token']!=data['token']: return
            agent.update(position=agent['movement']['path'][-1],movement=None)
            if data['next']=='browse':
                agent['status']='BROWSING'
                self.schedule(self.s['t']+self.c['browse_seconds'],w,aid,'service_done',
                              {'resource':'browse','sku':data['sku'],'token':None})
                self.emit('BROWSE_STARTED',w,aid,sku=data['sku'])
            else: self.enqueue(w,aid,data['next'],data['sku'])
            return
        if kind=='reminder':
            if agent['queue'] and agent['queue']['token']==data['token']:
                agent['ready']=True
                self.emit('QUEUE_REMINDER',w,aid,resource=agent['queue']['resource'])
            return
        if kind=='service_done':
            resource=data['resource']; sku=data['sku']
            if resource!='browse':
                r=world['resources'][resource]
                busy=r['busy'].get(str(data['slot']))
                if not busy or busy['token']!=data['token']: return
                del r['busy'][str(data['slot'])]
                world['services'].append({'resource':resource,'start':busy['start'],
                    'end':self.s['t'],'agent':aid,'completed':True})
            known=agent['known'].setdefault(sku,{})
            latent=self.s['latent'][aid][sku]
            if resource=='fitting':
                known.update(fit=round(latent['fit'],4),appearance=round(latent['appearance'],4),physical=True)
                self.emit('PHYSICAL_RESULT',w,aid,sku=sku,observed=copy.deepcopy(known))
            elif resource=='preview':
                signal_value=max(0,min(1,latent['appearance']+self.c['preview_noise']*latent['noise_u']))
                # A shopper cannot obtain independent samples by repeatedly previewing.
                known.setdefault('preview',round(signal_value,4))
                self.emit('PREVIEW_RESULT',w,aid,sku=sku,appearance_signal=known['preview'])
            elif resource=='browse':
                known['browsed']=True; self.emit('BROWSED',w,aid,sku=sku)
            elif resource=='checkout':
                price=agent['reserved_price']
                stock=world['stock'][sku]
                if agent['reserved_sku']!=sku or not stock['reserved']: raise ValueError('RESERVATION_LOST')
                stock['reserved']-=1; stock['sold']+=1
                person=self.s['personas'][aid]
                suitable=(latent['fit']>=person['accept_threshold'] and
                          latent['appearance']>=person['accept_threshold'] and
                          price<=person['budget_cents'] and self.s['t']<=agent['deadline'])
                sale={'agent':aid,'sku':sku,'price_cents':price,'time':self.s['t'],'suitable':suitable}
                world['sales'].append(sale)
                agent.update(reserved_sku=None,reserved_price=None,suitable=suitable)
                self.finish(w,aid,'PURCHASED',sku=sku,price_cents=price,suitable=suitable)
                if suitable: self.emit('GOAL_MET',w,aid,source='synthetic_ground_truth')
            if resource!='checkout': agent.update(status='DECIDING',ready=True)
            if resource!='browse': self.grant(w,resource)
    def walk(self,w,aid,target,next_kind,sku):
        agent=self.s['worlds'][w]['agents'][aid]
        path=route(agent['position'],target)
        token=digest([self.s['order'],w,aid,sku,next_kind,self.s['seq']])
        agent.update(status='MOVING',ready=False,movement={'path':path,'start':self.s['t'],
            'end':self.s['t']+max(1,len(path)-1),'token':token,'next':next_kind})
        self.schedule(agent['movement']['end'],w,aid,'move_done',{'token':token,'next':next_kind,'sku':sku})
        for x,y in path:
            key=f'{x},{y}'; heat=self.s['worlds'][w]['heat']; heat[key]=heat.get(key,0)+1
        self.emit('MOVEMENT',w,aid,destination=next_kind,sku=sku,path=path)
    def enqueue(self,w,aid,resource,sku):
        world=self.s['worlds'][w]; agent=world['agents'][aid]
        token=digest([w,aid,resource,self.s['seq'],'queue'])
        entry={'agent':aid,'sku':sku,'joined':self.s['t'],'token':token}
        world['resources'][resource]['queue'].append(entry)
        agent.update(status='QUEUED_'+resource.upper(),ready=False,
                     queue={'resource':resource,**entry})
        self.emit('QUEUE_JOINED',w,aid,resource=resource,sku=sku)
        self.grant(w,resource)
        if agent['queue']:
            self.schedule(self.s['t']+self.s['personas'][aid]['patience_seconds'],w,aid,'reminder',{'token':token})
    def grant(self,w,resource):
        world=self.s['worlds'][w]; r=world['resources'][resource]
        if self.s['t']<r['external_until']: return
        while r['queue'] and len(r['busy'])<r['capacity']:
            entry=r['queue'].pop(0); aid=entry['agent']; agent=world['agents'][aid]
            if agent['status'] in TERMINAL or not agent['queue'] or agent['queue']['token']!=entry['token']: continue
            slot=next(i for i in range(r['capacity']) if str(i) not in r['busy'])
            seconds=self.c[resource+'_seconds'] if resource!='fitting' else self.c['fitting_seconds']
            busy={'agent':aid,'sku':entry['sku'],'start':self.s['t'],
                  'until':self.s['t']+seconds,'token':entry['token']}
            r['busy'][str(slot)]=busy
            world['waits'].append({'agent':aid,'resource':resource,'joined':entry['joined'],
                'ended':self.s['t'],'seconds':self.s['t']-entry['joined'],'outcome':'served'})
            agent.update(status=resource.upper(),queue=None,ready=False)
            agent['position']=list(DEST[resource]); agent['position'][1]+=slot*2 if resource=='fitting' else slot
            self.emit('SERVICE_STARTED',w,aid,resource=resource,sku=entry['sku'],slot=slot,until=busy['until'])
            self.schedule(busy['until'],w,aid,'service_done',{'resource':resource,'sku':entry['sku'],
                'slot':slot,'token':entry['token']})
    def abandon(self,w,aid):
        world=self.s['worlds'][w]; agent=world['agents'][aid]
        if agent['reserved_sku']:
            sku=agent['reserved_sku']; stock=world['stock'][sku]
            stock['reserved']-=1; stock['available']+=1
            agent.update(reserved_sku=None,reserved_price=None)
            self.emit('RESERVATION_RELEASED',w,aid,sku=sku)
        if agent['queue']:
            q=agent['queue']; r=world['resources'][q['resource']]
            r['queue']=[item for item in r['queue'] if item['token']!=q['token']]
            world['waits'].append({'agent':aid,'resource':q['resource'],'joined':q['joined'],
                'ended':self.s['t'],'seconds':self.s['t']-q['joined'],'outcome':'abandoned'})
            agent['queue']=None
            self.emit('QUEUE_ABANDONED',w,aid,resource=q['resource'])
    def finish(self,w,aid,status,**data):
        world=self.s['worlds'][w]; agent=world['agents'][aid]
        self.abandon(w,aid)
        if agent['reserved_sku']:
            stock=world['stock'][agent['reserved_sku']]; stock['reserved']-=1; stock['available']+=1
            agent.update(reserved_sku=None,reserved_price=None)
        freed=[]
        for key,r in world['resources'].items():
            for slot,busy in list(r['busy'].items()):
                if busy['agent']==aid:
                    del r['busy'][slot]; freed.append(key)
                    world['services'].append({'resource':key,'start':busy['start'],'end':self.s['t'],
                                              'agent':aid,'completed':False})
        agent.update(status=status,ready=False,movement=None,ended_at=self.s['t'],position=list(DEST['exit']))
        self.emit(status,w,aid,**data)
        for key in freed: self.grant(w,key)
    def actions(self,w,aid):
        world=self.s['worlds'][w]; a=world['agents'][aid]; p=self.s['personas'][aid]
        choices=[{'action':'leave','sku':''}]
        if a['queue']: choices.append({'action':'wait','sku':''})
        for item in CATALOG:
            sku=item['id']
            choices.append({'action':'browse','sku':sku})
            if world['stock'][sku]['available']>0:
                if not a['queue'] or a['queue']['resource']!='fitting': choices.append({'action':'try_on','sku':sku})
                if w=='anywear' and (not a['queue'] or a['queue']['resource']!='preview'):
                    choices.append({'action':'preview','sku':sku})
                if self.c['price_cents']<=p['budget_cents']: choices.append({'action':'buy','sku':sku})
        return choices
    def observation(self,w,aid):
        world=self.s['worlds'][w]; agent=world['agents'][aid]
        def estimated_wait(key,r):
            if not r['capacity']: return None
            import heapq
            slots=[max(self.s['t'],r['external_until'],r['busy'].get(str(i),{}).get('until',self.s['t']))
                   for i in range(r['capacity'])]
            heapq.heapify(slots)
            for entry in r['queue']:
                available=heapq.heappop(slots)
                if entry['agent']==aid: return max(0,available-self.s['t'])
                heapq.heappush(slots,available+self.c[key+'_seconds'])
            return max(0,min(slots)-self.s['t'])
        resources={key:{'capacity':r['capacity'],'busy':len(r['busy']),'queue_length':len(r['queue']),
            'initial_busy_remaining':max(0,r['external_until']-self.s['t']),
            'estimated_wait_seconds':estimated_wait(key,r)}
            for key,r in world['resources'].items()}
        return {'agent_id':aid,'persona':copy.deepcopy(self.s['personas'][aid]),
            'condition':'Anywear available' if w=='anywear' else 'Anywear not provided',
            'ordinary_mirror':True,'virtual_time':self.s['t'],
            'elapsed_shopping_seconds':1200+(agent['ended_at'] if agent['ended_at'] is not None else self.s['t'])-agent['arrival'],
            'remaining_seconds':max(0,agent['deadline']-(agent['ended_at'] if agent['ended_at'] is not None else self.s['t'])),
            'status':agent['status'],'resources':resources,
            'reserved_purchase':{'sku':agent['reserved_sku'],'price_cents':agent['reserved_price']} if agent['reserved_sku'] else None,
            'catalogue':[{**sku,'price_cents':self.c['price_cents'],
                'available':world['stock'][sku['id']]['available'],
                'own_observations':copy.deepcopy(agent['known'].get(sku['id'],{}))} for sku in CATALOG],
            'allowed_actions':self.actions(w,aid)}
    def apply(self,w,aid,decision,allowed=None):
        d=Decision.model_validate(decision).model_dump()
        agent=self.s['worlds'][w]['agents'][aid]; world=self.s['worlds'][w]
        if not agent['ready']: raise ValueError('STALE_DECISION')
        if {'action':d['action'],'sku':d['sku']} not in (allowed or self.actions(w,aid)):
            raise ValueError('INVALID_ACTION')
        agent['decisions']+=1; agent['last_decision']=d; agent['ready']=False
        self.emit('DECISION',w,aid,**d)
        if d['action']=='leave': self.finish(w,aid,'LEFT'); return
        if agent['decisions']>=self.c['decision_cap']:
            self.finish(w,aid,'CENSORED',reason='decision_cap'); return
        if d['action']=='wait':
            if not agent['queue']: raise ValueError('NOT_QUEUED')
            self.schedule(self.s['t']+max(1,self.s['personas'][aid]['patience_seconds']),w,aid,
                          'reminder',{'token':agent['queue']['token']}); return
        self.abandon(w,aid)
        sku=d['sku']; action=d['action']
        if action!='browse' and world['stock'][sku]['available']<=0:
            agent.update(status='DECIDING',ready=True)
            self.emit('STOCKOUT',w,aid,sku=sku); return
        if action=='buy':
            stock=world['stock'][sku]; stock['available']-=1; stock['reserved']+=1
            agent.update(reserved_sku=sku,reserved_price=self.c['price_cents'])
        kind={'try_on':'fitting','preview':'preview','buy':'checkout','browse':'browse'}[action]
        target=next((item['x'],item['y']) for item in CATALOG if item['id']==sku) if kind=='browse' else DEST[kind]
        self.walk(w,aid,target,kind,sku)
    def invariants(self):
        for world in self.s['worlds'].values():
            for sku,stock in world['stock'].items():
                if min(stock.values())<0 or stock['initial']!=sum(stock[k] for k in ('available','reserved','sold')):
                    raise ValueError('INVENTORY_INVARIANT')
                reservations=sum(a['reserved_sku']==sku for a in world['agents'].values())
                if reservations!=stock['reserved']: raise ValueError('RESERVATION_INVARIANT')
                if sum(s['sku']==sku for s in world['sales'])!=stock['sold']: raise ValueError('SALES_INVARIANT')
            if len({s['agent'] for s in world['sales']})!=len(world['sales']): raise ValueError('DUPLICATE_PAYMENT')
            for r in world['resources'].values():
                if len(r['busy'])>r['capacity']: raise ValueError('RESOURCE_CAPACITY')
            for agent in world['agents'].values():
                if agent['ended_at'] is not None and agent['ended_at']>agent['deadline']:
                    raise ValueError('TIME_INVARIANT')
        return True
    def public(self):
        result={k:copy.deepcopy(self.s[k]) for k in ('schema_version','t','seq','config','personas')}
        result['state_hash']=self.hash(); result['worlds']=copy.deepcopy(self.s['worlds'])
        return result

def demo_decision(observation):
    """Clearly synthetic rule fixture. Never substitutes for a failed LLM."""
    allowed=observation['allowed_actions']; p=observation['persona']
    chosen={'action':'leave','sku':''}; code='no_options'
    if observation['status'].startswith('QUEUED'):
        chosen={'action':'wait','sku':''}; code='queue'
    else:
        candidates=sorted(observation['catalogue'],key=lambda s:abs(s['style']-p['style_preference']))
        for item in candidates:
            known=item['own_observations']
            if item['price_cents']>p['budget_cents']: continue
            if known.get('fit',0)>=p['accept_threshold'] and known.get('appearance',0)>=p['accept_threshold']:
                chosen={'action':'buy','sku':item['id']}; code='suitable'; break
            if observation['remaining_seconds']<200: continue
            if observation['condition']=='Anywear available' and 'preview' not in known and p['trust']>.25:
                chosen={'action':'preview','sku':item['id']}; code='trust'; break
            if not known.get('physical') and (known.get('preview',1)>=.5 or p['trust']<.4):
                chosen={'action':'try_on','sku':item['id']}; code='fit'; break
    if chosen not in allowed: chosen={'action':'leave','sku':''}; code='no_options'
    return {**chosen,'reason_code':code,'reason_zh':'DEMO 规则动作，用于功能验证。',
            'reason_en':'DEMO rule action for software verification.'}
