import Image from "next/image";
import Link from "next/link";
import { ArrowUpRight, BookOpen } from "lucide-react";
import { blogDate, type BlogSummary } from "@/lib/blogs";

export function BlogCard({ post }: { post: BlogSummary }) {
  return (
    <article className="flex min-w-0 flex-col overflow-hidden rounded-2xl border border-black/10 bg-white shadow-sm transition-shadow hover:shadow-lg">
      <Link href={`/blogs/${post.slug}`} tabIndex={-1} aria-hidden="true" className="block aspect-video overflow-hidden bg-primary-light">
        {post.cover_image ? (
          <Image src={post.cover_image} alt="" width={800} height={450} unoptimized className="h-full w-full object-cover" />
        ) : (
          <span className="flex h-full items-center justify-center"><BookOpen className="h-12 w-12 text-primary" /></span>
        )}
      </Link>
      <div className="flex flex-1 flex-col p-5 sm:p-6">
        <div className="flex flex-wrap items-center gap-3 text-xs font-semibold text-primary-darker">
          <span className="rounded-full bg-primary-light px-3 py-1">{post.kind === "external" ? "From around the web" : "LalahariHealth article"}</span>
          <time dateTime={post.published_at}>{blogDate(post.published_at)}</time>
        </div>
        <h3 className="mt-4 break-words font-heading text-xl font-semibold leading-snug text-ink">
          <Link href={`/blogs/${post.slug}`} className="hover:text-primary-darker">{post.title}</Link>
        </h3>
        <p className="mt-3 line-clamp-3 break-words text-sm leading-relaxed text-ink/65">{post.description}</p>
        {post.author_name && <p className="mt-3 text-xs text-ink/60">By {post.author_name}</p>}
        <Link href={`/blogs/${post.slug}`} aria-label={`Read blog: ${post.title}`} className="mt-auto inline-flex min-h-11 items-center gap-2 pt-5 text-sm font-semibold text-primary-darker">
          Read blog <ArrowUpRight className="h-4 w-4" />
        </Link>
      </div>
    </article>
  );
}
