"""Typed, versioned preferences. No profile credentials belong in this schema."""
from dataclasses import dataclass
import copy, os, pathlib, re
from urllib.parse import urlsplit

BASE=pathlib.Path(__file__).resolve().parents[1]
CATEGORIES=[('General','عمومی'),('Connection & Smart Connect','اتصال و انتخاب هوشمند'),('Network Cores','هسته‌های شبکه'),('Proxy & Windows Integration','پروکسی و ویندوز'),('Split Tunneling','مسیریابی تفکیکی'),('Security & Privacy','امنیت و حریم خصوصی'),('Diagnostics & Recovery','عیب‌یابی و بازیابی'),('Subscriptions & Configurations','اشتراک‌ها و پیکربندی'),('Telegram Proxies','پروکسی‌های تلگرام'),('Performance & Monitoring','کارایی و پایش'),('Interface & System Tray','رابط و سینی سیستم'),('Advanced & Developer','پیشرفته و توسعه‌دهنده'),('Logs','لاگ‌ها'),('Direct Exceptions','اتصال مستقیم سایت‌ها و برنامه‌ها'),('Internet Usage','مصرف اینترنت')]

@dataclass(frozen=True)
class Setting:
    key:str
    section:int
    title:str
    fa:str
    default:object
    kind:str='bool'
    choices:tuple=()
    minimum:int=0
    maximum:int=100
    description:str=''
    permission:str='user'
    application:str='next connection'
    export:bool=True
    advanced:bool=False
    unavailable:str=''
    @property
    def persistence(self):return 'atomic settings.json'
    @property
    def error_handling(self):return 'reject entire change set; keep previous preferences'
    @property
    def reset(self):return copy.deepcopy(self.default)

SPECS=[]
def add(key,section,title,fa,default,kind='bool',**kw):
    item=Setting(key,section,title,fa,default,kind,**kw);SPECS.append(item);return item

add('auto_save',0,'Automatically save simple preferences','ذخیره خودکار گزینه‌های ساده',True,application='on Apply',description='Appearance and harmless preferences save automatically. Network, startup, core and imported batches still require Apply.')
add('automatic_tuning',9,'Automatic performance tuning','تنظیم خودکار کارایی',True,application='on Apply',description='Uses bounded retry, timeout and concurrency defaults. Turn off to edit these values manually.')
add('allow_insecure_profiles',5,'Allow insecure TLS profiles (unsafe)','اجازه پروفایل با TLS ناامن',False,description='Explicit opt-in only for auxiliary profiles containing insecure=1. Prefer a trusted certificate and correct SNI.')
add('service_checks',5,'Check HTTPS websites with / without VPN','بررسی سایت‌های HTTPS با و بدون VPN',True,application='on Apply',description='Direct when disconnected; live proxy CONNECT when connected. Website checks do not guarantee account access or IP reputation.')
add('launch_startup',0,'Launch at Windows sign-in','اجرا هنگام ورود به ویندوز',False,permission='current-user registry',application='on Apply',unavailable='' if os.name=='nt' else 'Windows current-user startup is available on Windows only.')
add('start_minimized',0,'Start minimized','شروع به‌صورت کوچک‌شده',False,application='next launch')
add('start_tray',0,'Start in system tray','شروع در سینی سیستم',False,application='next launch')
add('allow_resize',10,'Allow window resizing','اجازه تغییر اندازه پنجره',False,application='on Apply')
add('remove_failed_servers',7,"Remove servers that do not work",'حذف سرورهای ناموفق پس از تست',False,description='OFF by default. After a completed batch, remove Failed/Timeout/Refused profiles from that tested group. A backup is made. Unsupported profiles and canceled tests are kept.')
add('tcp_concurrency',9,'Parallel quick checks','تعداد تست سریع هم‌زمان',128,'int',minimum=8,maximum=256,application='on Apply',advanced=True)
add('singbox_core',2,'sing-box executable path','مسیر هسته sing-box',str(BASE/'core'/('sing-box.exe' if os.name=='nt' else 'sing-box')),'path',export=False)
add('quality_checks',9,'Check 100 service destinations during HTTPS tests','بررسی دسترسی ۱۰۰ سایت در تست HTTPS',False,description='Optional: 100 destinations: 5 HTTPS + 95 TCP/CONNECT checks per verified server. Check badge requires at least 90 successes; Gemini badge checks the Gemini public page, not signed-in eligibility.')
add('remember_window',0,'Remember window size','به‌خاطر سپردن اندازه پنجره',True,application='next launch',description='Restores your saved compact window size at launch. Opening Settings never resizes the window.')
add('remember_profile',0,'Remember selected profile','به‌خاطر سپردن سرور انتخابی',True,application='next launch')
add('language',0,'Language','زبان','en','choice',choices=('en','fa','auto'),application='on Apply')
add('theme',0,'Dashboard appearance','پوسته صفحه اصلی','Apex','choice',choices=('Dark','Light','Apex'),application='on Apply',description='Apex uses a black and deep-red background with blue accents. Light is neutral.')
add('settings_theme',0,'Settings appearance','ظاهر تنظیمات','Apex','choice',choices=('Apex','Dark','Light','System'),application='on Apply',description='Apex uses black and deep red with blue accents. This setting controls the Settings page.')
add('accent',0,'Accent color','رنگ تأکیدی','#4F8CFF','color',application='on Apply')
add('auto_connect_on_launch',1,'Automatically connect when app starts','اتصال خودکار هنگام اجرای برنامه',False,application='next launch',description='Opt-in: at launch, select a fresh verified server; never trust cached ping. Manual disconnect stops it.')
add('smart_connect',1,'Enable Smart Connect','انتخاب هوشمند سرور',False,description='Tries compatible candidates sequentially; success requires real HTTPS through that core. Favorites stay pinned.')
add('smart_policy',1,'Selection policy','سیاست انتخاب','Balanced','choice',choices=('Lowest latency','Highest stability','Balanced','Manual preferred'))
add('auto_reconnect',1,'Reconnect after unexpected loss','اتصال مجدد پس از قطع غیرمنتظره',False,description='Never retries a user-requested disconnect. Attempts are bounded until a stable session is established.')
add('retry_attempts',1,'Maximum retries','حداکثر تلاش مجدد',3,'int',minimum=1,maximum=8)
add('retry_delay',1,'Retry delay (seconds)','فاصله تلاش‌ها (ثانیه)',3,'int',minimum=1,maximum=60)
add('retry_backoff',1,'Exponential backoff','افزایش تصاعدی فاصله',True)
add('seamless',1,'Seamless switching','تعویض بدون وقفه',False,unavailable='The single-process Xray supervisor cannot validate a parallel replacement and migrate established TCP sessions safely.')
add('verify_https',1,'Verify HTTPS after connect','تأیید HTTPS پس از اتصال',True,unavailable='Mandatory security gate: a listener or TCP response cannot prove a working authenticated tunnel.')
add('http_url',1,'Optional HTTP verification URL','نشانی بررسی HTTP','http://www.gstatic.com/generate_204','url',advanced=True,export=False)
add('https_url',1,'Required HTTPS verification URL','نشانی بررسی ضروری HTTPS','https://www.gstatic.com/generate_204','url',advanced=True,export=False)
add('core',2,'Xray executable path','مسیر فایل اجرایی Xray',str(BASE/'core'/('xray.exe' if os.name=='nt' else 'xray')),'path',export=False)
add('auto_core',2,'Automatically select compatible core','انتخاب خودکار هسته سازگار',False,unavailable='Core selection follows the profile protocol automatically. This legacy switch does not load arbitrary engines.')
add('mode',3,'Connection mode','حالت اتصال','System Proxy' if os.name=='nt' else 'Manual Proxy','choice',choices=('Manual Proxy','System Proxy','Disabled'),permission='WinINET for System Proxy',description='Disabled refuses all new connections. System Proxy changes only current-user WinINET after HTTPS succeeds.')
add('proxy_recovery',3,'Durable proxy recovery','بازیابی پایدار پروکسی',True,unavailable='Always enforced for System Proxy: ownership lease, exact previous settings and crash guardian are required.')
for key,title,fa,value in [('http_port','HTTP listener port','پورت HTTP',2080),('socks_port','SOCKS listener port','پورت SOCKS',2081),('stats_port','Metrics listener port','پورت آمار',2082)]:add(key,3,title,fa,value,'int',minimum=1024,maximum=65535,advanced=True)
add('tun',3,'TUN and driver installation','TUN و نصب درایور',False,permission='administrator',unavailable='Missing audited TUN adapter, approved driver installer and crash-safe route recovery. No drivers or routes will be changed.')
add('app_split',4,'Application split tunneling','تفکیک ترافیک برنامه‌ها',False,unavailable='Use Settings 14 for local process direct exceptions. Full system TUN capture is unavailable.')
add('bypass',4,'Bypass private LAN addresses','عبور مستقیم شبکه محلی',False,description='Enforced by explicit private-IP Xray routes on the next connection. Verification endpoints are always forced through the selected proxy.')
add('domain_rules',4,'Per-domain routing and explicit DNS','قوانین دامنه و DNS اختصاصی',False,unavailable='Use Settings 14 for validated direct domain exceptions. Arbitrary DNS and routing scripts are unavailable.')
add('privacy_guard',5,'Continuous DNS / route leak guard','پایش پیوسته نشت DNS و مسیر',False,unavailable='HTTP proxying does not capture all operating-system DNS or IPv6 traffic. Manual proxy IP verification is available below.')
add('kill_switch',5,'Kill switch','قطع اضطراری اینترنت',False,permission='administrator',unavailable='No audited WFP/firewall transaction and crash-recovery implementation. Remains OFF; Windows security is never weakened.')
add('auto_recover_core',6,'Recover after core crash','بازیابی پس از خرابی هسته',False,description='Uses the same bounded retry budget as Auto Reconnect. Stops on manual disconnect and repeated failures.')
add('subscription_interval',7,'Automatic refresh','به‌روزرسانی خودکار','Manual','choice',choices=('Manual','6 hours','12 hours','Daily'),application='on Apply',description='Contacts saved providers through the active proxy when connected, including the active subscription; failures use backoff.')
add('monitor',9,'Adaptive connection monitoring','پایش تطبیقی اتصال',False,application='on Apply')
add('stable_interval',9,'Stable check interval (seconds)','فاصله پایش پایدار (ثانیه)',60,'int',minimum=30,maximum=3600,application='on Apply')
add('failure_interval',9,'Check interval after recovery (seconds)','فاصله پایش پس از بازیابی',15,'int',minimum=5,maximum=120,application='on Apply',advanced=True)
add('health_timeout',9,'HTTP / HTTPS timeout (seconds)','مهلت بررسی اتصال (ثانیه)',8,'int',minimum=2,maximum=30)
add('concurrency',9,'Maximum parallel server checks','حداکثر بررسی همزمان سرورها',4,'int',minimum=1,maximum=16,application='on Apply',advanced=True)
add('battery_reduce',9,'Reduce polling on battery','کاهش پایش با باتری',True,application='on Apply',unavailable='' if os.name=='nt' else 'Windows power status is unavailable on this operating system.')
add('load_reduce',9,'Reduce checks under heavy CPU load','کاهش پایش با بار پردازشی بالا',False,unavailable='No reliable Windows CPU-load sampler is installed. Health verification is never skipped on connect.')
add('lightweight',9,'Lightweight mode','حالت سبک',False,application='on Apply',description='Slower 4-second UI polling, one bulk check at a time and less frequent background health tests. Mandatory HTTPS remains enabled.')
add('tray_enabled',10,'Enable tray controls','فعال‌سازی سینی سیستم',True,application='on Apply')
add('tray_status',10,'Show connection state','نمایش وضعیت اتصال',True,application='on Apply')
add('tray_server',10,'Show current server','نمایش سرور فعلی',True,application='on Apply')
add('tray_speed',10,'Show measured transfer speed','نمایش سرعت اندازه‌گیری‌شده',False,application='on Apply')
add('tray_connect',10,'Connect / disconnect action','عمل اتصال و قطع',True,application='on Apply')
add('tray_profiles',10,'Choose profile from tray','انتخاب سرور در سینی',False,application='on Apply')
add('minimize_close',10,'Minimize instead of closing','کوچک‌شدن به‌جای بستن',False,application='on Apply',description='Only when a visible system tray is available. Quit in the tray still exits and restores the proxy.')
add('notifications',10,'Connection notifications','اعلان اتصال',True,application='on Apply')
add('text_scale',10,'Settings text scale (%)','اندازه متن تنظیمات (درصد)',100,'int',minimum=90,maximum=150,application='on Apply')
add('reduced_motion',10,'Reduced motion','کاهش حرکت',False,application='on Apply',description='Disables hover animation. Static depth remains available; no continuous animation timer runs.')
add('visual_effects',10,'Glass depth and shadows','عمق شیشه‌ای و سایه‌ها',True,application='on Apply',description='Preserves layout. Disabled automatically in lightweight / high-contrast modes.')
add('sound_enabled',10,'Interaction and connection sounds','صدای کلیک و اتصال',True,application='on Apply',description='Short, quiet local cues; available on Windows via asynchronous native playback.')
add('high_contrast',10,'High contrast in Settings','کنتراست بالا در تنظیمات',False,application='on Apply')
add('logging',12,'Sanitized application history','سطح تاریخچه پاک‌سازی‌شده','Error','choice',choices=('Off','Error','Warning','Info','Debug'),application='on Apply',description='Only fixed diagnostic messages are retained in memory. Raw core output, credentials and configuration URLs are never logged.')
add('direct_enabled',13,'Enable direct exceptions','فعال‌سازی استثناهای اتصال مستقیم',True,description='Selected destinations use your real connection and IP. .ir bypass is enabled by default. Save changes at any time, then reconnect to apply.')
add('direct_ir',13,'Connect .ir sites directly','اتصال مستقیم سایت‌های .ir',True,description='Matches .ir domains and subdomains. Does not include all Iranian IP addresses or sites hosted on other suffixes.')
add('direct_domains',13,'Other direct domains · one per line','دامنه‌های مستقیم دیگر · هر خط یک دامنه','','domains',description='Example: example.com or https://example.com/page. The domain and its subdomains connect directly. Reserved connectivity-check domains always use the proxy.')
add('direct_apps',13,'Direct applications · EXE paths or names','برنامه‌های مستقیم · مسیر یا نام EXE','','applications',export=False,description='Choose the actual network process, not just its launcher. Exact paths are preferred. Xray matches process names and paths case-sensitively. Failed process lookup leaves traffic on the proxy.')
SCHEMA={s.key:s for s in SPECS}

def defaults():return {s.key:copy.deepcopy(s.default) for s in SPECS}

def validate(values):
    result=defaults()
    for key,value in values.items():
        if key not in SCHEMA:continue
        s=SCHEMA[key]
        if s.kind=='bool':ok=type(value) is bool
        elif s.kind=='int':ok=type(value) is int and s.minimum<=value<=s.maximum
        elif s.kind=='choice':ok=value in s.choices
        else:ok=isinstance(value,str) and len(value)<=4096
        if not ok:raise ValueError('Invalid setting: '+key)
        if s.unavailable and value!=s.default:raise ValueError('Unavailable setting: '+key)
        if s.kind=='color' and not re.fullmatch(r'#[0-9a-fA-F]{6}',value):raise ValueError('Accent must be a six-digit hex color.')
        if s.kind=='url':
            u=urlsplit(value)
            if u.scheme!=('https' if key=='https_url' else 'http') or not u.hostname or u.username or u.password:raise ValueError('Health URLs must use the correct scheme and cannot contain credentials.')
        if s.kind in ('domains','applications'):
            from .direct_routing import domains, applications
            (domains if s.kind=='domains' else applications)(value)
        result[key]=value
    ports=[result[x] for x in ('http_port','socks_port','stats_port')]
    if len(set(ports))!=3:raise ValueError('HTTP, SOCKS and metrics ports must be different.')
    if result['start_tray'] and not result['tray_enabled']:raise ValueError('Starting in tray requires enabled tray controls.')
    if result['mode']=='System Proxy' and os.name!='nt':raise ValueError('System Proxy requires Windows.')
    return result

def migrate(raw):
    """Validate fields independently to recover legacy settings without discarding profiles."""
    result=defaults()
    for key in SCHEMA:
        if key not in raw:continue
        try:
            candidate=dict(result);candidate[key]=raw[key];validate(candidate);result[key]=raw[key]
        except (ValueError,TypeError):pass
    if raw.get('direct_defaults_version') != 1:
        result['direct_enabled'] = True
        result['direct_ir'] = True
    result['direct_defaults_version'] = 1
    version=raw.get('apex_theme_version',0)
    if type(version) is not int:version=0
    if version<1 and raw.get('theme','Light')=='Light':result['theme']='Apex'
    if version<3 and result.get('theme')=='Apex':result['settings_theme']='Apex'
    result['apex_theme_version']=3
    if type(raw.get('hardware_tuned')) is bool:result['hardware_tuned']=raw['hardware_tuned']
    disabled=raw.get('disabled_free_sources',[])
    allowed={'proxycollector','alirewa','patterniha','mahsa'}
    result['disabled_free_sources']=sorted({key for key in disabled if isinstance(key,str) and key in allowed}) if isinstance(disabled,list) else []
    # Legacy UI and profile identity remain private application metadata.
    for key in ('dashboard_design','selected','release_seen','selected_group'):
        if key in raw and isinstance(raw[key],str) and len(raw[key])<=256:result[key]=raw[key]
    window=raw.get('settings_window')
    if isinstance(window,list) and len(window)==2 and all(type(v) is int and 500<=v<=4000 for v in window):result['settings_window']=window
    compact=raw.get('shadow_window')
    if isinstance(compact,list) and len(compact)==2 and type(compact[0]) is int and type(compact[1]) is int and 396<=compact[0]<=4000 and 600<=compact[1]<=3000:result['shadow_window']=compact
    if type(raw.get('free_catalog_version')) is int:result['free_catalog_version']=raw['free_catalog_version']
    pins=raw.get('service_priority',[])
    if isinstance(pins,list):result['service_priority']=[x for x in pins if isinstance(x,str) and len(x)<40][:5]
    history=raw.get('reliability',{})
    if isinstance(history,dict):
        clean={}
        for ident,entry in list(history.items())[-2000:]:
            if not isinstance(ident,str) or len(ident)>128 or not isinstance(entry,dict):continue
            if any(type(entry.get(k,0)) is not int or not 0<=entry.get(k,0)<=10000 for k in ('success','failures')):continue
            latency=entry.get('latency');verified=entry.get('verified_at',0)
            if latency is not None and (type(latency) not in (int,float) or not 0<=latency<=300000):continue
            if type(verified) not in (int,float) or not 0<=verified<=1e12:continue
            clean[ident]={'success':entry.get('success',0),'failures':entry.get('failures',0),'latency':latency,'verified_at':verified}
        result['reliability']=clean
    result.setdefault('theme','Light');result['schema_version']=1
    return result

def export_preferences(values):
    return {'format':'nekoray-next-settings','version':1,'settings':{k:v for k,v in validate(values).items() if SCHEMA[k].export}}

def import_preferences(payload,current):
    if not isinstance(payload,dict) or payload.get('format')!='nekoray-next-settings' or payload.get('version')!=1 or not isinstance(payload.get('settings'),dict):raise ValueError('Unsupported settings file.')
    incoming=payload['settings']
    if any(k not in SCHEMA or not SCHEMA[k].export for k in incoming):raise ValueError('Import contains private or unknown fields.')
    candidate={k:current.get(k,s.default) for k,s in SCHEMA.items()};candidate.update(incoming)
    return validate(candidate)
