import { Suspense } from "react";
import { notFound } from "next/navigation";
import { DoctorScheduleView } from "@/components/staff/DoctorScheduleView";
import { Spinner } from "@/components/staff/ui";

export default async function StaffDoctorSchedulePage({ params }: PageProps<"/staff/doctors/[id]">) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();
  return (
    <Suspense fallback={<Spinner />}>
      <DoctorScheduleView key={id} doctorId={id} />
    </Suspense>
  );
}
