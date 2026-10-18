import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { BlogCard } from "@/components/blogs/BlogCard";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { BlogApiError, getBlogs } from "@/lib/blogs";
import { BlogSection } from "@/components/sections/BlogSection";

export const metadata: Metadata = {
  title: "Blogs | LalahariHealth",
  description: "Read LalahariHealth articles and discover healthcare resources and videos.",
};

export default async function BlogsPage({ searchParams }: {
  searchParams: Promise<{ page?: string | string[] }>;
}) {
  const query = await searchParams;
  if (query.page !== undefined && (typeof query.page !== "string" || !/^[1-9]\d*$/.test(query.page))) notFound();
  const currentPage = Number(query.page ?? 1);
  if (!Number.isSafeInteger(currentPage)) notFound();

  let data;
  try {
    data = await getBlogs(currentPage);
  } catch (error) {
    if (!(error instanceof BlogApiError)) throw error;
    if (error.status === 404) notFound();
    console.error("Additional blogs could not be loaded:", error);
  }

  return (
    <Container className="py-12 sm:py-20">
      <Eyebrow>Insights and resources</Eyebrow>
      <h1 className="mt-5 font-heading text-3xl font-bold text-ink sm:text-5xl">Our blogs</h1>
      <p className="mt-4 max-w-2xl text-base leading-relaxed text-ink/70 sm:text-lg">
        Explore our original articles alongside selected blogs and videos from around the web.
        Content is for general information, not a personal diagnosis or a substitute for medical care.
      </p>
      {currentPage === 1 && <BlogSection showReadMore={false} />}
      <h2 className="mt-12 font-heading text-2xl font-bold text-ink">More from our blog</h2>
      {!data ? (
        <p role="status" className="mt-6 rounded-2xl bg-primary-soft p-8 text-center text-ink/70">
          Additional blogs could not be loaded right now. Please refresh the page to try again.
        </p>
      ) : data.results.length ? (
        <>
          <p className="mt-8 text-sm text-ink/60">{data.count} {data.count === 1 ? "post" : "posts"}</p>
          <div className="mt-6 grid gap-6 md:grid-cols-2 lg:grid-cols-3">{data.results.map((post) => <BlogCard key={post.id} post={post} />)}</div>
          <nav aria-label="Blog pagination" className="mt-12 flex flex-wrap items-center justify-center gap-5 text-sm">
            {data.previous && <Link href={currentPage === 2 ? "/blogs" : `/blogs?page=${currentPage - 1}`} className="rounded-full border border-primary px-5 py-3 font-semibold text-primary-darker">Previous page</Link>}
            <span aria-current="page" className="text-ink/70">Page {currentPage} of {Math.max(1, Math.ceil(data.count / 9))}</span>
            {data.next && <Link href={`/blogs?page=${currentPage + 1}`} className="rounded-full border border-primary px-5 py-3 font-semibold text-primary-darker">Next page</Link>}
          </nav>
        </>
      ) : (
        <p className="mt-10 rounded-2xl bg-primary-soft p-8 text-center text-ink/70">More articles will appear here as they are published. Please check back soon.</p>
      )}
    </Container>
  );
}
