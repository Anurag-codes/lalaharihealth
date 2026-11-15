import { notFound } from "next/navigation";
import { AppointmentDetailView } from "@/components/staff/AppointmentDetailView";

export default async function StaffAppointmentDetailPage({ params }: PageProps<"/staff/appointments/[id]">) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();
  return <AppointmentDetailView key={id} id={id} />;
}
