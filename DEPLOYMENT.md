# LalahariHealth deployment

These instructions deploy the Next.js site at `lalaharihealth.com` and the Django API at `api.lalaharihealth.com` alongside existing Nginx sites. They use independent systemd services, an API Unix socket, and frontend port `127.0.0.1:3101`; they do not edit or restart existing application services.

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
sudo install -d -o lalahari -g lalahari -m 0755 /srv/lalaharihealth
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

Swagger documentation is available after deployment at `https://api.lalaharihealth.com/api/v1/health/swagger-documentation/`. The OpenAPI schema is available at `https://api.lalaharihealth.com/api/v1/schema/`.

Patient authentication needs the SMTP sender/App Password and Firebase project
settings in `deploy/backend.env.example`. Store the Firebase service account file
outside the checkout and public media; restrict it to the service user. Install
the updated requirements, run migrations (including SimpleJWT blacklist tables),
and restart the API. Missing provider configuration returns 503 rather than
issuing unverified tokens. See the root README's Patient mobile authentication
section for the Android/iOS contract and account-linking flow.

`PATIENT_AUTH_TRUST_PROXY_HEADERS=True` is appropriate for this deployment only
because the API listens on a private Unix socket and Nginx overwrites `X-Real-IP`.
Do not enable it for a directly reachable development/API server. Use PostgreSQL
for authentication row-locking and run `python manage.py cleanup_patient_auth`
and `python manage.py flushexpiredtokens` daily using the API service user and its
virtual environment. Never include SMTP passwords, Firebase credentials or live
OTP values in logs or commits.

Set a real random `SECRET_KEY` in `.env`; this command prints one:

```bash
python3.12 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Set the printed value as `SECRET_KEY` in `.env`. The supplied production template also sets HSTS to one year. Keep HSTS enabled only after both domains have valid HTTPS certificates; it is safe to leave the setting at `0` until the Nginx and Certbot steps below are complete.

Build the frontend only after creating its production environment file, because `NEXT_PUBLIC_API_BASE_URL` is embedded during the Next.js build:

```bash
cd /srv/lalaharihealth/frontend
source /srv/lalahari/.nvm/nvm.sh
nvm use 20
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
sudo ss -ltnp '( sport = :3101 )'
curl --fail http://127.0.0.1:3101/
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

If a certificate was accidentally deployed to another site's Nginx block, remove the LalahariHealth-specific block from that site and replace `/etc/nginx/sites-available/lalaharihealth` with `deploy/nginx-lalaharihealth-https.conf`. The dedicated configuration uses the existing certificate files and must be validated with `sudo nginx -t` before reloading Nginx.

## Later releases

Blog publishing requires the `blogs` migrations and public image storage under
`backend/media/blogs/`. The API's existing `/media/` location serves those images;
include that directory in persistent storage and backups. Never put private
medical records in blog uploads. Staff publish at `/admin/` under Blog publishing.
The Next.js server must be able to reach the configured API URL for admin-published
posts on `/blogs` and `/blogs/<slug>`; these reads are not persistently cached.
The homepage blog preview and the three default resources on `/blogs` are fixed
site content and do not require the API.

Doctor verification uploads use `/srv/lalaharihealth/backend/private_documents/`,
not `backend/media/`. The stored relative path `doctors/documents/YYYY/MM/file.pdf`
is inside that private directory; only doctor profile photos use `media/doctors/photos/`.
Include `private_documents/` in persistent storage and backups, and ensure the
`lalahari` service user can write there. Do not expose it with an Nginx media alias.
Doctors download files through the authenticated API `download_url`; staff use
the file link or **Download** in Django admin. Run migrations: `doctors.0011`
moves existing public verification uploads to private storage. If a database
entry has no file in either location, restore it from backup or upload it again;
the migration cannot recreate missing files.

For app-run Zoho Meeting audio/video calls, deploy migration
`appointments.0006_appointmentcall_status` with `python manage.py migrate` and
restart the API. Existing call logs remain `unknown`; new doctor-app callbacks
can explicitly report in-progress, completed, failed, missed or cancelled calls.
No Zoho backend environment variables are required for this call-logging-only
integration. Session creation/joining stays in the app's SDK integration; call
completion remains separate from consultation completion. See the README's
Zoho Meeting SDK call outcomes section for requests and retry behavior.

### 100ms appointment video setup

For 100ms SDK video consultations, configure `HMS_ACCESS_KEY`, `HMS_APP_SECRET`
and `HMS_TEMPLATE_ID` in the server's backend `.env` using the matching app
credentials and a dedicated 100ms conferencing template. Optional
`HMS_DOCTOR_ROLE` / `HMS_PATIENT_ROLE` default to `doctor` / `patient`.
Never put signing secrets or management tokens in the app or repository.

In the 100ms dashboard, set both roles to `maxPeerCount: 1`, allow microphone /
camera and mutual subscription, disable role changes, and explicitly disable
browser recording, RTMP streaming and HLS streaming permissions. Disable all
automatic recording, transcription and caption/AI plugins on the template;
verify newer recording configurations manually. Do not create/share room codes
for these private rooms. Set the desired region and confirm account capacity
for five simultaneous two-person rooms. The API rejects unsafe role settings.

Deploy migration `appointments.0007_appointment_video_room` with
`python manage.py migrate`, then restart `lalaharihealth-api`. No new package
installation is required specifically for this integration. PostgreSQL 15+
(required by the current Django version) with row locking is required; SQLite
join requests return 503. Each appointment has a
persisted opaque provisioning name and one reusable private room, including
after a provider timeout. Rooms use the template selected when first reserved;
changing the environment template ID affects new reservations, not existing rooms.

Doctor join: `POST /api/v1/doctors/me/appointments/{id}/video/join/`.
Patient join: `POST /api/v1/appointments/{id}/video/join/`.
Both send `{}` with the correct backend access JWT and receive the room ID,
role-specific SDK `auth_token` (300 seconds), expiry and `call_id`. Responses
are `no-store`. No management token or app secret is returned.
The assigned doctor PATCHes the existing call-details endpoint only after actual
SDK events. See the README's **100ms private video consultations** section for
complete contracts, retry behavior and security/expiry limitations.

### Staff assignment at a replacement time

The staff assignment API accepts optional `starts_at` alongside `doctor_id`.
In Django admin, paid **Finding doctor** appointments expose an editable Doctor
dropdown and Slot time date/time fields. Save assigns the doctor and confirms the
actual time using the same payment, category, future-time and conflict checks
as the API. Eligible **Confirmed** appointments also allow doctor/time editing:
send optional `doctor_id` and/or `starts_at` to the same API, omitting a field to
retain its current value. Unchanged confirmed requests are idempotent.
Open `/admin/appointments/appointment/`, then the appointment's change page; these
controls are not on the Consultations page.
Once the consultation/call has started or a 100ms room ID has been provisioned,
doctor/time are locked. Issued video credentials create a safety lock, not proof
that a call started. A failed reservation without a room ID remains editable.
Deployment requires updated backend code and an API restart; there is no new
migration or environment setting for this change. See the README's Doctor
assignment after payment section for the request and admin steps.

### Independent family-member access

After deploying/restarting the API, a family member signing in with their own
Firebase-verified patient phone can see bookings whose saved family patient phone
matches that identity. No migration, account merge or new environment setting is
needed; existing matching bookings work automatically. Prefer E.164 phone numbers
in family profiles/Patient Details. Bare Indian ten-digit numbers match +91 only
for India/default-country bookings, not arbitrary international national numbers.
Changing/deleting a family profile does not change the historical booking phone.

Existing appointments, Home/My Cases, medical-record/document and patient video
join APIs support this access. Drafts and other relatives are not shared.
`can_manage_payment=false` identifies a family viewer; mobile clients must hide
checkout and use the viewer's own JWT for reads and joins. Payment creation and
verification remain restricted to the original booker. The 100ms template still
has one doctor and one patient seat; this does not add a second patient seat.
See README's independent family-member contract. Existing notification recipients
and doctor call-reporting responsibilities are unchanged.

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
source /srv/lalahari/.nvm/nvm.sh
nvm use 20
npm ci
npm run build
exit
sudo systemctl restart lalaharihealth-api lalaharihealth-web
sudo systemctl status lalaharihealth-api lalaharihealth-web --no-pager
```

### Full-day appointment scheduling

Appointments, staff/admin replacement assignment and doctor availability slots now accept any
15-minute start from 00:00 through 23:45 Asia/Kolkata time. A complete future day has 96 slots;
today omits past times. Existing booking-window, authorization, payment and conflict rules remain.
This change needs an API deployment/restart, but no database migration or new environment variables.
It does not automatically create doctor availability or change existing appointment times.

Coordinate the mobile release to remove 08:00 lower bounds and 64-slot limits. Patients consume
`GET /api/v1/appointments/slots/?date=YYYY-MM-DD` and `/api/v1/appointments/slot-dates/`.
Verified doctors open a full future day with
`POST /api/v1/doctors/me/slots/` and `{"date": "2026-11-16", "start_time": "00:00"}`,
omitting `end_time`. A supplied end is exclusive and on the same date; `24:00` and overnight
windows are not accepted. The mobile source is outside this repository; see README's full-day
app contract. Existing AM/PM display labels and offset-aware appointment timestamps are unchanged.

When deploying the Swagger addition to an already-running server, install the updated backend requirements, collect its self-hosted Swagger assets, and restart the API service:

```bash
sudo -iu lalahari
cd /srv/lalaharihealth/backend
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py collectstatic --noinput
exit
sudo systemctl restart lalaharihealth-api
```
