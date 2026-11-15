"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Eye, EyeOff, HeartPulse, Loader2, LogIn } from "lucide-react";
import { flattenApiErrors } from "@/lib/staff/client";
import { ErrorAlert, btnClasses, inputClasses, labelClasses } from "@/components/staff/ui";

export function safeStaffNext(next: string | null) {
  if (!next || next.startsWith("//") || next.includes("\\")) return "/staff";
  const isStaff = next === "/staff" || next.startsWith("/staff/") || next.startsWith("/staff?");
  if (!isStaff || next.startsWith("/staff/login")) return "/staff";
  return next;
}

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const destination = safeStaffNext(searchParams.get("next"));

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);

  // An expired access cookie can often be renewed silently with the refresh cookie.
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/staff/session", { credentials: "same-origin", cache: "no-store", signal: controller.signal })
      .then((res) => {
        if (res.ok) router.replace(destination);
        else setCheckingSession(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) setCheckingSession(false);
      });
    return () => controller.abort();
  }, [router, destination]);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!username.trim() || !password) {
      setErrors(["Enter your username and password."]);
      return;
    }
    setSubmitting(true);
    setErrors([]);
    try {
      const res = await fetch("/api/staff/login", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ username: username.trim(), password }),
      });
      if (res.ok) {
        setPassword("");
        router.replace(destination);
        router.refresh();
        return;
      }
      const data: unknown = await res.json().catch(() => null);
      const messages = flattenApiErrors(data);
      setErrors(
        messages.length
          ? messages
          : [res.status === 429 ? "Too many attempts. Please wait and try again." : "Login failed. Please try again."],
      );
    } catch {
      setErrors(["Network error. Check your connection and try again."]);
    }
    setSubmitting(false);
  }

  return (
    <div className="w-full max-w-sm">
      <div className="mb-6 flex flex-col items-center text-center">
        <HeartPulse className="h-10 w-10 text-primary" aria-hidden />
        <h1 className="mt-2 font-heading text-2xl font-bold text-ink">Staff sign in</h1>
        <p className="mt-1 text-sm text-slate-500">LalahariHealth operations console</p>
      </div>
      <form
        onSubmit={onSubmit}
        noValidate
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        aria-busy={submitting}
      >
        {checkingSession && (
          <p role="status" className="flex items-center gap-2 text-xs text-slate-500">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> Checking for an existing session…
          </p>
        )}
        <ErrorAlert messages={errors} />
        <div>
          <label htmlFor="staff-username" className={labelClasses}>
            Username
          </label>
          <input
            id="staff-username"
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className={inputClasses}
            aria-invalid={errors.length > 0 && !username.trim()}
          />
        </div>
        <div>
          <label htmlFor="staff-password" className={labelClasses}>
            Password
          </label>
          <div className="relative">
            <input
              id="staff-password"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`${inputClasses} pr-10`}
              aria-invalid={errors.length > 0 && !password}
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="absolute inset-y-0 right-0 flex items-center rounded-r-lg px-3 text-slate-500 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              aria-label={showPassword ? "Hide password" : "Show password"}
              aria-pressed={showPassword}
            >
              {showPassword ? <EyeOff className="h-4 w-4" aria-hidden /> : <Eye className="h-4 w-4" aria-hidden />}
            </button>
          </div>
        </div>
        <button type="submit" disabled={submitting} className={btnClasses("primary", "md", "w-full")}>
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <LogIn className="h-4 w-4" aria-hidden />}
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
