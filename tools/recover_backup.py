"""Explicitly decrypt your own migration backup to a new file. No system changes."""
import argparse,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from nextapp.storage import protect,atomic_write
p=argparse.ArgumentParser();p.add_argument('encrypted_backup',type=pathlib.Path);p.add_argument('output_zip',type=pathlib.Path);args=p.parse_args()
if args.output_zip.exists():raise SystemExit('Output already exists. Choose a new filename to avoid overwriting it.')
data=protect(args.encrypted_backup.read_bytes(),True)
if not data.startswith(b'PK'):raise SystemExit('Not a migration ZIP backup, or wrong account.')
atomic_write(args.output_zip,data);print('Recovered ZIP written. It contains secrets; keep it private.')
