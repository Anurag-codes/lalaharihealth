import type { MetadataRoute } from "next";
import { type BlogSummary, getBlogs } from "@/lib/blogs";
import { SITE_URL } from "@/lib/site";

const STATIC_PATHS = [
  "/",
  "/get-started",
  "/for-doctors",
  "/blogs",
  "/privacy",
  "/grievance",
  "/terms",
  "/refunds",
  "/disclaimer",
];
const BLOG_PAGE_SIZE = 24;
const MAX_BLOG_PAGES = 100;

async function getAllPublishedBlogs(): Promise<BlogSummary[]> {
  const posts: BlogSummary[] = [];
  for (let page = 1; page <= MAX_BLOG_PAGES; page++) {
    const data = await getBlogs(page, BLOG_PAGE_SIZE);
    posts.push(...data.results);
    if (!data.next || data.results.length === 0) break;
  }
  return posts;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const staticEntries: MetadataRoute.Sitemap = STATIC_PATHS.map((path) => ({
    url: path === "/" ? SITE_URL : `${SITE_URL}${path}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: path === "/" ? 1 : 0.7,
  }));

  let blogEntries: MetadataRoute.Sitemap = [];
  try {
    const posts = await getAllPublishedBlogs();
    blogEntries = posts.map((post) => ({
      url: `${SITE_URL}/blogs/${post.slug}`,
      lastModified: new Date(post.published_at),
      changeFrequency: "monthly",
      priority: 0.6,
    }));
  } catch (error) {
    console.error("Blog URLs could not be added to the sitemap:", error);
  }

  return [...staticEntries, ...blogEntries];
}
