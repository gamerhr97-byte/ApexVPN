"""Conservative HTTPS reachability checks using an explicit direct/proxy route.

These are website-level, unauthenticated probes, not tests of mobile apps,
accounts, IP reputation or streaming availability. Unknown != blocked.
"""

from dataclasses import dataclass
import concurrent.futures
import http.client
import ssl
import socket
import threading
import time
from urllib.parse import urlsplit
from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True)
class Service:
    key: str
    name: str
    url: str
    color: str
    glyph: str


SERVICES = (
    Service("youtube", "YouTube", "https://www.youtube.com/", "#EF4444", "play"),
    Service("gemini", "Gemini", "https://gemini.google.com/app", "#7899FF", "spark"),
    Service("chatgpt", "ChatGPT", "https://chatgpt.com/", "#10A37F", "chat"),
    Service("telegram", "Telegram", "https://web.telegram.org/", "#32A7DE", "plane"),
    Service("instagram", "Instagram", "https://www.instagram.com/", "#D85A9D", "camera"),
    Service("whatsapp", "WhatsApp", "https://web.whatsapp.com/", "#25B969", "phone"),
    Service("discord", "Discord", "https://discord.com/", "#7385EC", "game"),
    Service("netflix", "Netflix", "https://www.netflix.com/", "#E94A55", "N"),
    Service("spotify", "Spotify", "https://open.spotify.com/", "#30BE71", "waves"),
    Service("github", "GitHub", "https://github.com/", "#7F8EA9", "GH"),
    Service("google", "Google", "https://www.google.com/", "#4285F4", "G"),
    Service("drive", "Google Drive", "https://drive.google.com/", "#34A853", "D"),
    Service("microsoft", "Microsoft", "https://www.microsoft.com/", "#5B87B9", "M"),
    Service("reddit", "Reddit", "https://www.reddit.com/", "#FF4500", "R"),
    Service("wikipedia", "Wikipedia", "https://www.wikipedia.org/", "#7B8190", "W"),
    Service("stackoverflow", "Stack Overflow", "https://stackoverflow.com/", "#F48024", "SO"),
)


# Exactly 200 stable, credential-free public HTTPS probes.
SERVICES += (
    Service("site0", 'Google Flow', 'https://labs.google/fx/tools/flow/', "#6394DF", "globe"),
    Service("site1", 'Cloudflare', 'https://www.cloudflare.com/', "#6394DF", "globe"),
    Service("site2", 'Dota 2', 'https://www.dota2.com/', "#6394DF", "globe"),
    Service("site3", 'Steam', 'https://store.steampowered.com/', "#6394DF", "globe"),
    Service("site4", 'Claude', 'https://claude.ai/', "#6394DF", "globe"),
    Service("site5", 'Anthropic', 'https://www.anthropic.com/', "#6394DF", "globe"),
    Service("site6", 'OpenAI', 'https://openai.com/', "#6394DF", "globe"),
    Service("site7", 'Google AI Studio', 'https://aistudio.google.com/', "#6394DF", "globe"),
    Service("site8", 'Google Labs', 'https://labs.google/', "#6394DF", "globe"),
    Service("site9", 'Google Maps', 'https://maps.google.com/', "#6394DF", "globe"),
    Service("site10", 'Gmail', 'https://mail.google.com/', "#6394DF", "globe"),
    Service("site11", 'Google Photos', 'https://photos.google.com/', "#6394DF", "globe"),
    Service("site12", 'Google Docs', 'https://docs.google.com/', "#6394DF", "globe"),
    Service("site13", 'Google Sheets', 'https://sheets.google.com/', "#6394DF", "globe"),
    Service("site14", 'Google Slides', 'https://slides.google.com/', "#6394DF", "globe"),
    Service("site15", 'Google Calendar', 'https://calendar.google.com/', "#6394DF", "globe"),
    Service("site16", 'Google Meet', 'https://meet.google.com/', "#6394DF", "globe"),
    Service("site17", 'Google Translate', 'https://translate.google.com/', "#6394DF", "globe"),
    Service("site18", 'Google Play', 'https://play.google.com/', "#6394DF", "globe"),
    Service("site19", 'Google News', 'https://news.google.com/', "#6394DF", "globe"),
    Service("site20", 'Google Fonts', 'https://fonts.google.com/', "#6394DF", "globe"),
    Service("site21", 'Google Scholar', 'https://scholar.google.com/', "#6394DF", "globe"),
    Service("site22", 'Google Cloud', 'https://cloud.google.com/', "#6394DF", "globe"),
    Service("site23", 'Firebase', 'https://firebase.google.com/', "#6394DF", "globe"),
    Service("site24", 'Colab', 'https://colab.research.google.com/', "#6394DF", "globe"),
    Service("site25", 'Kaggle', 'https://www.kaggle.com/', "#6394DF", "globe"),
    Service("site26", 'Hugging Face', 'https://huggingface.co/', "#6394DF", "globe"),
    Service("site27", 'Perplexity', 'https://www.perplexity.ai/', "#6394DF", "globe"),
    Service("site28", 'Poe', 'https://poe.com/', "#6394DF", "globe"),
    Service("site29", 'Mistral', 'https://mistral.ai/', "#6394DF", "globe"),
    Service("site30", 'DeepSeek', 'https://www.deepseek.com/', "#6394DF", "globe"),
    Service("site31", 'Grok', 'https://grok.com/', "#6394DF", "globe"),
    Service("site32", 'Runway', 'https://runwayml.com/', "#6394DF", "globe"),
    Service("site33", 'Midjourney', 'https://www.midjourney.com/', "#6394DF", "globe"),
    Service("site34", 'Leonardo', 'https://leonardo.ai/', "#6394DF", "globe"),
    Service("site35", 'Ideogram', 'https://ideogram.ai/', "#6394DF", "globe"),
    Service("site36", 'Suno', 'https://suno.com/', "#6394DF", "globe"),
    Service("site37", 'ElevenLabs', 'https://elevenlabs.io/', "#6394DF", "globe"),
    Service("site38", 'Replicate', 'https://replicate.com/', "#6394DF", "globe"),
    Service("site39", 'Together AI', 'https://www.together.ai/', "#6394DF", "globe"),
    Service("site40", 'Groq', 'https://groq.com/', "#6394DF", "globe"),
    Service("site41", 'Cohere', 'https://cohere.com/', "#6394DF", "globe"),
    Service("site42", 'Cursor', 'https://cursor.com/', "#6394DF", "globe"),
    Service("site43", 'Windsurf', 'https://windsurf.com/', "#6394DF", "globe"),
    Service("site44", 'Replit', 'https://replit.com/', "#6394DF", "globe"),
    Service("site45", 'Bolt', 'https://bolt.new/', "#6394DF", "globe"),
    Service("site46", 'Lovable', 'https://lovable.dev/', "#6394DF", "globe"),
    Service("site47", 'v0', 'https://v0.dev/', "#6394DF", "globe"),
    Service("site48", 'NotebookLM', 'https://notebooklm.google.com/', "#6394DF", "globe"),
    Service("site49", 'Character AI', 'https://character.ai/', "#6394DF", "globe"),
    Service("site50", 'Meta AI', 'https://www.meta.ai/', "#6394DF", "globe"),
    Service("site51", 'Adobe Firefly', 'https://firefly.adobe.com/', "#6394DF", "globe"),
    Service("site52", 'Adobe', 'https://www.adobe.com/', "#6394DF", "globe"),
    Service("site53", 'Behance', 'https://www.behance.net/', "#6394DF", "globe"),
    Service("site54", 'Dribbble', 'https://dribbble.com/', "#6394DF", "globe"),
    Service("site55", 'Figma', 'https://www.figma.com/', "#6394DF", "globe"),
    Service("site56", 'Canva', 'https://www.canva.com/', "#6394DF", "globe"),
    Service("site57", 'Framer', 'https://www.framer.com/', "#6394DF", "globe"),
    Service("site58", 'Webflow', 'https://webflow.com/', "#6394DF", "globe"),
    Service("site59", 'Notion', 'https://www.notion.so/', "#6394DF", "globe"),
    Service("site60", 'Obsidian', 'https://obsidian.md/', "#6394DF", "globe"),
    Service("site61", 'Evernote', 'https://evernote.com/', "#6394DF", "globe"),
    Service("site62", 'Trello', 'https://trello.com/', "#6394DF", "globe"),
    Service("site63", 'Asana', 'https://asana.com/', "#6394DF", "globe"),
    Service("site64", 'Linear', 'https://linear.app/', "#6394DF", "globe"),
    Service("site65", 'ClickUp', 'https://clickup.com/', "#6394DF", "globe"),
    Service("site66", 'Monday', 'https://monday.com/', "#6394DF", "globe"),
    Service("site67", 'Airtable', 'https://airtable.com/', "#6394DF", "globe"),
    Service("site68", 'Miro', 'https://miro.com/', "#6394DF", "globe"),
    Service("site69", 'Slack', 'https://slack.com/', "#6394DF", "globe"),
    Service("site70", 'Zoom', 'https://zoom.us/', "#6394DF", "globe"),
    Service("site71", 'Microsoft Teams', 'https://teams.microsoft.com/', "#6394DF", "globe"),
    Service("site72", 'Outlook', 'https://outlook.live.com/', "#6394DF", "globe"),
    Service("site73", 'OneDrive', 'https://onedrive.live.com/', "#6394DF", "globe"),
    Service("site74", 'Microsoft 365', 'https://www.office.com/', "#6394DF", "globe"),
    Service("site75", 'Copilot', 'https://copilot.microsoft.com/', "#6394DF", "globe"),
    Service("site76", 'Bing', 'https://www.bing.com/', "#6394DF", "globe"),
    Service("site77", 'DuckDuckGo', 'https://duckduckgo.com/', "#6394DF", "globe"),
    Service("site78", 'Brave Search', 'https://search.brave.com/', "#6394DF", "globe"),
    Service("site79", 'Yahoo', 'https://www.yahoo.com/', "#6394DF", "globe"),
    Service("site80", 'Proton', 'https://proton.me/', "#6394DF", "globe"),
    Service("site81", 'Tuta', 'https://tuta.com/', "#6394DF", "globe"),
    Service("site82", 'Fastmail', 'https://www.fastmail.com/', "#6394DF", "globe"),
    Service("site83", 'Dropbox', 'https://www.dropbox.com/', "#6394DF", "globe"),
    Service("site84", 'Box', 'https://www.box.com/', "#6394DF", "globe"),
    Service("site85", 'WeTransfer', 'https://wetransfer.com/', "#6394DF", "globe"),
    Service("site86", 'MEGA', 'https://mega.nz/', "#6394DF", "globe"),
    Service("site87", 'iCloud', 'https://www.icloud.com/', "#6394DF", "globe"),
    Service("site88", 'Apple', 'https://www.apple.com/', "#6394DF", "globe"),
    Service("site89", 'X', 'https://x.com/', "#6394DF", "globe"),
    Service("site90", 'Facebook', 'https://www.facebook.com/', "#6394DF", "globe"),
    Service("site91", 'Threads', 'https://www.threads.net/', "#6394DF", "globe"),
    Service("site92", 'TikTok', 'https://www.tiktok.com/', "#6394DF", "globe"),
    Service("site93", 'Snapchat', 'https://www.snapchat.com/', "#6394DF", "globe"),
    Service("site94", 'Pinterest', 'https://www.pinterest.com/', "#6394DF", "globe"),
    Service("site95", 'LinkedIn', 'https://www.linkedin.com/', "#6394DF", "globe"),
    Service("site96", 'Tumblr', 'https://www.tumblr.com/', "#6394DF", "globe"),
    Service("site97", 'Bluesky', 'https://bsky.app/', "#6394DF", "globe"),
    Service("site98", 'Mastodon', 'https://mastodon.social/', "#6394DF", "globe"),
    Service("site99", 'Signal', 'https://signal.org/', "#6394DF", "globe"),
    Service("site100", 'Messenger', 'https://www.messenger.com/', "#6394DF", "globe"),
    Service("site101", 'Viber', 'https://www.viber.com/', "#6394DF", "globe"),
    Service("site102", 'LINE', 'https://line.me/', "#6394DF", "globe"),
    Service("site103", 'Twitch', 'https://www.twitch.tv/', "#6394DF", "globe"),
    Service("site104", 'Kick', 'https://kick.com/', "#6394DF", "globe"),
    Service("site105", 'Vimeo', 'https://vimeo.com/', "#6394DF", "globe"),
    Service("site106", 'Dailymotion', 'https://www.dailymotion.com/', "#6394DF", "globe"),
    Service("site107", 'YouTube Music', 'https://music.youtube.com/', "#6394DF", "globe"),
    Service("site108", 'SoundCloud', 'https://soundcloud.com/', "#6394DF", "globe"),
    Service("site109", 'Bandcamp', 'https://bandcamp.com/', "#6394DF", "globe"),
    Service("site110", 'Deezer', 'https://www.deezer.com/', "#6394DF", "globe"),
    Service("site111", 'Tidal', 'https://tidal.com/', "#6394DF", "globe"),
    Service("site112", 'Apple Music', 'https://music.apple.com/', "#6394DF", "globe"),
    Service("site113", 'Last.fm', 'https://www.last.fm/', "#6394DF", "globe"),
    Service("site114", 'IMDb', 'https://www.imdb.com/', "#6394DF", "globe"),
    Service("site115", 'Letterboxd', 'https://letterboxd.com/', "#6394DF", "globe"),
    Service("site116", 'Disney Plus', 'https://www.disneyplus.com/', "#6394DF", "globe"),
    Service("site117", 'Prime Video', 'https://www.primevideo.com/', "#6394DF", "globe"),
    Service("site118", 'Hulu', 'https://www.hulu.com/', "#6394DF", "globe"),
    Service("site119", 'Crunchyroll', 'https://www.crunchyroll.com/', "#6394DF", "globe"),
    Service("site120", 'Plex', 'https://www.plex.tv/', "#6394DF", "globe"),
    Service("site121", 'Epic Games', 'https://store.epicgames.com/', "#6394DF", "globe"),
    Service("site122", 'GOG', 'https://www.gog.com/', "#6394DF", "globe"),
    Service("site123", 'EA', 'https://www.ea.com/', "#6394DF", "globe"),
    Service("site124", 'Ubisoft', 'https://www.ubisoft.com/', "#6394DF", "globe"),
    Service("site125", 'Battle.net', 'https://www.battle.net/', "#6394DF", "globe"),
    Service("site126", 'Riot Games', 'https://www.riotgames.com/', "#6394DF", "globe"),
    Service("site127", 'Valorant', 'https://playvalorant.com/', "#6394DF", "globe"),
    Service("site128", 'League of Legends', 'https://www.leagueoflegends.com/', "#6394DF", "globe"),
    Service("site129", 'Counter-Strike', 'https://www.counter-strike.net/', "#6394DF", "globe"),
    Service("site130", 'Fortnite', 'https://www.fortnite.com/', "#6394DF", "globe"),
    Service("site131", 'Minecraft', 'https://www.minecraft.net/', "#6394DF", "globe"),
    Service("site132", 'Roblox', 'https://www.roblox.com/', "#6394DF", "globe"),
    Service("site133", 'Xbox', 'https://www.xbox.com/', "#6394DF", "globe"),
    Service("site134", 'PlayStation', 'https://www.playstation.com/', "#6394DF", "globe"),
    Service("site135", 'Nintendo', 'https://www.nintendo.com/', "#6394DF", "globe"),
    Service("site136", 'FACEIT', 'https://www.faceit.com/', "#6394DF", "globe"),
    Service("site137", 'HLTV', 'https://www.hltv.org/', "#6394DF", "globe"),
    Service("site138", 'Liquipedia', 'https://liquipedia.net/', "#6394DF", "globe"),
    Service("site139", 'Chess.com', 'https://www.chess.com/', "#6394DF", "globe"),
    Service("site140", 'Lichess', 'https://lichess.org/', "#6394DF", "globe"),
    Service("site141", 'itch.io', 'https://itch.io/', "#6394DF", "globe"),
    Service("site142", 'Mod DB', 'https://www.moddb.com/', "#6394DF", "globe"),
    Service("site143", 'Nexus Mods', 'https://www.nexusmods.com/', "#6394DF", "globe"),
    Service("site144", 'GitLab', 'https://gitlab.com/', "#6394DF", "globe"),
    Service("site145", 'Bitbucket', 'https://bitbucket.org/', "#6394DF", "globe"),
    Service("site146", 'Codeberg', 'https://codeberg.org/', "#6394DF", "globe"),
    Service("site147", 'SourceForge', 'https://sourceforge.net/', "#6394DF", "globe"),
    Service("site148", 'npm', 'https://www.npmjs.com/', "#6394DF", "globe"),
    Service("site149", 'PyPI', 'https://pypi.org/', "#6394DF", "globe"),
    Service("site150", 'Docker Hub', 'https://hub.docker.com/', "#6394DF", "globe"),
    Service("site151", 'Vercel', 'https://vercel.com/', "#6394DF", "globe"),
    Service("site152", 'Netlify', 'https://www.netlify.com/', "#6394DF", "globe"),
    Service("site153", 'Render', 'https://render.com/', "#6394DF", "globe"),
    Service("site154", 'Railway', 'https://railway.com/', "#6394DF", "globe"),
    Service("site155", 'DigitalOcean', 'https://www.digitalocean.com/', "#6394DF", "globe"),
    Service("site156", 'AWS', 'https://aws.amazon.com/', "#6394DF", "globe"),
    Service("site157", 'Azure', 'https://azure.microsoft.com/', "#6394DF", "globe"),
    Service("site158", 'Hetzner', 'https://www.hetzner.com/', "#6394DF", "globe"),
    Service("site159", 'OVHcloud', 'https://www.ovhcloud.com/', "#6394DF", "globe"),
    Service("site160", 'Vultr', 'https://www.vultr.com/', "#6394DF", "globe"),
    Service("site161", 'Linode', 'https://www.linode.com/', "#6394DF", "globe"),
    Service("site162", 'Oracle Cloud', 'https://www.oracle.com/', "#6394DF", "globe"),
    Service("site163", 'Python', 'https://www.python.org/', "#6394DF", "globe"),
    Service("site164", 'Rust', 'https://www.rust-lang.org/', "#6394DF", "globe"),
    Service("site165", 'Go', 'https://go.dev/', "#6394DF", "globe"),
    Service("site166", 'Node.js', 'https://nodejs.org/', "#6394DF", "globe"),
    Service("site167", 'MDN', 'https://developer.mozilla.org/', "#6394DF", "globe"),
    Service("site168", 'W3Schools', 'https://www.w3schools.com/', "#6394DF", "globe"),
    Service("site169", 'freeCodeCamp', 'https://www.freecodecamp.org/', "#6394DF", "globe"),
    Service("site170", 'Coursera', 'https://www.coursera.org/', "#6394DF", "globe"),
    Service("site171", 'edX', 'https://www.edx.org/', "#6394DF", "globe"),
    Service("site172", 'Udemy', 'https://www.udemy.com/', "#6394DF", "globe"),
    Service("site173", 'Khan Academy', 'https://www.khanacademy.org/', "#6394DF", "globe"),
    Service("site174", 'Duolingo', 'https://www.duolingo.com/', "#6394DF", "globe"),
    Service("site175", 'arXiv', 'https://arxiv.org/', "#6394DF", "globe"),
    Service("site176", 'ResearchGate', 'https://www.researchgate.net/', "#6394DF", "globe"),
    Service("site177", 'Semantic Scholar', 'https://www.semanticscholar.org/', "#6394DF", "globe"),
    Service("site178", 'Internet Archive', 'https://archive.org/', "#6394DF", "globe"),
    Service("site179", 'Medium', 'https://medium.com/', "#6394DF", "globe"),
    Service("site180", 'Substack', 'https://substack.com/', "#6394DF", "globe"),
    Service("site181", 'WordPress', 'https://wordpress.com/', "#6394DF", "globe"),
    Service("site182", 'Blogger', 'https://www.blogger.com/', "#6394DF", "globe"),
    Service("site183", "Firestorm", "https://firestorm-servers.com/", "#EF9050", "game"),
)


ICON_CATALOG = SERVICES
# Five HTTPS defaults, plus 95 lightweight CONNECT destinations.
_DEFAULT_KEYS = ("youtube", "gemini", "chatgpt", "telegram", "google")
_REQUIRED_KEYS = ("site0", "site1", "site2", "site183")
_by_key = {s.key: s for s in ICON_CATALOG}
_order = list(dict.fromkeys(_DEFAULT_KEYS + _REQUIRED_KEYS + tuple(_by_key)))
SERVICES = tuple(_by_key[k] for k in _order[:100])


def priority_keys(settings):
    values = settings.get("service_priority", list(_DEFAULT_KEYS))
    keys = [k for k in values if k in {s.key for s in SERVICES}]
    return tuple(dict.fromkeys(keys + list(_DEFAULT_KEYS)))[:5]


def connect_service(service, port=None, timeout=1.5):
    """TCP handshake or HTTP CONNECT only: no page/TLS download, no ping claim."""
    host = urlsplit(service.url).hostname
    conn = None
    try:
        if port is None:
            with socket.create_connection((host,443), timeout):
                pass
        else:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
            conn.set_tunnel(host,443)
            conn.connect()
        return ServiceResult(service.key,"ok",reason="TCP/CONNECT reachable · HTTPS access not checked")
    except (OSError, http.client.HTTPException):
        return ServiceResult(service.key,"unknown",reason="Connection not confirmed")
    finally:
        if conn is not None:
            conn.close()


@dataclass(frozen=True)
class ServiceResult:
    key: str
    state: str
    latency: float | None = None
    status: int | None = None
    reason: str = ""
    region: str = "unknown"  # blocked / not_observed / unknown; never guarantees access


def classify_status(service, status, body=b""):
    """HTTP statuses are not a yes/no verdict about an account or application."""
    if service.key == "gemini":
        lower = body.lower()
        markers = (b"not available in your country", b"not available in your region",
                   b"not supported in your country", b"country is not supported",
                   b"gemini isn't currently supported in your country")
        if any(marker in lower for marker in markers):
            return "limited", "Explicit country restriction on public page", "blocked"
    if 200 <= status < 300:
        return "ok", "Public HTTPS page responded; app/account not verified", (
            "not_observed" if service.key == "gemini" and body else "unknown"
        )
    if status in (401, 403, 407):
        return "limited", "Authentication, anti-bot or region restriction possible", "unknown"
    if status == 429:
        return "limited", "Rate limited; not evidence of a blocked service", "unknown"
    if 300 <= status < 400:
        return "limited", "Redirect not followed; access undecided", "unknown"
    if 400 <= status < 500:
        return "limited", "Requested page or probe method was rejected; app status uncertain", "unknown"
    if 500 <= status < 600:
        return "limited", "Remote service temporarily unavailable", "unknown"
    return "unknown", "Unexpected HTTP status; application access unconfirmed", "unknown"


def probe_service(service, port=None, timeout=4):
    """Use local CONNECT proxy when a live proxy port is supplied; otherwise direct.

    Strict TLS; no redirected requests, login, cookies, or credentials. A timeout
    applies per network operation, so measured time is HTTPS request latency, not ICMP.
    """
    target = urlsplit(service.url)
    if target.scheme != "https" or not target.hostname or target.username or target.password:
        raise ValueError("Service endpoint must be credential-free HTTPS.")
    started = time.monotonic()

    def request(method):
        if port is None:
            conn = http.client.HTTPSConnection(
                target.hostname, target.port or 443, timeout=timeout,
                context=ssl.create_default_context()
            )
        else:
            conn = http.client.HTTPSConnection(
                "127.0.0.1", port, timeout=timeout, context=ssl.create_default_context()
            )
            conn.set_tunnel(target.hostname, target.port or 443)
        try:
            path = (target.path or "/") + ("?" + target.query if target.query else "")
            conn.request(method, path, headers={
                "User-Agent": "ApexVPN/0.10.4 ConnectivityCheck",
                "Connection": "close", "Range": "bytes=0-0" if method == "HEAD" else "bytes=0-32767",
            })
            response = conn.getresponse()
            body = response.read(32768) if service.key == "gemini" and method == "GET" else b""
            return response.status, body
        finally:
            conn.close()

    try:
        # Gemini's public country-restriction page requires a bounded GET.
        status, body = request("GET" if service.key == "gemini" else "HEAD")
        if status in (405, 501) and service.key != "gemini":
            status, body = request("GET")
        state, reason, region = classify_status(service, status, body)
        return ServiceResult(service.key, state, (time.monotonic()-started)*1000,
                             status, reason, region)
    except (TimeoutError, socket.timeout):
        return ServiceResult(service.key, "unknown", reason="Timed out; retry later")
    except ssl.SSLError:
        return ServiceResult(service.key, "failed", reason="TLS verification failed")
    except (OSError, http.client.HTTPException):
        return ServiceResult(service.key, "unknown", reason="Network request failed; access undecided")



class ServiceChecks(QObject):
    result = Signal(object)

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.generation = 0
        self.cancel_event = threading.Event()
        self.closed = False
        self.last_results = {}
        self.futures = []
        self.flush_pending = False
        self.route = "direct"
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=8, thread_name_prefix="service-check"
        )
        self.result.connect(self.deliver)

    def cancel(self):
        self.generation += 1
        self.cancel_event.set()
        self.last_results.clear()
        for future in self.futures:
            future.cancel()
        self.futures = []
        for tile in getattr(self.owner, "service_buttons", {}).values():
            tile.set_result(None)

    def start(self, reset=False):
        self.cancel()
        if self.closed or not self.owner.settings.get("service_checks", True):
            return
        self.route = "proxy" if self.owner.engine.running else "direct"
        port = self.owner.engine.settings["http_port"] if self.route == "proxy" else None
        process = self.owner.engine.process if port is not None else None
        self.cancel_event = threading.Event()
        cancel = self.cancel_event
        generation = self.generation
        profile = next((p for p in self.owner.profiles if p.id == self.owner.active_id),None) if port is not None else None
        if profile and reset:
            profile.service_cache.clear()
            profile.service_score=None
            profile.gemini_ok=False
            self.owner.store.save_profiles(self.owner.profiles)
            self.owner.populate()
        elif profile:
            for key,data in profile.service_cache.items():
                try:
                    self.last_results[key]=ServiceResult(key,**data)
                except (TypeError,ValueError):
                    pass
        for service in SERVICES:
            if service.key in self.last_results and service.key not in priority_keys(self.owner.settings):
                self.owner.service_buttons[service.key].set_result(self.last_results[service.key])
                continue
            self.owner.service_buttons[service.key].set_pending()
            self.futures.append(self.executor.submit(
                self.work, service, port, cancel, generation, process, self.route
            ))

    def work(self, service, port, cancel, generation, process, route, force_ping=False):
        if cancel.is_set():
            return
        value = probe_service(service, port) if force_ping or service.key in priority_keys(self.owner.settings) else connect_service(service, port)
        if not cancel.is_set() and not self.closed:
            self.result.emit((generation, process, route, value))

    def deliver(self, payload):
        # Two-argument legacy fixture compatibility while avoiding stale cross-route results.
        if len(payload) == 3:
            generation, process, value = payload
            route = "proxy" if self.owner.engine.running else "direct"
        else:
            generation, process, route, value = payload
        if (generation != self.generation or self.closed or route != self.route
                or (self.owner.engine.running != (route == "proxy"))
                or (route == "proxy" and process is not self.owner.engine.process)
                or (route == "direct" and process is not None)):
            return
        self.last_results[value.key] = value
        if value.key in self.owner.service_buttons:
            self.owner.service_buttons[value.key].set_result(value)
        if route == "proxy" and self.owner.active_id:
            p=next((x for x in self.owner.profiles if x.id == self.owner.active_id),None)
            if p:
                from dataclasses import asdict
                data=asdict(value);data.pop("key")
                p.service_cache[value.key]=data
                if value.key == "gemini" and value.state == "ok" and value.region == "not_observed":
                    p.gemini_ok=True
                if len(self.last_results) == len(SERVICES):
                    p.service_score=sum(v.state == "ok" for v in self.last_results.values())
                if not self.flush_pending:
                    from PySide6.QtCore import QTimer
                    self.flush_pending=True
                    QTimer.singleShot(500,self.flush)

    def flush(self):
        self.flush_pending=False
        if not self.closed:
            self.owner.store.save_profiles(self.owner.profiles)
            self.owner.populate()

    def ping_one(self, key):
        service = next((s for s in SERVICES if s.key == key), None)
        if not service or self.closed:
            return
        proxy = self.owner.engine.running
        self.route = "proxy" if proxy else "direct"
        port = self.owner.engine.settings["http_port"] if proxy else None
        process = self.owner.engine.process if proxy else None
        self.futures.append(self.executor.submit(self.work, service, port,
            self.cancel_event, self.generation, process, self.route, True))
        self.owner.notice("در حال بررسی…" if self.owner.t("Settings") == "تنظیمات" else "Checking…")

    def pin(self, key):
        keys = [key] + [k for k in priority_keys(self.owner.settings) if k != key]
        self.owner.settings["service_priority"] = keys[:5]
        self.owner.store.save_settings(self.owner.settings)
        self.ping_one(key)

    def show_details(self):
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
            QPushButton, QScrollArea, QWidget, QGridLayout, QMenu)
        from PySide6.QtCore import Qt, QTimer, QSize
        from .service_icons import service_icon
        fa = self.owner.t("Settings") == "تنظیمات"
        d = QDialog(self.owner)
        d.setWindowTitle("سرویس‌ها" if fa else "Services")
        d.setLayoutDirection(Qt.LeftToRight)
        d.setFixedSize(390, min(550, self.owner.height()-40))
        lay = QVBoxLayout(d)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setFrameShape(QScrollArea.NoFrame)
        accent = self.owner.settings.get("accent", "#4F8CFF")
        area.verticalScrollBar().setStyleSheet(f"""
            QScrollBar:vertical {{ background:transparent; width:10px; margin:3px 1px; }}
            QScrollBar::handle:vertical {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {accent},stop:1 rgba(110,130,190,150)); border-radius:5px; min-height:28px; }}
            QScrollBar::handle:vertical:hover {{ background:{accent}; min-height:36px; }}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{ height:0; }}
            QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {{ background:transparent; }}
        """)
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(2,2,2,2)
        grid.setSpacing(7)
        buttons = {}
        def menu(key, btn, point):
            m = QMenu(d)
            m.addAction("پینگ" if fa else "Ping", lambda: self.ping_one(key))
            m.addAction("انتقال به ۵ سرویس اول" if fa else "Pin to first five", lambda: self.pin(key))
            m.exec(btn.mapToGlobal(point))
        for service in SERVICES:
            btn = QPushButton()
            btn.setFixedSize(59, 51)
            btn.setIconSize(QSize(32,32))
            btn.setAccessibleName(service.name)
            btn.clicked.connect(lambda checked=False, key=service.key: self.ping_one(key))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pt,key=service.key,b=btn:menu(key,b,pt))
            buttons[service.key] = btn
        area.setWidget(grid_widget)
        lay.addWidget(area, 1)
        arranged = []
        def update_rows():
            nonlocal arranged
            keys = priority_keys(self.owner.settings)
            ordered = sorted(SERVICES, key=lambda s: (keys.index(s.key) if s.key in keys else 5, list(SERVICES).index(s)))
            visible = ordered
            ids = [s.key for s in visible]
            if ids != arranged:
                for btn in buttons.values():grid.removeWidget(btn);btn.hide()
                for i,service in enumerate(visible):
                    btn=buttons[service.key];grid.addWidget(btn,i//5,i%5);btn.show()
                arranged=ids
            for service in SERVICES:
                btn=buttons[service.key]
                result=self.last_results.get(service.key)
                ok=bool(result and result.state == "ok")
                failed=bool(result and result.state != "ok")
                btn.setIcon(service_icon(service.key,service.color))
                theme=self.owner.settings.get("theme", "Apex")
                if ok:
                    tile_bg = "rgba(22,145,99,46)" if theme != "Light" else "rgba(22,145,99,30)"
                    tile_hover = "rgba(22,175,116,88)"
                elif failed:
                    tile_bg = "rgba(226,63,76,52)" if theme != "Light" else "rgba(226,63,76,34)"
                    tile_hover = "rgba(245,75,88,92)"
                else:
                    tile_bg = "rgba(95,115,150,20)" if theme != "Light" else "rgba(90,110,145,16)"
                    tile_hover = "rgba(90,130,205,48)"
                btn.setStyleSheet(f"QPushButton{{padding:3px;border:0;border-radius:10px;background:{tile_bg};}} QPushButton:hover{{background:{tile_hover};}} QPushButton:pressed{{background:{accent};}}")
                detail=(result.reason if result and result.state != "ok" else
                        f"{result.latency:.0f} ms HTTPS" if result and result.latency is not None else
                        ("اتصال برقرار؛ پینگ بگیرید" if fa else "Connected · click to ping") if ok else
                        ("تأیید نشده" if fa else "Unconfirmed"))
                btn.setToolTip(service.name + " · " + detail)
        timer=QTimer(d);timer.setInterval(500);timer.timeout.connect(update_rows);timer.start()
        update_rows()
        note=QLabel("کلیک: پینگ · راست‌کلیک: سنجاق" if fa else "Click: ping · Right-click: pin")
        lay.addWidget(note)
        actions=QHBoxLayout()
        again=QPushButton("تازه‌سازی" if fa else "Refresh")
        again.clicked.connect(lambda: self.start(reset=True))
        close=QPushButton("بستن" if fa else "Close");close.clicked.connect(d.accept)
        actions.addWidget(again);actions.addWidget(close);lay.addLayout(actions)
        d.exec()

    def restore_widgets(self):
        for key, result in self.last_results.items():
            if key in self.owner.service_buttons:
                self.owner.service_buttons[key].set_result(result)

    def shutdown(self):
        if self.flush_pending:
            self.owner.store.save_profiles(self.owner.profiles)
            self.flush_pending=False
        self.closed = True
        self.cancel()
        self.executor.shutdown(wait=False, cancel_futures=True)


def measure_quality(port, cancel, settings=None):
    """Optional exhaustive score through one isolated verified tunnel.

    Results belong to this test only. Cancellation does not award partial stars.
    No geography whitelist is used as a substitute for observing Gemini.
    """
    score = 0
    gemini = False
    iterator = iter(SERVICES[:100])
    server_workers = 1 if (settings or {}).get('lightweight') else max(1,min(8,int((settings or {}).get('concurrency',4))))
    workers = max(12,min(48,256//server_workers))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {}
        def launch():
            if cancel.is_set():
                return
            service = next(iterator, None)
            if service:
                probe = probe_service if service.key in priority_keys(settings or {}) else connect_service
                pending[pool.submit(probe, service, port, 2)] = service
        for _ in range(workers):
            launch()
        while pending:
            done, _ = concurrent.futures.wait(pending, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                service = pending.pop(future)
                try:
                    result = future.result()
                    score += result.state == "ok"
                    if service.key == "gemini":
                        gemini = result.state == "ok" and result.region == "not_observed"
                except Exception:
                    pass
                launch()
    return (None, False) if cancel.is_set() else (score, gemini)
