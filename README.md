# LalahariHealth

Consult experienced doctors for a minimal fee, compare treatment options across
Allopathic, Homeopathic and Home Remedy — and get guided to the
best, most affordable hospital when advanced care is genuinely needed.

## Tech stack & why

| Layer     | Choice                                   | Why |
|-----------|-------------------------------------------|-----|
| Backend   | **Django + Django REST Framework**        | This is a multi-sided marketplace (patients, doctors, hospitals, payments) that needs a strong admin panel from day one for doctor KYC/verification, content moderation and support ops. Django's batteries-included admin, auth and ORM let us model that relational data quickly and safely. FastAPI is excellent for lean, async-heavy microservices, but we'd rebuild the admin/auth/ORM tooling Django gives for free. |
| Frontend  | **Next.js (App Router) + TypeScript + Tailwind CSS** | Fast, SEO-friendly, image-optimized marketing pages plus room to grow into authenticated patient/doctor dashboards using the same codebase. |
| Auth      | JWT (`djangorestframework-simplejwt`)      | Stateless auth that works cleanly for a decoupled frontend/backend and later mobile apps. |

The two apps are decoupled: the frontend talks to the backend purely over a JSON
API (`/api/v1/...`), so either side can be redeployed or replaced independently.

## Project structure

```
lalaharihealth/
├── backend/                  Django project (API + admin)
│   ├── config/                settings, root urls, wsgi/asgi
│   ├── apps/
│   │   ├── accounts/           custom User model (patient/doctor/admin roles)
│   │   ├── doctors/            doctor profiles, KYC documents, verification
│   │   ├── patients/           patient profiles
│   │   ├── treatments/         conditions + cross-system treatment options
│   │   ├── hospitals/          partner hospitals + recommendations
│   │   ├── consultations/      symptom intake -> doctor consultation records
│   │   ├── appointments/       scheduled slots
│   │   ├── payments/           consultation fee payments
│   │   └── core/               testimonials, FAQs, contact messages
│   ├── requirements.txt
│   └── manage.py
└── frontend/                  Next.js app
    └── src/
        ├── app/
        │   ├── page.tsx          promotional homepage
        │   ├── for-doctors/      doctor onboarding teaser (full flow: TODO)
        │   └── layout.tsx        shared Navbar/Footer/mobile CTA
        └── components/
            ├── ui/                Button, Container, Eyebrow, Image/VideoPlaceholder
            ├── layout/            Navbar, Footer, MobileStickyCta
            └── sections/          every homepage section (Hero, TreatmentComparison, ...)
```

Only the promotional homepage is fully built out right now, per the current
priority. The backend apps are scaffolded with models + admin so future API
endpoints (serializers/viewsets) can be added quickly; `urls.py` stubs exist
per app under `/api/v1/...` ready to be filled in.

## Getting started

### Backend (Django)

```powershell
cd backend
venv\Scripts\activate
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

API root: `http://127.0.0.1:8000/api/v1/health/` · Admin: `http://127.0.0.1:8000/admin/`

### Patient mobile authentication

Patient authentication uses **Gmail SMTP email OTP** or **Firebase Phone Auth**.
The Android/iOS app owns the phone SMS flow. The backend owns email code
generation, delivery and verification; never embed Gmail credentials in the app
or trust a client-supplied `verified` flag. Both sign-in paths return our JWT pair
and automatically register a new patient/profile only after successful verification.
Existing username/password authentication is retained for existing users/staff.

#### Configure the backend

Install the updated `backend/requirements.txt`, then run `python manage.py migrate`.
The migration adds verified contacts, OTP/rate-limit records and JWT blacklist tables.
Configure these only in the backend environment (see `backend/.env.example`):

- `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=True`,
  `EMAIL_USE_SSL=False`.
- `EMAIL_HOST_USER`: your Gmail or Google Workspace sender.
- `EMAIL_HOST_PASSWORD`: its Google **App Password**, not the normal account password.
  The account must be eligible for App Passwords and have Google's required security
  settings enabled. Set `DEFAULT_FROM_EMAIL` to that sender or an authorised sender.
- `FIREBASE_PROJECT_ID`: the same project used by both mobile apps.
- `FIREBASE_CREDENTIALS_FILE`: absolute path to its service account JSON, stored
  outside git/public media with restricted filesystem access. Application Default
  Credentials are also supported when this path is empty. Credentials must allow
  Firebase Authentication user lookups for revocation/disabled-user checks.
- Enable the Phone sign-in provider, SMS regions/billing and Android/iOS app
  verification in the Firebase project. The backend does not send Firebase SMS.
  Firebase Authentication emulator tokens are deliberately not accepted.

Without SMTP/Firebase configuration the relevant endpoint returns **503**, not a
fake successful login. Live provider delivery/verification requires real credentials.
Local tests mock the provider boundary and do not send email or SMS.

Use HTTPS and `DEBUG=False` in production. PostgreSQL is required for reliable
concurrent row locking in OTP consumption and rate-limit counters; SQLite is for
local development. Keep `SECRET_KEY` strong and stable (it also protects OTP hashes).

#### Email sign-in / registration

All URLs below are relative to `/api/v1/auth/patient/`; requests use JSON.

1. `POST email/request-otp/` with `{"email":"patient@example.com"}`.
   A **202** response contains:

   ```json
   {
     "request_id": "<uuid>",
     "expires_in": 300,
     "resend_after": 60,
     "detail": "Verification email sent. Use the code to continue."
   }
   ```

2. `POST email/verify-otp/` with
   `{"request_id":"<uuid>","otp":"123456"}`. Keep the OTP as a string so leading
   zeroes are preserved. Use the newest request ID after requesting another code.

Email addresses are trimmed/lowercased. Six-digit codes expire after five minutes,
allow five guesses per challenge and are single-use. Resending invalidates previous
codes for that address. Only a keyed digest is stored, never the plaintext code.
Requests are limited to one per minute and five per hour per address, twenty per
hour per client IP. Verification/phone exchange/refresh each have a sixty-per-hour
IP limit. Invalid/expired codes return **400**; throttling returns **429** with
`Retry-After`; delivery/configuration failures return **503**.

#### Phone sign-in / registration

1. In Android/iOS use Firebase Phone Auth to request the SMS OTP and sign in with
   the SMS credential. Firebase SDK app verification must be configured there.
2. Obtain the signed-in user's Firebase **ID token**, not a custom token, SMS code
   or Firebase refresh token.
3. `POST phone/firebase/` with `{"id_token":"<firebase-id-token>"}`.

The Admin SDK verifies signature/project/expiry and checks revoked tokens and
disabled/deleted Firebase users. The token must come from a phone sign-in, contain
an E.164 number (for example `+919812345678`), and have an authentication time within
five minutes. Tenant tokens are not supported. Each Firebase ID token is exchanged
only once. On a rejected replay, obtain a fresh token; if sign-in is older than five
minutes, reauthenticate using the SMS flow (refreshing an ID token does not reset
its authentication time). App-side delivery failures never create a backend account.
Invalid/stale/revoked proof returns **401**; Firebase service/configuration failures
return **503**.

#### Shared successful response and patient endpoints

Successful email/phone verification returns **200**:

```json
{
  "access": "<our-access-jwt>",
  "refresh": "<our-refresh-jwt>",
  "is_new_user": true,
  "user": {
    "id": 123,
    "first_name": "",
    "last_name": "",
    "city": "",
    "role": "patient",
    "email": "patient@example.com",
    "phone_number": "",
    "is_email_verified": true,
    "is_phone_verified": false,
    "identities": [
      {"kind": "email", "value": "patient@example.com", "verified_at": "<timestamp>"}
    ]
  }
}
```

Store tokens in the mobile OS secure storage. Send our access JWT as an
`Authorization: Bearer <access>` header to protected APIs, not the Firebase token.

- `GET me/`: current patient and verified contacts.
- `PATCH me/`: update only `first_name`, `last_name`, `city`. Role, verification
  flags and contacts cannot be changed through profile updates.
- `POST token/refresh/` with `{"refresh":"<our-refresh-jwt>"}`: returns new
  `access`/`refresh`. **Replace both stored tokens**. Used refresh tokens are
  blacklisted. Serialize refresh calls in the app; do not refresh concurrently.
- `POST logout/` with the access header and `{"refresh":"<our-refresh-jwt>"}`:
  revokes that account's supplied refresh token (204). Delete local tokens.
  Already-issued access tokens remain valid until expiry (currently 60 minutes);
  Firebase revocation does not instantly revoke already-issued backend JWTs.

Inactive users and doctor/staff/admin accounts cannot use these patient endpoints.
Existing `/api/v1/auth/token/` and `/api/v1/auth/token/refresh/` stay available for
legacy authentication; refresh rotation now revokes the old token there too.

#### Link the other verified method

First sign in and send the **current backend access JWT**:

- `POST link/email/request-otp/` with `{"email":"patient@example.com"}`.
- `POST link/email/verify-otp/` with its `request_id` and `otp`. The challenge is
  bound to that signed-in patient and cannot be verified by another user or on the
  anonymous sign-in endpoint.
- `POST link/phone/` with a recent Firebase phone `id_token`.

Successful linking returns the same JWT/user response with `is_new_user=false`.
Each patient may have one verified email and one verified phone. Contacts and
Firebase UIDs are unique. A contact already linked to another account returns
**400**; accounts are never automatically merged. Replacing a verified contact
or recovering a changed Firebase UID requires a separate support/recovery process.
Legacy email/phone profile fields are not treated as proof of ownership: sign in
to the original legacy account and explicitly link the contact, or contact support.
No bulk verification or automatic migration of old profile fields is performed.

#### Operations and tests

Rate limits use database-backed counters, not process-local memory. By default
the socket IP is used; forwarded headers are ignored. Enable
`PATIENT_AUTH_TRUST_PROXY_HEADERS=True` **only** when direct API access is blocked
and a trusted reverse proxy overwrites `X-Real-IP` (as the supplied Nginx templates
do). Otherwise a client could forge its rate-limit identity.

Run daily: `python manage.py cleanup_patient_auth` and
`python manage.py flushexpiredtokens`. The first removes expired OTP records older
than one day, expired Firebase replay digests and stale rate counters; the second
removes expired JWT blacklist/outstanding records. No OTP/token proof is returned
in API responses or included in application logs. Verified identities are
read-only in Django admin; use an audited recovery process rather than manually
marking an existing contact verified.

Run `python manage.py test apps.accounts` for the authentication regression tests.
Interactive API documentation is under `/api/v1/docs/` (Patient authentication).

#### API documentation for app developers

Swagger UI: `/api/v1/docs/`; raw schema: `/api/v1/schema/` (also committed as
`backend/openapi.yaml`, regenerate with `python manage.py spectacular --file openapi.yaml --validate`).
Every endpoint has a description, request and response examples and its error
responses. Examples that views do not declare themselves come from
`apps/core/openapi_examples.json` and are added by the `apps.core.openapi.add_docs`
postprocessing hook. `python manage.py test apps.core.tests_openapi` fails if an
endpoint is missing docs or an example does not match its schema.

### Patient profile section APIs

All patient endpoints need the patient access JWT. Request/response examples for
each one are in Swagger under **Patient profile**, **Family profiles**,
**Medical records** and **Doctor consultation records**.

| Screen | Endpoint |
| --- | --- |
| Profile | `GET` / `PATCH /api/v1/patients/profile/`: name, city, gender, date of birth and app language (`en` or `hi`). Also returns the photo URL, beneficiary badge and family member count. Email and phone change only through `/api/v1/auth/patient/link/`. |
| Profile photo | `PUT` (multipart field `photo`: PNG/JPG up to 5 MB), `GET` (private, authenticated download), `DELETE /api/v1/patients/profile/photo/` |
| Family Profiles | `GET` / `POST /api/v1/patients/family-members/`; `GET` / `PATCH` / `DELETE /api/v1/patients/family-members/{id}/`. Store `date_of_birth`; `age` is calculated. |
| Medical Records | `GET /api/v1/patients/medical-records/` (paginated; optional `?family_member_id=self` or an id). `status` is `upcoming`, `completed` or `cancelled`; every mode is shown as Online. |
| Consultation Record | `GET /api/v1/patients/medical-records/{consultation_id}/`: diagnosis, prescriptions, doctor notes and follow-up, filled once the doctor completes the consultation. |
| Contact Us | `GET /api/v1/core/support-contacts/` (public). Change it with `SUPPORT_PHONE_NUMBER` / `SUPPORT_EMAIL`. |

To book for a relative, send `family_member_id` to `POST /api/v1/consultations/`;
blank patient fields are filled from that member. Records keep the name and
relation used at booking, even after the member is removed.

Verified doctors sign in with `POST /api/v1/auth/token/`, list assigned
consultations at `GET /api/v1/doctors/me/consultations/?status=upcoming`, and
write the record with
`PUT /api/v1/doctors/me/consultations/{id}/record/`. The prescription list sent
there replaces the previous one. `mark_completed: true` completes the
consultation and appointment and publishes the record to the patient. Doctors can
also download the intake documents of their assigned consultations.

### Appointment booking flow APIs

Examples for every request and response are in Swagger under **Mobile intake**,
**Mobile documents**, **Mobile scheduling**, **Payments** and **Doctor schedule**.

| Screen | Endpoint |
| --- | --- |
| Patient Details + Verify OTP (logged out) | The app keeps the typed details, logs in with Firebase phone OTP (`POST /api/v1/auth/patient/phone/firebase/`), then sends them to `POST /api/v1/consultations/`. |
| Select Patient (logged in) | `GET /api/v1/patients/booking-patients/` returns Myself, then family members. `POST /api/v1/consultations/` with `{"family_member_id": null or id, "mode": "video"}` fills in the details. A 400 that lists missing fields means the app should show Patient Details. "+ Add family member" uses `POST /api/v1/patients/family-members/`. |
| Symptoms (Known Disease → Specific Type → Sub-condition/Variant) | `GET /api/v1/consultations/conditions/` returns the tree. Send `PUT /api/v1/consultations/{id}/history/` with `condition`, `condition_type`, `condition_variant`, `condition_details`, `duration_value`, `duration_unit`, `ongoing_medication` and `treatment_details`. The type and variant are required whenever that level has options. Manage the list in Django admin under Conditions / Condition types. |
| Upload Documents | `POST /api/v1/consultations/{id}/documents/` (optional) |
| Schedule Appointment | `GET /api/v1/appointments/slot-dates/?days=7` returns the date strip. `GET /api/v1/appointments/slots/?date=YYYY-MM-DD` returns the 15-minute times. "Request Appointment" only opens Case Preview. |
| Case Preview | `GET /api/v1/consultations/{id}/preview/?slot_id=`. "Submit Case" sends `POST /api/v1/appointments/` with `{"consultation_id", "slot_id", "information_confirmed": true}`. This reserves the slot. If that doctor was just booked, it uses another doctor who is free at the same time. |
| Checkout | `GET /api/v1/appointments/{id}/` returns `appointment_number`, `schedule_date`, `schedule_time` and `amount`. Then `POST /api/v1/payments/orders/` → Razorpay SDK → `POST /api/v1/payments/verify/`. |
| Finding Your Doctor | Poll `GET /api/v1/appointments/{id}/`. `finding_doctor` means payment succeeded. `confirmed` adds `doctor_name`. |

Verified doctors open their time from the doctor app:
`POST /api/v1/doctors/me/slots/` with `{"date": "2026-10-18", "start_time": "19:00"}`. This creates
15-minute slots from that time until 23:45 (or until the optional `end_time`). Each slot holds one patient.
`GET /api/v1/doctors/me/slots/?date=` lists the slots and shows which are booked, and
`DELETE /api/v1/doctors/me/slots/{id}/` removes a slot that is not booked.
Patients see each time once, as long as any verified doctor is free then. When staff assign a doctor after
payment (`/api/v1/appointments/{id}/assign-doctor/`), the booking moves to that doctor's slot at the same time.

### Home screen APIs

Examples are in Swagger under **Home**, **My Cases**, **Notifications** and **Appointment booking**.

| Home screen part | Endpoint |
| --- | --- |
| Welcome Back, avatar, EN toggle, bell red dot, "Prefer to book by call?", Upcoming appointments, My Cases badge | `GET /api/v1/patients/home/`. Change the language with `PATCH /api/v1/patients/profile/` and `{"preferred_language": "hi"}`. |
| General Physician → Book Appointment | The normal booking flow (fee from the country pricing table, target `DOCTOR_MATCH_TARGET_MINUTES`). |
| Expert Care → Book Specialist | `GET /api/v1/doctors/specialities/`. Send `speciality` in `POST /api/v1/consultations/` and `speciality_id` to `slot-dates/` and `slots/`. The fee comes from the speciality. |
| Bell / notification list | `GET /api/v1/notifications/` (`?unread=true`), `unread-count/`, `POST {id}/read/`, `POST read-all/` |
| Push | After login, `POST /api/v1/notifications/devices/` with `{"token": "<FCM token>", "platform": "android"}`. On logout, `POST /api/v1/notifications/devices/remove/`. |
| My Cases (Track history) | `GET /api/v1/patients/cases/?status=active` (or `closed`) and `GET /api/v1/patients/cases/{consultation_id}/`. Each case has `stage`, `next_action` and a 4-step `tracker`. |
| Medical Records | Unchanged: `/api/v1/patients/medical-records/` |

Notifications are created automatically for payment successful, doctor assigned, consultation completed,
appointment cancelled and appointment reminder (English or Hindi, following the patient's app language).
Admins can send a broadcast from Django admin → Announcements → "Send now".

Operations:

- **Specialities.** Manage them in Django admin → Specialities. Cardiology, Orthopaedics and Dermatology are seeded as
  *inactive* with a placeholder fee of ₹500. Set the real fee, then tick Active. Set each specialist's
  **Speciality** on their Doctor profile. A doctor without one is a general physician. Staff can assign a doctor
  only when the doctor's speciality matches the booking and their `consultation_fee` equals the fee paid.
- **Reminders.** Run `python manage.py send_appointment_reminders` every 5 minutes (cron or Task Scheduler).
  It notifies confirmed appointments starting within `APPOINTMENT_REMINDER_MINUTES`, once per appointment.
- **Push.** Push uses the same `FIREBASE_*` service-account settings as phone login. Set
  `PUSH_NOTIFICATIONS_ENABLED=False` to keep inbox-only notifications.

### Location-based pricing

The general physician fee depends on the user's country. Rates are stored in the `CountryPricing` table (Django admin ? **Country pricing**). Only India is seeded: INR ₹200, with specialists choosing ₹200?₹2,000 in steps of 100. India is also the fallback for any country without an active row. Add a row per country with its currency, symbol, general fee and specialist min/max/step.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/pricing/?lat=28.61&lng=77.20` | Public. Finds the country offline from GPS coordinates (`reverse_geocode`, coordinates are not stored) and returns its pricing. |
| `GET /api/v1/pricing/?country=US` | Same, but by ISO country code. With no parameters it returns the default (India). |

The response includes `country_code`, `currency`, `currency_symbol`, `general_fee`, `general_fee_display`, `general_doctor_payout_display` (75%), the specialist range, `source` (`location`/`country`/`default`) and `is_fallback`.

- **App booking:** send the returned `country_code` in step 1 (`POST /api/v1/consultations/`). General bookings are charged that country's fee in its currency. Razorpay orders use minor units (cents, paise...), so enable international currencies in Razorpay. Specialist bookings always use the INR speciality fee.
- **Home screen:** `GET /api/v1/patients/home/?lat=&lng=` (or `?country=`) returns the localised `general_care` fee.
- **Doctor applications:** the fee is validated against the pricing of `country_code`. A general doctor's fee must equal the general fee, and a specialist's fee must fall within min/max on the step.
- **Website:** on load, the site asks for location ("Location is required to show you correct doctors of your area"). Every price is then shown in the visitor's currency. If permission is denied, ?200 is shown.

### Frontend (Next.js)

```powershell
cd frontend
npm install
npm run dev
```

App: `http://localhost:3000`

## Brand colors

| Token      | Hex       | Usage                          |
|------------|-----------|---------------------------------|
| Primary    | `#00A7A7` | Buttons, highlights, icons, links |
| Ink (text) | `#1F2937` | Body copy                       |
| Background | `#FFFFFF` | Page background                 |

Defined as CSS variables/Tailwind tokens in `frontend/src/app/globals.css`
(`--primary`, `--ink`, `--background`, plus generated tints/shades used for
section backgrounds and gradients).

## Images & videos still needed

The homepage ships with clearly labelled placeholder boxes (dashed border,
teal tint) instead of guessed stock photos — each one states exactly what to
shoot or source. Search them by component name to swap in real media:

| Where                                   | What to source                                                                 | Suggested size |
|------------------------------------------|---------------------------------------------------------------------------------|-----------------|
| Hero (`Hero.tsx`)                        | Doctor on a video call with a patient, warm/friendly lighting                   | 900×1000        |
| How It Works (`HowItWorks.tsx`)          | 45–60s demo video: symptom intake → doctor call → treatment comparison screen   | 16:9, ~60s      |
| Home Remedy banner (`HomeRemedyBanner.tsx`) | Flat-lay of ginger, turmeric, honey, tulsi, lemon, cinnamon                  | 800×800         |
| Hospital Support (`HospitalSupport.tsx`) | Clean hospital reception/exterior, or doctor reviewing a report with a patient  | 900×700         |
| Hospital partner logos                   | Real partner hospital logos (once partnerships are signed)                     | any, transparent bg |
| Patient stories (`VideoTestimonials.tsx`)| 3 short real patient testimonial videos (consent required)                     | 4:3, 30–45s each |
| Doctor cards (`DoctorsShowcase.tsx`)     | 4+ professional doctor headshots (once real doctors are onboarded)             | 500×500         |
| For Doctors page                         | Doctor using a laptop/tablet in a clinic setting                               | 900×700         |

All sample doctor names, testimonials and stats are placeholder/template
content — replace with real, consented data before launch.

## Roadmap

1. Doctor onboarding flow (multi-step form + document upload → `apps.doctors` API)
2. Integrate Android/iOS clients with patient email OTP and Firebase phone authentication → `apps.accounts` API
3. Consultation booking + payments flow
4. Patient & doctor dashboards
