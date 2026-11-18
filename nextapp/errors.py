"""Only fixed messages and numeric OS codes can leave this diagnostic boundary."""
import http.client, socket, ssl

MESSAGES={
 'TCP_REFUSED':'The selected server refused the TCP connection. Check its address/port or refresh the subscription; this is not a local-proxy success.',
 'DNS_FAILED':'Server DNS resolution failed. Check the network and server hostname.',
 'TIMEOUT':'The server or health endpoint did not respond before the timeout.',
 'TLS_FAILED':'TLS/REALITY handshake failed. Check SNI, certificate, fingerprint and server compatibility.',
 'AUTH_FAILED':'The core reported an authentication failure. Refresh the profile or check its credentials privately.',
 'PORT_CONFLICT':'A local port is already in use. Change the inbound ports in Settings.',
 'ENCRYPTION_UNSUPPORTED':'The core rejected an encryption/configuration feature. The original fields were preserved.',
 'CORE_EXIT':'Xray exited before a verified connection was established. Check configuration and dependency compatibility.',
 'PROXY_TUNNEL':'The local proxy could not establish the outbound tunnel. Check server reachability and profile compatibility.',
 'REMOTE_CLOSED':'The proxy/server closed the connection before a valid response. Check the server and transport settings.',
 'HTTP_STATUS':'The health endpoint returned a non-success status.',
 'DEPENDENCY_MISSING':'A required executable or dependency is missing. Check the selected Xray core.',
 'PERMISSION':'Windows or the OS denied access. Check the file permissions and security policy.',
}
class AppError(RuntimeError):
    def __init__(self,code,detail=None):
        self.code=code;self.detail=detail or MESSAGES.get(code,'Operation failed. Run diagnostics for the current stage.')
        super().__init__(f'[{code}] {self.detail}')

# Raw core output is classified and immediately discarded, never retained/exported.
def core_category(raw):
    text=raw.lower()
    rules=[('PORT_CONFLICT',('address already in use','only one usage of each socket','bind: permission denied')),
      ('AUTH_FAILED',('authentication failed','invalid user','invalid password','failed to authenticate')),
      ('ENCRYPTION_UNSUPPORTED',('unknown encryption','unsupported encryption','invalid encryption')),
      ('TLS_FAILED',('tls handshake','certificate verify','reality verification','invalid connection: authentication')),
      ('TCP_REFUSED',('connection refused','actively refused')),
      ('DNS_FAILED',('no such host','failed to lookup','name resolution failed')),
      ('TIMEOUT',('i/o timeout','context deadline exceeded'))]
    for code,words in rules:
        if any(word in text for word in words):return code
    return None

def exception_category(e):
    if isinstance(e,socket.gaierror):return 'DNS_FAILED'
    if isinstance(e,ConnectionRefusedError):return 'TCP_REFUSED'
    if isinstance(e,(TimeoutError,socket.timeout)):return 'TIMEOUT'
    if isinstance(e,ssl.SSLError):return 'TLS_FAILED'
    if isinstance(e,FileNotFoundError):return 'DEPENDENCY_MISSING'
    if isinstance(e,PermissionError):return 'PERMISSION'
    if isinstance(e,(http.client.RemoteDisconnected,ConnectionResetError,BrokenPipeError)):return 'REMOTE_CLOSED'
    if isinstance(e,(http.client.HTTPException,ConnectionError)):return 'PROXY_TUNNEL'
    if isinstance(e,OSError):
        if getattr(e,'winerror',None)==10061 or e.errno in (61,111,10061):return 'TCP_REFUSED'
        if getattr(e,'winerror',None)==10060:return 'TIMEOUT'
        # Never echo the OSError text: it may embed the requested URL or credentials.
        return 'PROXY_TUNNEL'
    return None
