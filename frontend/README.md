This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

The homepage (`/`) reuses the offer content, hero content, TrustStats,
navbar and footer without an initial popup. Its registration button opens the
existing call/app consultation popup. The sale video autoplays muted, pauses when
out of view or the browser tab is hidden, and resumes from the same position when
visible again. The original full homepage and its initial offer popup are available
at `/get-started`, except DoctorsShowcase, BookConsultation, FAQ and FinalCta,
which are now on the homepage. Navbar Doctors, FAQs and Book Consultation links
point to `/#doctors`, `/#faq` and `/#book-consultation`; other section links
continue to point to `/get-started`.

Only registration is free; consultations are paid. Human-assisted consultation is
₹200, and other consultation fees are confirmed before booking.

## Blog publishing

The homepage uses the existing **Reports, journalism and perspectives on healthcare
costs** section as its blog preview, keeping its three original resource cards,
wording, images and external links unchanged, with a **Read more blogs** button.
Those same three curated resources are always shown on the first `/blogs` page;
they are fixed site content, not editable admin posts. Additional posts are
published from Django admin and listed below them, nine per page.
`/blogs/<slug>` displays each admin-published post.
Navbar and footer include a Blogs link. Additional blog reads are server-rendered from
`NEXT_PUBLIC_API_BASE_URL` without persistent caching, so the API must be reachable
from the Next.js server. API outages show an explicit unavailable state for
additional posts while the three default resources remain visible.
Drafts, future-dated posts and unknown slugs are not public.

Staff write blogs at the backend's `/admin/` under **Blog publishing > Blog posts**:

1. Enter a title, stable URL slug, short description and optional author credit.
2. Choose one of two post types:
   - **External blog / video link:** upload a cover and enter its alt text, then
     enter the original source URL. Do not add content blocks. The detail page
     shows the summary and source link, plus a player for supported video links.
   - **Original article:** upload a cover and enter its alt text, leave the source
     URL empty, and use **Add another Blog block** to compose the article.
     Give each block a distinct position (10, 20, 30, ...) to reorder it.
     Heading blocks support H2/H3, paragraph blocks preserve line breaks, image
     blocks accept an upload with alt text and an optional caption, and video
     blocks accept a supported URL with an optional caption. Add as many as needed.
     Content is plain text, not raw HTML.
3. Save as **Draft** while preparing. Select **Published** and save when ready.
   A cover with alt text is required; original articles need at least one valid
   block. Set a future publication date to schedule visibility. Changing a
   published slug changes its URL (old URLs are not redirected).

Supported video links: YouTube watch, shorts, live, embed or youtu.be links;
public `vimeo.com/<numeric-id>` videos; and HTTPS URLs ending in `.mp4`
(query parameters are allowed). Playback is user-initiated. Only link to material
you have permission to share; provider privacy settings may prevent embedding.
Uploaded blog images are public media, including images attached to drafts; do not
upload private patient information or documents.

Backend setup: run `python manage.py migrate` and create a staff user with blog
permissions (or use an existing superuser). The public API is read-only:

- `GET /api/v1/blogs/?page=1&page_size=9` returns `count`, `next`, `previous`, `results`
  (default 9, maximum 24 posts per page).
- `GET /api/v1/blogs/<slug>/` returns the summary, external source and ordered blocks.

Staff publish only through Django admin; there is no public blog-write endpoint.
On deployment, persist and serve `backend/media/blogs/` via the API's public media
location, and back it up alongside the database. No example posts are published
automatically. Run `python manage.py test apps.blogs` for the publishing/API tests.

The footer links to `/privacy` and `/grievance`. The grievance form saves complaints
through the existing `POST /api/v1/core/contact-messages/` endpoint with a
`[Grievance]` prefix in the message and displays `LH-<id>` after confirmed creation.
Staff can review and mark them resolved in Django admin under Contact messages.
It requires the backend configured by `NEXT_PUBLIC_API_BASE_URL`; it does not send
email notifications. The support email is `care@lalaharihealth.com`, and founder
escalation is available on `9818677599`. Review the privacy wording when service
providers, data practices or retention requirements change.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
