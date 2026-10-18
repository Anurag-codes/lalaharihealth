import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowUpRight } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { BlogContent, BlogVideoPlayer } from "@/components/blogs/BlogContent";
import { blogDate, getBlog } from "@/lib/blogs";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const post = await getBlog((await params).slug);
  if (!post) return { title: "Blog not found | LalahariHealth" };
  return {
    title: `${post.title} | LalahariHealth`,
    description: post.description,
    openGraph: {
      type: "article",
      title: post.title,
      description: post.description,
      publishedTime: post.published_at,
      ...(post.cover_image ? { images: [{ url: post.cover_image, alt: post.cover_alt }] } : {}),
    },
  };
}

export default async function BlogPage({ params }: Props) {
  const post = await getBlog((await params).slug);
  if (!post) notFound();

  return (
    <Container className="max-w-4xl py-10 sm:py-16">
      <Link href="/blogs" className="inline-flex min-h-11 items-center text-sm font-semibold text-primary-darker underline underline-offset-4">Back to all blogs</Link>
      <article className="mt-5">
        <header>
          <p className="text-sm font-semibold text-primary-darker">{post.kind === "external" ? "From around the web" : "LalahariHealth article"}</p>
          <h1 className="mt-4 break-words font-heading text-3xl font-extrabold leading-tight text-ink sm:text-5xl">{post.title}</h1>
          <div className="mt-5 flex flex-wrap gap-x-4 gap-y-2 text-sm text-ink/60">
            {post.author_name && <span>By {post.author_name}</span>}
            <time dateTime={post.published_at}>{blogDate(post.published_at)}</time>
          </div>
          <p className="mt-6 whitespace-pre-line break-words text-lg leading-relaxed text-ink/75">{post.description}</p>
          {post.cover_image && <Image src={post.cover_image} alt={post.cover_alt} width={1200} height={675} unoptimized className="mt-8 h-auto max-h-[36rem] w-full rounded-2xl object-cover" />}
        </header>

        <div className="mt-10">
          {post.kind === "external" ? (
            <div className="space-y-6">
              {post.source_video && <BlogVideoPlayer video={post.source_video} title={post.title} />}
              <div className="rounded-2xl border border-primary/20 bg-primary-soft p-6">
                <h2 className="font-heading text-xl font-semibold text-ink">Explore the original source</h2>
                <p className="mt-3 break-words text-sm leading-relaxed text-ink/70">
                  This resource is published by a third party at {new URL(post.source_url).hostname}.
                  Its views belong to its creator; inclusion does not imply endorsement of LalahariHealth.
                </p>
                <a href={post.source_url} target="_blank" rel="noopener noreferrer" className="mt-4 inline-flex min-h-11 items-center gap-2 font-semibold text-primary-darker underline underline-offset-4">
                  {post.source_video ? "Watch the original video" : "Visit the original source"} <ArrowUpRight className="h-4 w-4 shrink-0" />
                </a>
              </div>
            </div>
          ) : <BlogContent blocks={post.blocks} />}
        </div>
        <p className="mt-12 border-t border-black/10 pt-6 text-sm leading-relaxed text-ink/60">
          This content is for general information, not individual medical advice or a diagnosis.
          Do not delay emergency care or change prescribed treatment based on a blog or video.
          Discuss your personal situation with a qualified clinician.
        </p>
      </article>
      <div className="mt-8"><Link href="/blogs" className="inline-flex min-h-11 items-center font-semibold text-primary-darker underline underline-offset-4">Read more blogs</Link></div>
    </Container>
  );
}
