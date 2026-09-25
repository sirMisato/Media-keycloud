#!/usr/bin/env python3
import base64, os, secrets
from pathlib import Path
root=Path(__file__).resolve().parents[1]
config=root/'.deploy';config.mkdir(mode=0o700,exist_ok=True)
os.chmod(config,0o700)
if any((config/f'{env}.env').exists() for env in ('prod','dev')):
    raise SystemExit('Konfigurasi sudah ada. Tidak menimpa kunci, password, atau database.')
image=os.environ.get('MEDIA_IMAGE','mahad-media:initial')
for env,domain,port in [('prod','media.keycloud.id',8081),('dev','media-dev.keycloud.id',8082)]:
    path=config/f'{env}.env'
    content=f'''APP_NAME="Ma’had Aly Situbondo"
APP_ENV={'production' if env=='prod' else 'staging'}
APP_DEBUG=false
APP_KEY=base64:{base64.b64encode(secrets.token_bytes(32)).decode()}
APP_URL=https://{domain}
APP_LOCALE=id
APP_FALLBACK_LOCALE=en
LOG_CHANNEL=stderr
LOG_LEVEL=warning
DB_CONNECTION=pgsql
DB_HOST=db
DB_PORT=5432
DB_DATABASE=media_{env}
DB_USERNAME=media_{env}
DB_PASSWORD={secrets.token_hex(32)}
SESSION_DRIVER=database
SESSION_COOKIE=mahad_{env}_session
SESSION_SECURE_COOKIE=true
SESSION_DOMAIN=null
CACHE_STORE=database
QUEUE_CONNECTION=database
FILESYSTEM_DISK=local
MEDIA_NOINDEX={'false' if env=='prod' else 'true'}
MEDIA_DEMO={'false' if env=='prod' else 'true'}
MAIL_MAILER=log
APP_IMAGE={image}
HTTP_PORT={port}
ENV_FILE={path}
'''
    with path.open('x') as file: file.write(content)
    os.chmod(path,0o600)
print('Konfigurasi prod/dev dibuat dengan kunci dan password berbeda.')
