# metablog-theme

The Hugo theme and tooling behind [Metamodel.blog](https://metamodel.blog) —
a heavily customized version of the
[Blist](https://github.com/apvarun/blist-hugo-theme) theme, restructured
so that a site builds with **only the plain Hugo binary**: no npm, no
Tailwind toolchain, no Hugo extended edition, no theme submodule. The
CSS is pre-compiled and vendored; everything else is vanilla Hugo
templates and a little dependency-free JavaScript.

This repository is a **read-only mirror**, updated automatically from
the (private) repo of the live blog whenever its theme code changes.
Issues are welcome; pull requests can't be merged here directly but
will be applied upstream.

## Quick start

Requires [Hugo](https://gohugo.io) v0.164+ (standard edition is fine).

```bash
git clone https://github.com/mitotic/metablog-theme.git myblog
cd myblog
hugo server -D        # sample site at http://localhost:1313
```

The repo is a complete runnable Hugo site with sample posts. To make
it yours: edit `config.toml` (title, author, baseurl, social links),
replace `content/posts/` with your posts, and replace the placeholder
images in `static/`.

## Features

- Card-based home page (recent + featured posts with thumbnails,
  titles, and subtitles), paginated post list, tag pages
- Dark mode toggle, client-side search (Fuse.js), RSS + JSON feeds
- **Bluesky comments**: add `Bskypost: <bsky.app post URL>` to a
  post's front matter and the replies to that Bluesky post render as
  the comment thread (fetched client-side from the public Bluesky
  AppView; no server, no API key). Moderation via Bluesky threadgates
  and reply-hiding
- giscus (GitHub Discussions) comments as a dormant fallback
  (`GiscusComments: true` + `[params.giscus]`)
- **Archived comments**: `tools/remark2data.py` converts a Remark42
  backup into `data/archived_comments.json`, rendered statically
  below posts — useful when migrating off a self-hosted comment system
- Unlisted posts (`Unlisted: true`): published and reachable by URL
  but excluded from listings, RSS, and the sitemap
- Social share cards (OpenGraph/Twitter), tweet embeds (`Tweetid:`),
  KaTeX math (`math: true`), collapsible `detail-tag` shortcode
- eBook generation: `blog2book.py` + Pandoc turn posts into
  ePUB/PDF downloads

## Front matter reference

```yaml
---
Author: "Your Name"
Title: "Post title"
Date: 2026-07-15
Description: "Subtitle shown under the title and on cards."
Tags: ["tag1", "tag2"]
Thumbnail: /posts/my-post/image/cover.jpg   # above title + listing card
Card: /posts/my-post/image/card.jpg         # social share image (2:1)
Featured: true          # show in Featured section of home page
Draft: true             # local preview only (hugo server -D)
Unlisted: true          # deployed but hidden from listings/RSS/sitemap
math: true              # KaTeX
Bskypost: https://bsky.app/profile/you.bsky.social/post/3k...  # comments
Aliases: ["/posts/old-slug/"]               # redirects from old URLs
---
```

Posts are page bundles: `content/posts/<slug>/index.md` plus an
`image/` subdirectory (a bare `<slug>.md` also works).

## Repository layout

```
layouts/       Templates (base, single, list, home, partials, shortcodes)
assets/css/    Pre-compiled vendored CSS + additions.css for new styles
assets/js/     search.js + fuse.min.js, bsky-comments.js
archetypes/    Front matter template for hugo new
static/        Fonts and sample images (replace with yours)
content/       Sample posts and pages (replace with yours)
tools/         remark2data.py (Remark42 -> archived comments JSON)
blog2book.py   eBook (ePUB/PDF) generator, with pandoc/ support files
config.toml    Sample configuration
```

Note on CSS: the vendored `styles-compiled.css` was produced by the
original Blist Tailwind build and then frozen; unused Tailwind classes
were purged. Style new markup with plain CSS in `assets/css/additions.css`
rather than Tailwind utility classes that may not be in the bundle.

## Deployment

The site builds to static files (`hugo` → `public/`) and runs anywhere
static hosting works. The live blog deploys on Cloudflare Workers
(static assets) with build command `hugo`, deploy command
`npx wrangler deploy`, and `HUGO_VERSION=0.164.0`; a sample
`wrangler.jsonc` for that setup:

```jsonc
{
  "name": "myblog",
  "compatibility_date": "2026-07-01",
  "assets": { "directory": "./public", "not_found_handling": "404-page" }
}
```

GitHub Pages, Netlify, etc. work equally well — there is no build
dependency beyond the hugo binary.

## Credits and license

Based on [Blist](https://github.com/apvarun/blist-hugo-theme) by
Varun A P. Customizations by R. Saravanan for
[Metamodel.blog](https://metamodel.blog).
[MIT](LICENSE).
