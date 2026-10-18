import { API_BASE_URL } from "@/lib/api";
import { cache } from "react";

export type BlogVideo = { kind: "embed" | "file"; url: string };
export type BlogSummary = {
  id: number;
  title: string;
  slug: string;
  description: string;
  kind: "external" | "article";
  cover_image: string | null;
  cover_alt: string;
  author_name: string;
  published_at: string;
};
export type BlogBlock = {
  id: number;
  position: number;
  kind: "heading" | "paragraph" | "image" | "video";
  heading_level: "h2" | "h3";
  text: string;
  image: string | null;
  image_alt: string;
  caption: string;
  video: BlogVideo | null;
};
export type BlogDetail = BlogSummary & {
  source_url: string;
  source_video: BlogVideo | null;
  blocks: BlogBlock[];
};
export type BlogPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: BlogSummary[];
};

export class BlogApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
    this.name = "BlogApiError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isWebUrl(value: unknown): value is string {
  if (typeof value !== "string") return false;
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password;
  } catch {
    return false;
  }
}

function isOptionalImage(value: unknown): value is string | null {
  return value === null || value === "" || isWebUrl(value);
}

function isVideo(value: unknown): value is BlogVideo | null {
  if (value === null) return true;
  if (!isRecord(value) || !isWebUrl(value.url)) return false;
  const url = new URL(value.url);
  if (value.kind === "file") return url.protocol === "https:" && url.pathname.toLowerCase().endsWith(".mp4");
  return value.kind === "embed" && url.protocol === "https:" && (
    (url.hostname === "www.youtube-nocookie.com" && /^\/embed\/[A-Za-z0-9_-]{11}$/.test(url.pathname)) ||
    (url.hostname === "player.vimeo.com" && /^\/video\/\d+$/.test(url.pathname))
  );
}

function isSummary(value: unknown): value is BlogSummary {
  return isRecord(value) && Number.isSafeInteger(value.id) &&
    typeof value.title === "string" && typeof value.slug === "string" && /^[a-zA-Z0-9_-]+$/.test(value.slug) &&
    typeof value.description === "string" && ["external", "article"].includes(String(value.kind)) &&
    isOptionalImage(value.cover_image) && typeof value.cover_alt === "string" &&
    typeof value.author_name === "string" && typeof value.published_at === "string" &&
    Number.isFinite(Date.parse(value.published_at));
}

function isBlock(value: unknown): value is BlogBlock {
  return isRecord(value) && Number.isSafeInteger(value.id) && Number.isSafeInteger(value.position) &&
    ["heading", "paragraph", "image", "video"].includes(String(value.kind)) &&
    ["h2", "h3"].includes(String(value.heading_level)) && typeof value.text === "string" &&
    isOptionalImage(value.image) && typeof value.image_alt === "string" &&
    typeof value.caption === "string" && isVideo(value.video) &&
    (value.kind !== "image" || isWebUrl(value.image)) &&
    (value.kind !== "video" || value.video !== null);
}

function isDetail(value: unknown): value is BlogDetail {
  if (!isRecord(value)) return false;
  const { source_url, source_video, blocks } = value;
  return typeof source_url === "string" && (source_url === "" || isWebUrl(source_url)) &&
    isVideo(source_video) && Array.isArray(blocks) && blocks.every(isBlock) &&
    isSummary(value) && (value.kind !== "external" || isWebUrl(source_url));
}

async function requestBlogs(path: string): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/blogs/${path}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    });
  } catch (error) {
    if (!(error instanceof TypeError) &&
      !(error instanceof Error && ["AbortError", "TimeoutError"].includes(error.name))) throw error;
    throw new BlogApiError(`Could not reach the blog service: ${error instanceof Error ? error.message : "Network error"}`);
  }
  if (!response.ok) throw new BlogApiError("The blog service returned an error.", response.status);
  try {
    return await response.json();
  } catch (error) {
    if (!(error instanceof SyntaxError)) throw error;
    throw new BlogApiError("The blog service returned an invalid response.");
  }
}

export async function getBlogs(page = 1, pageSize = 9): Promise<BlogPage> {
  const data = await requestBlogs(`?page=${page}&page_size=${pageSize}`);
  if (!isRecord(data) || typeof data.count !== "number" || !Number.isSafeInteger(data.count) || data.count < 0 ||
    !(data.next === null || isWebUrl(data.next)) || !(data.previous === null || isWebUrl(data.previous)) ||
    !Array.isArray(data.results) || !data.results.every(isSummary)) {
    throw new BlogApiError("The blog service returned an invalid blog list.");
  }
  return { count: data.count, next: data.next, previous: data.previous, results: data.results };
}

export const getBlog = cache(async (slug: string): Promise<BlogDetail | null> => {
  if (!/^[a-zA-Z0-9_-]+$/.test(slug)) return null;
  let data: unknown;
  try {
    data = await requestBlogs(`${encodeURIComponent(slug)}/`);
  } catch (error) {
    if (error instanceof BlogApiError && error.status === 404) return null;
    throw error;
  }
  if (!isDetail(data)) {
    throw new BlogApiError("The blog service returned an invalid article.");
  }
  return data;
});

export function blogDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Kolkata",
  }).format(new Date(value));
}
