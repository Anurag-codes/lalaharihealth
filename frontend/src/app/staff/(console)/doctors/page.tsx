import { Suspense } from "react";
import { DoctorsListView } from "@/components/staff/DoctorsListView";
import { Spinner } from "@/components/staff/ui";

export default function StaffDoctorsPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <DoctorsListView />
    </Suspense>
  );
}
