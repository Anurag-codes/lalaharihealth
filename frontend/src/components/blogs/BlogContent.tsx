import Image from "next/image";
import { type BlogBlock, type BlogVideo } from "@/lib/blogs";

export function BlogVideoPlayer({ video, title }: { video: BlogVideo; title: string }) {
  if (video.kind === "file") {
    return <video src={video.url} controls playsInline preload="metadata" aria-label={title} className="aspect-video w-full rounded-2xl bg-black object-contain" />;
  }
  return (
    <iframe
      src={video.url}
      title={title}
      className="aspect-video w-full rounded-2xl border-0 bg-black"
      loading="lazy"
      allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; fullscreen"
      referrerPolicy="strict-origin-when-cross-origin"
      allowFullScreen
    />
  );
}

export function BlogContent({ blocks }: { blocks: BlogBlock[] }) {
  return (
    <div className="space-y-7 break-words">
      {blocks.map((block) => {
        if (block.kind === "heading") {
          const Tag = block.heading_level;
          return <Tag key={block.id} className={`pt-4 font-heading font-bold leading-snug text-ink ${Tag === "h2" ? "text-2xl sm:text-3xl" : "text-xl sm:text-2xl"}`}>{block.text}</Tag>;
        }
        if (block.kind === "paragraph") {
          return (
            <div key={block.id} className="space-y-4 text-base leading-8 text-ink/80 sm:text-lg">
              {block.text.split(/\n\s*\n/).map((paragraph, index) => <p key={index} className="whitespace-pre-line">{paragraph}</p>)}
            </div>
          );
        }
        if (block.kind === "image" && block.image) {
          return (
            <figure key={block.id}>
              <Image src={block.image} alt={block.image_alt} width={1200} height={800} unoptimized className="h-auto w-full rounded-2xl" />
              {block.caption && <figcaption className="mt-3 text-center text-sm text-ink/60">{block.caption}</figcaption>}
            </figure>
          );
        }
        if (block.kind === "video" && block.video) {
          return (
            <figure key={block.id}>
              <BlogVideoPlayer video={block.video} title={block.caption || "Article video"} />
              {block.caption && <figcaption className="mt-3 text-center text-sm text-ink/60">{block.caption}</figcaption>}
            </figure>
          );
        }
        return null;
      })}
    </div>
  );
}
