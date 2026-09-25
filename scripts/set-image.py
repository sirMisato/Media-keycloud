#!/usr/bin/env python3
import re,sys
from pathlib import Path
if len(sys.argv)!=3 or sys.argv[1] not in ('prod','dev') or not re.fullmatch(r'mahad-media:[a-zA-Z0-9_.-]+',sys.argv[2]):
    raise SystemExit('Gunakan: set-image.py prod|dev mahad-media:TAG')
p=Path(__file__).resolve().parents[1]/'.deploy'/f'{sys.argv[1]}.env'
s=p.read_text();s,n=re.subn(r'^APP_IMAGE=.*$',f'APP_IMAGE={sys.argv[2]}',s,flags=re.M)
if n!=1: raise SystemExit('Konfigurasi APP_IMAGE tidak valid.')
p.write_text(s)
