import json
"""Pure subscription reconciliation: never mutate unrelated profiles or caller state."""
from dataclasses import dataclass,field,asdict
import copy,uuid
from .profiles import ProfileError

@dataclass
class Subscription:
    name:str
    url:str
    id:str=field(default_factory=lambda:uuid.uuid4().hex)
    updated_at:str=''
    status:str='unknown'
    last_error:str=''
    metadata:dict=field(default_factory=dict)
    is_free:bool=False
    source_key:str=''
    def to_dict(self):return asdict(self)

def reconcile(current,incoming,subscription_id,selected):
    if not incoming:raise ProfileError('The subscription returned no profiles. Existing profiles were kept.')
    old={(p.original,json.dumps(p.raw,sort_keys=True) if p.raw else ""):p for p in current if p.subscription_id==subscription_id or p.favorite_source_id==subscription_id}
    output=[copy.deepcopy(p) for p in current if p.subscription_id!=subscription_id]
    seen=set();updated=[]
    for item in incoming:
        identity=(item.original,json.dumps(item.raw,sort_keys=True) if item.raw else "")
        if identity in seen:continue
        seen.add(identity);p=copy.deepcopy(item);previous=old.get(identity)
        if previous:
            for key in ('id','favorite','favorite_source_id','service_score','service_cache','gemini_ok','latency','tested_at','last_success','test_status','test_method','test_error'):setattr(p,key,getattr(previous,key))
        if previous and previous.favorite_source_id==subscription_id and not previous.subscription_id:
            p.favorite_source_id=subscription_id;p.subscription_id=''
            output=[p if item.id==previous.id else item for item in output]
        else:
            p.subscription_id=subscription_id
            updated.append(p)
    output.extend(updated)
    if selected not in {p.id for p in output}:selected=updated[0].id
    return output,selected
