import http.client,socket
from nextapp.engine import safe_error
from nextapp.errors import AppError,core_category

def test_error_classification_does_not_export_server_credentials():
    secret='https://secret-uuid@private-server/token'
    for exc in [ConnectionRefusedError(secret),OSError(secret),http.client.RemoteDisconnected(secret),socket.gaierror(secret),RuntimeError(secret)]:
        assert secret not in safe_error(exc)
        assert '[' in safe_error(exc)
    assert 'TCP_REFUSED' in safe_error(ConnectionRefusedError(secret))
    assert 'REMOTE_CLOSED' in safe_error(http.client.RemoteDisconnected(secret))

def test_raw_core_lines_only_become_fixed_codes():
    assert core_category('failed to dial private-host:443: connection refused; token=private')=='TCP_REFUSED'
    assert core_category('password=private authentication failed')=='AUTH_FAILED'
    assert core_category('unknown encryption private-value')=='ENCRYPTION_UNSUPPORTED'
    assert core_category('normal startup') is None
    assert 'authentication' in safe_error(AppError('AUTH_FAILED')).lower()
