import { Suspense } from "react";
import { AppointmentsListView } from "@/components/staff/AppointmentsListView";
import { Spinner } from "@/components/staff/ui";

export default function StaffAppointmentsPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <AppointmentsListView />
    </Suspense>
  );
}
