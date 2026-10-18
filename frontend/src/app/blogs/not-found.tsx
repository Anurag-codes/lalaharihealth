import Link from "next/link";
import { Container } from "@/components/ui/Container";

export default function BlogNotFound() {
  return (
    <Container className="max-w-2xl py-16 text-center">
      <h1 className="font-heading text-3xl font-bold text-ink">Blog not found</h1>
      <p className="mt-4 text-ink/70">This article or page does not exist, or is not currently published.</p>
      <Link href="/blogs" className="mt-6 inline-flex min-h-11 items-center font-semibold text-primary-darker underline underline-offset-4">Back to all blogs</Link>
    </Container>
  );
}
