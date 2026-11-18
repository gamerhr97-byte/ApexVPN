"""Fixed-message structured logs. Never accept raw config/core output for display/export."""
import collections,datetime,re
from dataclasses import dataclass
from PySide6.QtCore import QObject,Signal
from .errors import MESSAGES

EXTRA={
 'CONNECTED':'HTTPS through the selected proxy was verified.',
 'CONNECT_ATTEMPT':'Starting a supervised, verified connection attempt.',
 'SUBSCRIPTION':'Subscription operation failed; existing data was kept.',
 'PREFERENCES':'A preference operation could not complete.',
 'HTTP_OPTIONAL':'Optional HTTP check failed; HTTPS is the required connection gate.',
 'EVENT':'A sanitized diagnostic event occurred. Run diagnostics for details.'}
STAGES={'idle','configuration','core-validation','core-start','process-supervision','https-verification','http-check','system-proxy','connected'}
@dataclass(frozen=True)
class Entry:
    timestamp:str
    severity:str
    code:str
    stage:str
    message:str
    def line(self):return f'{self.timestamp}  {self.severity.upper():7}  [{self.code}]  {self.stage} · {self.message}'

class LogBook(QObject):
    changed=Signal()
    def __init__(self,parent=None):super().__init__(parent);self.entries=collections.deque(maxlen=500)
    def append(self,text,severity='Error',stage='idle'):
        code=next((k for k in MESSAGES if re.search(r'\b'+re.escape(k)+r'\b',text)),None)
        if not code:
            if text.startswith('Optional HTTP'):code='HTTP_OPTIONAL'
            elif text.startswith('[CORE]'):code='CONNECT_ATTEMPT'
            elif text.startswith('[STATE]'):code='CONNECTED'
            elif text.startswith('[SUBSCRIPTION]'):code='SUBSCRIPTION'
            elif text.startswith('[PREFERENCES]'):code='PREFERENCES'
            elif 'crashed' in text.lower():code='CORE_EXIT'
            else:code='EVENT'
        entry=Entry(datetime.datetime.now().astimezone().isoformat(timespec='seconds'),severity if severity in ('Error','Warning','Info','Debug') else 'Error',code,stage if stage in STAGES else 'idle',MESSAGES.get(code,EXTRA.get(code,EXTRA['EVENT'])))
        self.entries.append(entry);self.changed.emit()
    def clear(self):self.entries.clear();self.changed.emit()
    def text(self,query='',severity='All'):
        query=query.casefold()
        return '\n'.join(e.line() for e in self.entries if (severity=='All' or e.severity==severity) and (not query or query in e.line().casefold()))
