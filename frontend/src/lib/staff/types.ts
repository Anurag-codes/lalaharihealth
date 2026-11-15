export type StaffUser = {
  id: number;
  username: string;
  full_name: string;
  email: string;
  is_superuser: boolean;
};

export type AppointmentStatus =
  | "pending"
  | "awaiting_payment"
  | "finding_doctor"
  | "confirmed"
  | "completed"
  | "cancelled";

export type PaymentStatus = "not_required" | "not_started" | "pending" | "success" | "failed" | "refunded";

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type StaffSummary = {
  today_date: string;
  needs_doctor: number;
  overdue: number;
  today_count: number;
  awaiting_payment: number;
  completion_pending: number;
  upcoming_confirmed: number;
};

export type DoctorRef = { id: number; name: string; specialization: string };

export type AppointmentItem = {
  booker_account_deleted: boolean;
  doctor_account_deleted: boolean;
  coupon_code: string;
  free_consultation_doctor: number | null;
  id: number;
  appointment_number: string;
  status: AppointmentStatus;
  status_label: string;
  slot_time: string;
  schedule_date: string;
  schedule_time: string;
  date_display: string;
  patient_name: string;
  patient_phone: string;
  patient_relation: string;
  patient_relation_label: string;
  booker: { id: number; name: string; phone: string; email?: string };
  category: { speciality_id: number | null; name: string; title: string };
  mode: string;
  mode_label: string;
  doctor: DoctorRef | null;
  payment_status: PaymentStatus;
  amount: string | number | null;
  currency: string;
  amount_display: string;
  created_at: string;
  is_overdue: boolean;
  can_assign: boolean;
  lock_reason: string | null;
  can_edit_patient: boolean;
  needs_completion_confirmation: boolean;
};

export type AppointmentDetail = AppointmentItem & {
  consultation_id: number | null;
  consultation_status: string | null;
  chief_complaint: string;
  condition_details: string;
  symptoms: string;
  duration_display: string;
  ongoing_medication: boolean | null;
  treatment_details: string;
  patient_age: number | null;
  patient_gender: string;
  patient_gender_label: string;
  family_member_id: number | null;
  payment: {
    id: number;
    status: string;
    method: string;
    amount: string | number;
    currency: string;
    gateway_order_id: string;
    transaction_id: string;
    created_at: string;
  } | null;
  timeline: {
    created_at: string | null;
    information_confirmed_at: string | null;
    paid_at: string | null;
    doctor_assigned_at: string | null;
    completed_at: string | null;
    completion_confirmed_at: string | null;
    completion_confirmed_by: string | null;
    cancelled_at: string | null;
  };
  documents: { id: number; original_name: string; uploaded_at: string; download_path: string }[];
  calls: {
    id: number;
    mode: string;
    provider: string;
    status: string;
    status_label: string;
    started_at: string | null;
    ended_at: string | null;
    duration_seconds: number | null;
    end_reason: string;
  }[];
  video_room_provisioned: boolean;
};

export type EligibleDoctor = {
  id: number;
  name: string;
  specialization: string;
  speciality_name: string | null;
  experience_years: number | null;
  phone: string;
  is_current: boolean;
  is_available: boolean;
  has_open_slot: boolean;
  conflict: { appointment_id: number; appointment_number: string } | null;
  appointments_that_day: number;
};

export type EligibleDoctorsResponse = { starts_at: string; results: EligibleDoctor[] };

export type StaffDoctor = {
  id: number;
  name: string;
  specialization: string;
  speciality: { id: number; name: string } | null;
  phone: string;
  experience_years: number | null;
  city: string;
  upcoming_appointments: number;
};

export type ScheduleTime = {
  starts_at: string;
  time_display: string;
  is_past: boolean;
  slot_open: boolean;
  slot_id: number | null;
  appointment: { id: number; appointment_number: string; status: AppointmentStatus; patient_name: string } | null;
};

export type DoctorSchedule = { doctor: DoctorRef; date: string; times: ScheduleTime[] };

export type Speciality = { id: number; name: string };
