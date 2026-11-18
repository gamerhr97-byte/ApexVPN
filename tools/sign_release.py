"""Sign built Windows executables using an existing trusted certificate store identity.

No certificates are generated or installed and no private key is exported.
Run on the Windows signing machine before packaging the release.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--signtool', required=True, type=Path)
    parser.add_argument('--thumbprint', required=True)
    parser.add_argument('--timestamp', required=True)
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('Signing requires Windows and an accessible trusted code-signing identity.')
    if not re.fullmatch(r'[0-9A-Fa-f]{40}', args.thumbprint):
        parser.error('Supply the certificate SHA-1 thumbprint; file signatures use SHA-256.')
    url = urlsplit(args.timestamp)
    if url.scheme != 'https' or not url.hostname or url.username or url.password:
        parser.error('Supply a credential-free HTTPS RFC3161 timestamp endpoint.')
    files = [Path(__file__).parent / name for name in ('ShadowBox.exe', 'ShadowBoxHost.exe')]
    if not args.signtool.is_file() or not all(path.is_file() for path in files):
        parser.error('Build the release first and select the installed Windows SDK signtool.exe.')
    for path in files:
        subprocess.run([str(args.signtool), 'sign', '/sha1', args.thumbprint,
                        '/fd', 'SHA256', '/tr', args.timestamp, '/td', 'SHA256',
                        '/d', 'Shadow Box', str(path)], check=True)
        subprocess.run([str(args.signtool), 'verify', '/pa', '/all', str(path)], check=True)


if __name__ == '__main__':
    main()
