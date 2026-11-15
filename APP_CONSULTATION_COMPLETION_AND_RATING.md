# App: complete a consultation and rate it

All requests are authenticated with the app's backend access token: `Authorization: Bearer <access>`.

## 1. Doctor app: after the video call

1. **Join:** `POST /api/v1/doctors/me/appointments/{appointment_id}/video/join/` returns `call_id`.
2. **Report the call end:** `PATCH /api/v1/doctors/me/appointments/{appointment_id}/calls/{call_id}/`
   ```json
   {"status": "completed", "started_at": "2026-11-15T10:31:00+05:30", "ended_at": "2026-11-15T10:43:30+05:30", "end_reason": "doctor_ended"}
   ```
   Other outcomes are `failed`, `missed` and `cancelled`. Reporting a call does **not** complete the consultation.
3. **Mark the consultation complete.** Show a "Complete consultation" button and use **one** of these:
   - **With prescription (recommended):** `PUT /api/v1/doctors/me/consultations/{consultation_id}/record/`
     ```json
     {"diagnosis": "Acute pharyngitis", "prescriptions": [], "doctor_notes": "", "follow_up_date": null, "follow_up_notes": "", "mark_completed": true}
     ```
     `prescriptions` replaces the whole list. Send `mark_completed: false` to save a draft.
     Every field is optional (for example `{"mark_completed": true}` alone), but each PUT replaces the typed record, so send the full record if one was typed.
   - **Without a record:** `PATCH /api/v1/doctors/me/appointments/{appointment_id}/`, with body `{"status": "completed"}`.
   - **Handwritten prescription (optional, any time before or after completing):** see section 3.
4. **Result:** the response returns `status: "completed"` and `completed_at`. The patient gets a `consultation_completed` notification, and the consultation counts in earnings.
   - Allowed only for confirmed appointments assigned to this doctor, from 5 minutes before the start time.
   - Repeating the request is safe, and a completed consultation cannot be reopened.
   - Staff confirm completion separately, shown as `completion_confirmed`.

## 2. Patient app: rate after completion

`consultation_id` comes from the case or appointment that the patient opened.

- **Check:** `GET /api/v1/consultations/{consultation_id}/review/`
  ```json
  {"consultation_id": 41, "can_review": true, "reason": "", "review": null}
  ```
  - Show the 1–5 star form while `can_review` is `true`. Otherwise show `reason`, for example "not completed yet".
  - `review` holds the patient's saved rating; use it to pre-fill the form when they edit.
- **Submit or edit:** `PUT /api/v1/consultations/{consultation_id}/review/`
  ```json
  {"rating": 5, "feedback": "Doctor explained clearly."}
  ```
  - `rating` is required, as a whole number from 1 to 5.
  - `feedback` is optional, up to 1000 characters. It can be omitted or sent as `""`.
  - The response has the same shape as GET, with `review: {rating, feedback, created_at, updated_at}`.
  - Sending again edits the existing rating.

Rating rules:
- Rating is allowed only after the doctor marks the consultation completed. Cancelled consultations can't be rated.
- There is one rating per consultation. The booking account or the family member who received the consultation can rate, but only the first account to rate can edit it.
- Errors:
  - `400` for invalid input or when rating isn't allowed (`detail` explains why).
  - `401` when not signed in.
  - `403` when the account isn't a patient.
  - `404` when the consultation isn't the user's.
- Ratings update the doctor's `average_rating`. Staff can view them in Django admin under **Consultation reviews**.

## 3. Doctor app: upload a handwritten prescription (optional)

The doctor can type the record (section 1), upload photos of the written prescription, or both. Nothing is mandatory.

- **Upload:** `POST /api/v1/doctors/me/consultations/{consultation_id}/record/documents/`
  - `multipart/form-data`; repeat the field `files` once per page/photo.
  - JPG, PNG or PDF, up to 10 MB each; 1–10 files per request, 20 per consultation.
  - Allowed once the appointment is confirmed, and also after completion (for corrections).
  - `201` returns every prescription photo of the consultation:
    ```json
    [{"id": 3, "original_name": "page-1.jpg", "uploaded_at": "2026-11-15T10:44:00+05:30", "download_url": "https://api.lalaharihealth.com/api/v1/consultations/41/prescription-documents/3/download/"}]
    ```
- **List:** `GET` the same URL. The record GET/PUT responses also include `prescription_documents`.
- **Delete one:** `DELETE /api/v1/doctors/me/consultations/{consultation_id}/record/documents/{document_id}/`, which returns `204`.
- **Complete:** after uploading, complete as in section 1 step 3 (photos only: use the `PATCH` with `{"status": "completed"}`, or the record `PUT` with `{"mark_completed": true}` if nothing was typed).
- **Patient app:** `GET /api/v1/patients/medical-records/{consultation_id}/` returns `prescription_documents` once the consultation is completed (empty before). Open each `download_url` **with the Bearer header**; files are private.
- Errors: `400` for a bad file type/size, too many files, or an appointment that is not confirmed/completed; `403` when not a verified doctor; `404` when the consultation isn't assigned to this doctor.
