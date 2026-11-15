# App developer: consultation fees and the free offer

Base URL: `https://api.lalaharihealth.com`. Authenticated requests use
`Authorization: Bearer <backend-access-token>`, not a Firebase or 100ms token.
All example IDs, dates and prices below are illustrative; use live API values.

## 1. Existing specialist fee flow (unchanged)

The app does not need a separate speciality picker. The backend maps the selected
condition and subcategory to a speciality and its fee.

### Fetch condition/subcategory options

`GET /api/v1/consultations/conditions/` (authenticated) returns a plain array:

```json
[
  {
    "id": 3,
    "name": "Headache",
    "slug": "headache",
    "type_label": "Specific Headache Type",
    "speciality": null,
    "types": [
      {
        "id": 7,
        "name": "Cluster Headache",
        "speciality": {
          "id": 4,
          "name": "Neurology",
          "slug": "neurology",
          "title": "Neurology Consultation",
          "fee": 600,
          "currency": "INR",
          "fee_display": "\u20b9600"
        },
        "variants": [{"id": 15, "name": "Chronic"}]
      }
    ]
  }
]
```

- When the condition has `types`, use the selected type's `speciality` object.
  This is already resolved by the server; **do not fall back to the condition
  yourself if the type returns null**.
- Without types, use the condition's `speciality`.
- Non-null: display `speciality.title` and `speciality.fee_display`.
  `speciality.fee` is the numeric fee in whole INR, not paise.
- Null: General Physician. Call public `GET /api/v1/pricing/` (optional
  `?country=IN` or `?lat=...&lng=...`) and display `general_fee_display`.
  Retain its `country_code` for draft creation.
- Variants do not carry a separate fee/category. If a type has variants, the
  user must select one. Never infer a speciality from a condition's name.

To refresh an exact specialist fee without fetching the tree again:

`GET /api/v1/pricing/consultation-fee/?category=4`

Use the speciality **ID or slug**, not the condition/type/variant ID. Public
response:

```json
{
  "category": "neurology",
  "speciality_id": 4,
  "speciality_name": "Neurology",
  "consultation_title": "Neurology Consultation",
  "country_code": "IN",
  "fee": 600,
  "currency": "INR",
  "currency_symbol": "\u20b9",
  "fee_display": "\u20b9600",
  "source": "mode"
}
```

General equivalent:
`GET /api/v1/pricing/consultation-fee/?category=general&country=IN`.
Specialists remain INR. Their price is the most common positive INR fee of the
active verified doctors in that speciality; highest tied fee wins. Without
eligible doctors, the stored speciality fee applies (`source: "speciality_fee"`).
General prices come from country pricing (`source: "general_fee"`).

### Create draft and save symptoms

1. `POST /api/v1/consultations/`:

   ```json
   {
     "patient_name": "Example Patient",
     "patient_age": 30,
     "patient_gender": "male",
     "patient_phone": "+919000000000",
     "country_code": "IN",
     "mode": "video"
   }
   ```

   Retain response `id` as the consultation ID. Existing self/family-member
   shortcuts are still supported. The initial draft's fee may be general until
   symptoms are saved.

2. `PUT /api/v1/consultations/{id}/history/`:

   ```json
   {
     "condition": 3,
     "condition_type": 7,
     "condition_variant": 15,
     "duration_value": 5,
     "duration_unit": "days",
     "ongoing_medication": false
   }
   ```

   Send IDs, not names. Omit children only when the selected item has none.
   The response includes `speciality` (numeric ID or null),
   `consultation_title`, `fee`, `fee_currency`, and `history_completed`.
   **Replace the displayed fee with these server values.** Changing the
   condition/type re-maps the category. No client fee/speciality override.

3. Pick a future `starts_at` from
   `GET /api/v1/appointments/slots/?date=YYYY-MM-DD`. Times are IST,
   15-minute aligned, 00:00-23:45, within 30 days.

4. `GET /api/v1/consultations/{id}/preview/?starts_at=<URL-encoded timestamp>`
   returns `fee`, `currency`, `schedule`, `ready_to_submit`, `missing_steps`,
   and the case details. Ensure the plus in `+05:30` is URL-encoded.
   Nothing is reserved; the fee can change before submission.

5. `POST /api/v1/appointments/`:

   ```json
   {
     "consultation_id": 42,
     "starts_at": "2026-11-20T10:00:00+05:30",
     "information_confirmed": true
   }
   ```

   Response: 201 created / 200 identical retry; important fields include
   `id`, `consultation`, `amount`, `currency`, `status: "awaiting_payment"`,
   `payment_required: true`, `payment_status: "not_started"`,
   `can_manage_payment: true` for the original booker.
   **Use this locked `amount` and `currency` for checkout**, never a hardcoded
   fee, an individual doctor's fee, or a client-supplied amount.

6. `POST /api/v1/payments/orders/`:

   ```json
   {"appointment_id": 123, "method": "upi"}
   ```

   `method` is `upi` or `card`. Response:
   `payment_id`, `gateway_order_id`, `key_id`, `amount`, `currency`, `status`.
   **This payment-order `amount` is minor units (INR paise), unlike appointment
   `amount` and consultation `fee`, which are whole units.** Pass the returned
   order values directly to Razorpay SDK; never multiply again.

7. After SDK success, `POST /api/v1/payments/verify/` with
   `payment_id`, `razorpay_payment_id`, `razorpay_signature`.
   Only server-verified capture is success. Poll
   `GET /api/v1/appointments/{id}/`: `finding_doctor` waits for staff,
   `confirmed` supplies `doctor`, `doctor_name`, and the final schedule.
   SDK success alone does not confirm payment.

## 2. Free general consultation by Dr. Banarsi Das

### Discover the offer (public; refresh on screen focus)

`GET /api/v1/appointments/free-consultation-offer/`

```json
{
  "available": true,
  "offer": {
    "coupon_code": "BANARSI_FREE",
    "doctor_id": 7,
    "doctor_name": "Dr. Banarsi Das",
    "category": "general",
    "fee": 0,
    "currency": "INR",
    "valid_until": null
  }
}
```

Unavailable, disabled, expired, not started, deleted, or ineligible doctor:

```json
{"available": false, "offer": null}
```

Hide the offer when unavailable or on fetch failure. Do not hardcode the doctor
ID or coupon code. No per-patient booking limit while available. The homepage
refreshes every 30 seconds/on focus and hides at a configured expiry; disabling
an offer may take up to 30 seconds to disappear on an already-open page.
All submissions are revalidated immediately on the backend.

### Apply only when the patient selects the offer doctor

Keep the normal intake/history/scheduling flow. After history, the consultation
must have `speciality: null`. Never apply this offer to a specialist case; do
not erase/change the condition mapping to make it eligible.

Send **both** `coupon_code` and `doctor_id` returned above when previewing:

`GET /api/v1/consultations/{id}/preview/?starts_at=<encoded timestamp>&coupon_code=BANARSI_FREE&doctor_id=7`

Preview returns `fee: 0`, `currency: "INR"`, `coupon_code: "BANARSI_FREE"`,
`free_consultation_doctor: 7` alongside the existing case fields. This is a
quote, not redemption. Submit:

```json
{
  "consultation_id": 42,
  "starts_at": "2026-11-20T10:00:00+05:30",
  "information_confirmed": true,
  "coupon_code": "BANARSI_FREE",
  "doctor_id": 7
}
```

`POST /api/v1/appointments/` returns its usual appointment object, including:

```json
{
  "id": 123,
  "consultation": 42,
  "status": "finding_doctor",
  "doctor": null,
  "amount": 0,
  "currency": "INR",
  "coupon_code": "BANARSI_FREE",
  "free_consultation_doctor": 7,
  "payment_required": false,
  "payment_status": "not_required",
  "can_manage_payment": false
}
```

- **Skip payment-order creation, Razorpay checkout and verification.**
  Show "Free consultation requested - waiting for staff confirmation".
  `not_required` is a new payment-status value, not `success`.
- Staff can only assign the selected offer doctor, and can adjust the time
  through the existing staff/admin assignment flow. The appointment becomes
  `confirmed` afterward. Poll detail and use its final doctor/time for calls.
- A 400 for an unavailable/mismatched coupon must show its error, refresh the
  offer and ask the patient to explicitly accept normal paid pricing or leave.
  Never silently fall back to charging the patient.
- Send neither coupon nor doctor ID for normal paid bookings. Sending just
  one is invalid. Clients cannot make bookings free by sending `fee: 0`.
- Repeat identical submissions with the same consultation ID/time/code/doctor:
  200, same appointment, even if the offer expired after initial redemption.
  A different selection for that booked consultation is rejected.
- Existing submitted free bookings remain free after the offer is disabled,
  expires, is edited or is deleted. New bookings cannot redeem it.
  No fake successful payment record or `paid_at` timestamp is created.
- Coupon codes are public promotions, not authentication credentials.
  They do not bypass ownership, intake, scheduling, verification or call rules.

## 3. Staff setup/deployment

1. Apply `appointments.0008_free_consultation_offer` using
   `python manage.py migrate`; rebuild/restart the frontend and backend.
2. In Django admin, ensure Dr. Banarsi Das has an active user with doctor role
   and an active **verified general physician** profile (`Speciality` empty).
3. Go to `/admin/appointments/freeconsultationoffer/` -> Add.
   Enter an uppercase code, e.g. `BANARSI_FREE`; select **Dr. Banarsi Das by
   name/user ID**, set optional start/expiry times (IST), enable **Is active**,
   and save. Only one offer can have Is active checked. No offer is seeded:
   nobody's identity is guessed or changed during migration.
4. The homepage's second section now displays "Free consultation by
   Dr. Banarsi Das" / "Claim now". It uses the existing app-download/direct-call
   popup, with offer-specific copy and code. Store buttons remain "Coming soon"
   until real links are configured. The existing phone link is unchanged.
5. Assign submitted bookings at `/staff/appointments/{id}` or Django admin ->
   Appointments. Free bookings show a free badge, code and only the offer doctor
   as eligible. No payment needed. Changing the doctor to someone else is rejected.
6. To end the offer, uncheck **Is active**, set an expiry, or delete the offer.
   The homepage/app discovery stops advertising it. Honour already-submitted
   bookings. Offer expiry is a redemption deadline, not the consultation date.
   No new environment variables or external payment configuration are required.
