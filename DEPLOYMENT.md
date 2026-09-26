# LalahariHealth deployment

These instructions deploy the Next.js site at `lalaharihealth.com` and the Django API at `api.lalaharihealth.com` alongside existing Nginx sites. They use independent systemd services, an API Unix socket, and frontend port `127.0.0.1:3001`; they do not edit or restart existing application services.

The application runs under its own `lalahari` system user in `/srv/lalaharihealth`. This deliberately avoids altering the users, services, Node.js versions, or directories of existing sites.

## Prerequisites

Create DNS `A` records for `lalaharihealth.com` and `api.lalaharihealth.com` pointing to the server's public IPv4 address. Wait until both resolve before issuing certificates.

The existing Algolog PostgreSQL database and its superuser credentials must not be reused. LalahariHealth uses its own `lalaharihealth_db` database and a role limited to that database.

This repository pins Django 6.1, which requires Python 3.12 or newer. Next.js 16 requires Node.js 20.9 or newer. Install Node 20 only for the new `lalahari` user; do not install the Ubuntu `npm` package or replace the host-wide Node version used by existing websites:

```bash
sudo adduser --system --group --home /srv/lalahari --shell /bin/bash lalahari
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo -u lalahari -H bash -lc 'curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash'
sudo -u lalahari -H bash -lc 'source /srv/lalahari/.nvm/nvm.sh && nvm install 20 && nvm alias default 20 && node --version && npm --version'
python3.12 --version
sudo nginx -t
```

## PostgreSQL database

Run the following as `root`. At the PostgreSQL prompt, choose a new long password for `lalaharihealth_user`; do not use or place the password of any existing application in this repository. The existing PostgreSQL server can remain shared because this creates a separate database and role.

```bash
sudo -u postgres psql
```

```sql
CREATE ROLE lalaharihealth_user LOGIN PASSWORD 'replace-with-a-new-unique-password';
CREATE DATABASE lalaharihealth_db OWNER lalaharihealth_user ENCODING 'UTF8';
\\q
```

Use the same new password as `DB_PASSWORD` in the LalahariHealth backend `.env` file. PostgreSQL listens only on `127.0.0.1`, so no database port needs to be opened in the firewall.

## Application install

Run these commands after SSHing into the server. Replace the Git URL with the repository URL. If the source is uploaded with SFTP instead, upload it to `/srv/lalaharihealth`, then set its ownership with `sudo chown -R lalahari:lalahari /srv/lalaharihealth` and start at the virtual-environment command.

```bash
sudo -u lalahari -H git clone <YOUR_GIT_REPOSITORY_URL> /srv/lalaharihealth
sudo -iu lalahari
cd /srv/lalaharihealth/backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp ../deploy/backend.env.example .env
nano .env
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```

Set a real random `SECRET_KEY` in `.env`; this command prints one:

```bash
python3.12 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Build the frontend only after creating its production environment file, because `NEXT_PUBLIC_API_BASE_URL` is embedded during the Next.js build:

```bash
cd /srv/lalaharihealth/frontend
cp ../deploy/frontend.env.production.example .env.production
npm ci
npm run build
```

## systemd services

Install the two new unit files. They do not replace any existing `gunicorn-*` or Node service.

```bash
exit
sudo cp /srv/lalaharihealth/deploy/lalaharihealth-api.service /etc/systemd/system/
sudo cp /srv/lalaharihealth/deploy/lalaharihealth-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lalaharihealth-api lalaharihealth-web
sudo systemctl status lalaharihealth-api lalaharihealth-web --no-pager
curl --fail http://127.0.0.1:3001/
```

## Nginx and HTTPS

Copy only the new site configuration, validate the whole Nginx configuration, then reload it. A reload preserves the running configuration for all other validated sites.

```bash
sudo install -d -m 0755 /var/www/certbot
sudo cp /srv/lalaharihealth/deploy/nginx-lalaharihealth.conf /etc/nginx/sites-available/lalaharihealth
sudo ln -s /etc/nginx/sites-available/lalaharihealth /etc/nginx/sites-enabled/lalaharihealth
sudo nginx -t
sudo systemctl reload nginx
curl --fail -H "Host: api.lalaharihealth.com" http://127.0.0.1/api/v1/health/
sudo certbot --nginx --redirect -d lalaharihealth.com -d api.lalaharihealth.com
sudo systemctl reload nginx
```

Certbot adds the certificate directives and HTTP-to-HTTPS redirects to this new Nginx file only. Confirm its renewal timer is active:

```bash
sudo systemctl status certbot.timer --no-pager
curl --fail https://api.lalaharihealth.com/api/v1/health/
curl -I https://lalaharihealth.com/
```

## Later releases

Back up PostgreSQL before each migration. The production database is separate from all other app databases.

```bash
sudo install -d -o postgres -g postgres -m 0700 /var/backups/lalaharihealth
sudo -u postgres pg_dump --format=custom --file="/var/backups/lalaharihealth/lalaharihealth_db.$(date +%F-%H%M%S).dump" lalaharihealth_db
sudo -iu lalahari
cd /srv/lalaharihealth
git pull --ff-only
cd backend
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
cd ../frontend
npm ci
npm run build
exit
sudo systemctl restart lalaharihealth-api lalaharihealth-web
sudo systemctl status lalaharihealth-api lalaharihealth-web --no-pager
```
