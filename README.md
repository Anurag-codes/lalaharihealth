# LalahariHealth

Consult experienced doctors for a minimal fee, compare treatment options across
Allopathic, Homeopathic, Ayurvedic, Unani and Home Remedy — and get guided to the
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
2. Auth (registration/login/JWT) → `apps.accounts` API
3. Consultation booking + payments flow
4. Patient & doctor dashboards
