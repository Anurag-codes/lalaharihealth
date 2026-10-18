"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Container } from "@/components/ui/Container";
import { getButtonClasses } from "@/components/ui/Button";

export default function BlogsError({ error, reset }: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => { console.error("Blogs page failed to load:", error); }, [error]);
  return (
    <Container className="max-w-2xl py-16 text-center">
      <h1 className="font-heading text-3xl font-bold text-ink">Blogs are temporarily unavailable</h1>
      <p role="alert" className="mt-4 leading-relaxed text-ink/70">We could not load this content. Please try again shortly.</p>
      <div className="mt-6 flex flex-wrap justify-center gap-4">
        <button type="button" onClick={reset} className={getButtonClasses("primary", "md")}>Try again</button>
        <Link href="/" className={getButtonClasses("outline", "md")}>Return home</Link>
      </div>
    </Container>
  );
}
