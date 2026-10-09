from __future__ import annotations
import hashlib
import json
import os
import random
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('ANYWEAR_LAB_DATA', ROOT / '.lab-data')).resolve()
SCHEMA_VERSION = 1
NATURAL = {'PURCHASED', 'LEFT', 'TIME_LIMIT'}
TERMINAL = NATURAL | {'CENSORED'}
WORLDS = ('control', 'anywear')

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def uniform(seed, *key):
    return int(digest([seed, *key])[:13], 16) / 0xfffffffffffff

class Costs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    cogs_cents: int = Field(6000, ge=0, le=1000000)
    capex_cents: int = Field(300000, ge=0, le=100000000)
    monthly_fixed_cents: int = Field(20000, ge=0, le=100000000)
    preview_cents: int = Field(0, ge=0, le=1000000)
    monthly_eligible: int = Field(1000, ge=1, le=10000000)
    assumed: bool = True

class Targets(BaseModel):
    model_config = ConfigDict(extra='forbid')
    min_monthly_increment_cents: int = 0
    max_leave_delta: float = Field(0, ge=-1, le=1)
    min_suitable_delta: float = Field(0, ge=-1, le=1)

class RunConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field('受挫购物基准 / Frustrated-shopping baseline', max_length=120)
    mode: Literal['demo', 'codex'] = 'demo'
    n_agents: int = Field(10, ge=1, le=100)
    seed: int = Field(20261009, ge=0, le=2147483647)
    price_cents: int = Field(12000, ge=100, le=1000000)
    stock_per_sku: int = Field(20, ge=1, le=10000)
    arrival_seconds: int = Field(30, ge=1, le=600)
    fitting_rooms: int = Field(4, ge=1, le=16)
    preview_devices: int = Field(1, ge=1, le=8)
    checkout_desks: int = Field(1, ge=1, le=8)
    initial_fitting_delay: int = Field(0, ge=0, le=3600)
    fitting_seconds: int = Field(180, ge=15, le=1800)
    preview_seconds: int = Field(45, ge=5, le=600)
    checkout_seconds: int = Field(30, ge=5, le=600)
    browse_seconds: int = Field(60, ge=5, le=600)
    preview_noise: float = Field(0.2, ge=0, le=1)
    decision_cap: int = Field(64, ge=16, le=256)
    attempt_budget: int = Field(200, ge=1, le=100000)
    model: Literal['gpt-6.1-sol'] = 'gpt-6.1-sol'
    timeout_seconds: int = Field(180, ge=30, le=300)
    breakpoints: list[Literal['PURCHASED','LEFT','QUEUE_JOINED','INVALID','GOAL_MET']] = []
    costs: Costs = Field(default_factory=Costs)
    targets: Targets = Field(default_factory=Targets)

class Decision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['browse','preview','try_on','buy','wait','leave']
    sku: str = Field(max_length=20)
    reason_code: Literal['fit','style','fatigue','budget','queue','privacy','trust','suitable','no_options']
    reason_zh: str = Field(min_length=1, max_length=240)
    reason_en: str = Field(min_length=1, max_length=320)

def personas(seed):
    # Fixed 100-person pool: smoke cohort is a subset, never a population estimate.
    axes = {}
    for key in ('budget','time','privacy','trust','threshold','style','patience'):
        rng = random.Random(int(digest([seed, key])[:16], 16))
        values = [(i + rng.random()) / 100 for i in range(100)]
        rng.shuffle(values)
        axes[key] = values
    return [{
        'id': f'C{i+1:03}', 'budget_cents': round((50 + 450 * axes['budget'][i]) * 100),
        'remaining_seconds': round((5 + 25 * axes['time'][i]) * 60),
        'privacy': round(axes['privacy'][i], 4), 'trust': round(axes['trust'][i], 4),
        'accept_threshold': round(0.6 + 0.25 * axes['threshold'][i], 4),
        'style_preference': round(axes['style'][i], 4),
        'patience_seconds': round(120 + 480 * axes['patience'][i]),
        'given_history': {'spent_minutes':20, 'failed_physical_tries':3, 'source':'given_baseline'},
    } for i in range(100)]

CATALOG = [
    {'id':f'S{i+1}', 'name_zh':zh, 'name_en':en, 'style':style, 'x':5+i*3, 'y':6}
    for i,(zh,en,style) in enumerate([
        ('运动上衣 A','Training top A',.1),('运动上衣 B','Training top B',.3),
        ('运动上衣 C','Training top C',.5),('运动长裤 A','Training pants A',.6),
        ('运动长裤 B','Training pants B',.8),('运动长裤 C','Training pants C',.95)])
]

def truth(seed, agent, sku):
    return {'fit':uniform(seed,agent,sku,'fit'), 'appearance':uniform(seed,agent,sku,'appearance'),
            'noise_u':2*uniform(seed,agent,sku,'preview')-1}
