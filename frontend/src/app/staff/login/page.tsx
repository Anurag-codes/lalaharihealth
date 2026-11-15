import { Suspense } from "react";
import { LoginForm } from "@/components/staff/LoginForm";
import { Spinner } from "@/components/staff/ui";

export default function StaffLoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <Suspense fallback={<Spinner />}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
