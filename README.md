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

### Simplified partner registration

The `/for-doctors` page currently shows only name, phone number and education for
doctors, and facility name, contact person and phone number for hospitals/clinics/labs.
Other input fields and their frontend submission logic are commented out for now;
the visible fields retain their existing frontend required validation.

All application fields are optional in the backend endpoints
`POST /api/v1/doctors/applications/` and `POST /api/v1/hospitals/applications/`.
Supplied values still undergo validation. Existing full submissions, photos and
document uploads remain supported. Run `python manage.py migrate` when deploying
this change, then rebuild the frontend.

Omitted doctor experience and consultation fee are stored and returned as `null`,
and an unspecified consultation category is an empty string. The featured-doctors
endpoint also returns `fee_display: null` for an unspecified fee; clients must not
display missing experience or invent a consultation price. Existing records keep
their stored values. Staff still approve applications before they appear publicly.

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

Verified doctors sign in to the doctor app with Firebase phone OTP (see **Doctor app APIs** below), list assigned
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
| Schedule Appointment | `GET /api/v1/appointments/slot-dates/?days=7` returns the date strip. `GET /api/v1/appointments/slots/?date=YYYY-MM-DD` returns every 15-minute time from 08:00 AM to 11:45 PM (past times left out), for any category. The patient picks a preferred time only; no doctor is chosen. "Request Appointment" only opens Case Preview. |
| Case Preview | `GET /api/v1/consultations/{id}/preview/?starts_at=` (URL-encode the `+` of the offset). "Submit Case" sends `POST /api/v1/appointments/` with `{"consultation_id", "starts_at", "information_confirmed": true}`. This creates the appointment without a doctor and locks the fixed category fee. |
| Checkout | `GET /api/v1/appointments/{id}/` returns `appointment_number`, `schedule_date`, `schedule_time` and `amount`. Then `POST /api/v1/payments/orders/` → Razorpay SDK → `POST /api/v1/payments/verify/`. |
| Finding Your Doctor | Poll `GET /api/v1/appointments/{id}/`. `finding_doctor` means payment succeeded. `confirmed` adds `doctor_name`. |

**Fixed fee per category.** `GET /api/v1/pricing/consultation-fee/?category=general` (optional `&country=US`) returns the
general physician fee stored for the country. `?category=<speciality id or slug>` returns the specialist fee in INR: the
mode (most common value) of the `consultation_fee` of that speciality's active, verified doctors, the highest one on a
tie, or the speciality's own fee when it has no verified doctors yet. The same amount is shown in the speciality list and
Case Preview, and is locked on Submit Case, so later fee changes do not affect submitted appointments.

**Doctor assignment after payment.** Staff call `POST /api/v1/appointments/{id}/assign-doctor/` with `{"doctor_id"}` once
the appointment is `finding_doctor`. Any active, verified doctor of the booking's category can be assigned (a general
physician for general bookings, the same speciality for specialist bookings), whatever their own fee. A doctor who
already has an unfinished appointment at that time is rejected; once the doctor marks that consultation completed,
they can be assigned another patient at the same time. The doctor gets a "New appointment booked" notification.

Verified doctors can still mark when they are free from the doctor app:
`POST /api/v1/doctors/me/slots/` with `{"date": "2026-10-18", "start_time": "19:00"}`. This creates
15-minute slots from that time until 23:45 (or until the optional `end_time`). Each slot holds one patient.
`GET /api/v1/doctors/me/slots/?date=` lists the slots and shows which are booked, and
`DELETE /api/v1/doctors/me/slots/{id}/` removes a slot that is not booked.
Patients do not see these slots. When staff assign a doctor who has a slot at the appointment time, that slot is
linked to the appointment and shows as booked in the doctor app.

### Home screen APIs

Examples are in Swagger under **Home**, **My Cases**, **Notifications** and **Appointment booking**.

| Home screen part | Endpoint |
| --- | --- |
| Welcome Back, avatar, EN toggle, bell red dot, "Prefer to book by call?", Upcoming appointments, My Cases badge | `GET /api/v1/patients/home/`. Change the language with `PATCH /api/v1/patients/profile/` and `{"preferred_language": "hi"}`. |
| General Physician → Book Appointment | The normal booking flow (fee from the country pricing table, target `DOCTOR_MATCH_TARGET_MINUTES`). |
| Expert Care → Book Specialist | `GET /api/v1/doctors/specialities/`. Send `speciality` in `POST /api/v1/consultations/`. The fee is the speciality's fixed fee (see `GET /api/v1/pricing/consultation-fee/`); times are the same as for general bookings. |
| Bell / notification list | `GET /api/v1/notifications/` (`?unread=true`), `unread-count/`, `POST {id}/read/`, `POST read-all/` |
| Push | After login, `POST /api/v1/notifications/devices/` with `{"token": "<FCM token>", "platform": "android"}`. On logout, `POST /api/v1/notifications/devices/remove/`. |
| My Cases (Track history) | `GET /api/v1/patients/cases/?status=active` (or `closed`) and `GET /api/v1/patients/cases/{consultation_id}/`. Each case has `stage`, `next_action` and a 4-step `tracker`. |
| Medical Records | Unchanged: `/api/v1/patients/medical-records/` |

Notifications are created automatically for payment successful, doctor assigned, consultation completed,
appointment cancelled and appointment reminder (English or Hindi, following the patient's app language).
Admins can send a broadcast from Django admin → Announcements → "Send now".

Operations:

- **Specialities.** Manage them in Django admin → Specialities. Cardiology, Orthopaedics and Dermatology are seeded as
  *inactive* with a placeholder fee of ₹500. The speciality fee is only used until the speciality has verified
  doctors; after that patients pay the most common fee among them. Set each specialist's
  **Speciality** on their Doctor profile. A doctor without one is a general physician. Staff can assign any verified
  doctor whose speciality matches the booking, whatever their own `consultation_fee`.
- **Reminders.** Run `python manage.py send_appointment_reminders` every 5 minutes (cron or Task Scheduler).
  It notifies confirmed appointments starting within `APPOINTMENT_REMINDER_MINUTES`, once per appointment.
- **Push.** Push uses the same `FIREBASE_*` service-account settings as phone login. Set
  `PUSH_NOTIFICATIONS_ENABLED=False` to keep inbox-only notifications.

### Doctor app APIs

Examples for every request and response are in Swagger under **Doctor app: authentication**, **Doctor app: profile**
and **Doctor app: appointments**. Doctors use doctor JWTs; patient tokens are rejected and vice versa.

| Doctor app screen | Endpoint |
| --- | --- |
| Sign Up → Verify Your Number | The app verifies the OTP with Firebase Phone Auth, then `POST /api/v1/auth/doctor/phone/firebase/` with `{"id_token"}` returns `access`, `refresh`, `is_new_user` and `doctor`. Refresh with `POST /api/v1/auth/doctor/token/refresh/`, log out with `POST /api/v1/auth/doctor/logout/`. |
| After sign-in | Open the screen given by `doctor.onboarding.next_step`: `profile` (Step 2), `availability` (Step 3) or `done` (Home). `GET /api/v1/doctors/me/` returns the same profile. |
| Step 2 Professional Details | `PATCH /api/v1/doctors/me/` with `full_name`, `age`, `gender`, `registration_number`, `qualification` and `speciality_id` (from `GET /api/v1/doctors/specialities/`, `null` = General Physician). Photo: `PUT`/`DELETE /api/v1/doctors/me/photo/`. Registration certificate: `POST /api/v1/doctors/me/documents/` (multipart, `document_type=medical_registration`). Qualification suggestions: `GET /api/v1/doctors/qualifications/?search=`. |
| Step 3 Weekly Availability → Start Consulting | `PUT /api/v1/doctors/me/availability/` replaces the week: 1 to 3 windows per open day (24-hour `HH:MM`, 15-minute steps, no overlaps), at least 6 hours per open day. Staff use it to contact the doctor and assign consultations; patients never see it. |
| Home (day timeline) | `GET /api/v1/doctors/me/schedule/?date=YYYY-MM-DD`: confirmed and completed appointments, 15 minutes each, with `can_join`. |
| Appointment details / call | `GET /api/v1/doctors/me/appointments/{id}/` returns the patient's name, age, gender, phone, reason and fee. The app runs the call. Optional call details: `POST /api/v1/doctors/me/appointments/{id}/calls/`, then `PATCH .../calls/{call_id}/` when it ends. After the consultation, `PATCH /api/v1/doctors/me/appointments/{id}/` with `{"status": "completed"}` (allowed from 5 minutes before the start). |
| Prescription | `PUT /api/v1/doctors/me/consultations/{consultation_id}/record/` |
| Earnings (Daily / Monthly / Financial Year) | `GET /api/v1/doctors/me/earnings/?period=daily&date=YYYY-MM-DD` (`period` = `daily`, `monthly` or `financial_year`): total, count, average, chart and the Video / Audio / Chat split. Only completed consultations count, using the fee the patient paid. |
| Notifications | The same `/api/v1/notifications/` endpoints, plus device registration for push. |
| Profile → Verification Documents | `GET /api/v1/doctors/me/documents/`, download with `download_url` (auth required), `DELETE /api/v1/doctors/me/documents/{id}/`. Uploading `medical_registration`, `degree_certificate` or `government_id` replaces the previous file of that type; up to 5 `other` files. |

- **Doctor accounts.** A doctor account is separate from a patient account on the same number. On first sign-in, the
  newest website For Doctors form entry with the same phone number is copied into the profile: name, email, city,
  qualification, experience, speciality, treatment systems, fee, photo and documents (as `other` documents). Every new
  doctor is **Pending Review**. A doctor account created by staff with that phone number is reused.
- **Verification.** Staff set **Verification status** in Django admin → Doctor profiles. The doctor gets a notification,
  and only verified doctors can open the schedule, appointments and earnings or be assigned. Registration number,
  qualification and speciality are locked in the app once verified. Documents are private: open them from the
  doctor profile in Django admin with the **Download** link.
- **Completion.** When the doctor marks a consultation completed, the patient is notified. Staff confirm it with
  `POST /api/v1/appointments/{id}/confirm-completion/` or the admin action "Confirm completion" (filter Appointments by
  *completion confirmed*). Appointment reminders go to both the patient and the doctor.
- **Deploy.** Run `python manage.py migrate`. Doctor documents are now stored privately in `private_documents/`;
  migration `doctors.0011` moves existing files there from `media/doctors/documents/` (same relative paths) and logs
  any file it could not move. Make sure the app user can write to both folders when migrating.
- **Form matching.** A 10-digit number in the For Doctors form is read as Indian (+91) and only for Indian
  applications; other numbers must be typed with their country code to be matched.

### Location-based pricing

The general physician fee depends on the user's country. Rates are stored in the `CountryPricing` table (Django admin ? **Country pricing**). Only India is seeded: INR ₹200, with specialists choosing ₹200?₹2,000 in steps of 100. India is also the fallback for any country without an active row. Add a row per country with its currency, symbol, general fee and specialist min/max/step.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/pricing/?lat=28.61&lng=77.20` | Public. Finds the country offline from GPS coordinates (`reverse_geocode`, coordinates are not stored) and returns its pricing. |
| `GET /api/v1/pricing/?country=US` | Same, but by ISO country code. With no parameters it returns the default (India). |
| `GET /api/v1/pricing/consultation-fee/?category=` | Public. The fixed fee charged for a category: `general` (with optional `country`) or a speciality id/slug. |

The response includes `country_code`, `currency`, `currency_symbol`, `general_fee`, `general_fee_display`, `general_doctor_payout_display` (75%), the specialist range, `source` (`location`/`country`/`default`) and `is_fallback`.

- **App booking:** send the returned `country_code` in step 1 (`POST /api/v1/consultations/`). General bookings are charged that country's fee in its currency. Razorpay orders use minor units (cents, paise...), so enable international currencies in Razorpay. Specialist bookings always use the INR speciality fee from `GET /api/v1/pricing/consultation-fee/`.
- **Home screen:** `GET /api/v1/patients/home/?lat=&lng=` (or `?country=`) returns the localised `general_care` fee.
- **Doctor applications:** the fee is validated against the pricing of `country_code`. A general doctor's fee must equal the general fee, and a specialist's fee must fall within min/max on the step.
- **Website:** on load, the site asks for location ("Location is required to show you correct doctors of your area"). Every price is then shown in the visitor's currency. If permission is denied, ?200 is shown.

### Doctor photos & homepage doctors

- The /for-doctors form (general doctors and specialists) accepts an optional `photo` (JPG, PNG or WEBP, up to 5 MB) on `POST /api/v1/doctors/applications/`.
- To show a doctor on the homepage, set the application's status to **Approved** in Django admin → **Doctor applications**. The status can be edited directly in the list, which also shows a photo thumbnail.
- `GET /api/v1/doctors/featured/` is public. It returns up to 8 approved doctors, newest first, with only public fields; `photo_url` is `null` when no photo was uploaded.
- The homepage refreshes this list every 60 seconds. It uses the default doctor image when there is no photo. While no doctor is approved, it shows two sample doctors instead.

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
