"""Provider quota, never inferred from local session counters."""
from dataclasses import dataclass
@dataclass(frozen=True)
class Usage:
    known:bool
    used:int=0
    total:int=0
    percent:float=0
    remaining:int=0

def subscription_usage(metadata):
    if not isinstance(metadata,dict):return Usage(False)
    values=[metadata.get(k) for k in ('upload','download','total')]
    if any(type(n) is not int or n<0 or n>2**63-1 for n in values) or values[2]==0:return Usage(False)
    upload,download,total=values;used=upload+download
    return Usage(True,used,total,100*used/total,max(0,total-used))

def size(n):
    for unit in ('B','KiB','MiB','GiB','TiB'):
        if n<1024:return f'{n:.1f} {unit}'
        n/=1024
    return f'{n:.1f} PiB'
