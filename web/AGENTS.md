<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Run `npm run build:ci` before pushing data-fetching or caching changes

CI builds this app with no pipeline artifacts present — `data/current/` is gitignored,
so every `local-json` read returns nothing. A normal `npm run build` on a dev machine
*does* have the artifacts, so it cannot reproduce that. `npm run build:ci` points
`PIPELINE_ROOT` at an empty temp dir to close the gap.

This matters because `cacheComponents: true` (see `next.config.ts`) makes Next
prerender everything it can at build time. A cached read that executes during
prerender will hit the missing artifacts and fail the build — which is exactly how
the Cache Components migration broke CI once while passing locally.

**The rule that keeps it green:** every cached read must sit behind a runtime bail
*before* the `use cache` call, so prerender never reaches it. Either

- `await connection()` — see `app/packs/page.tsx`, or
- the request's own `await params` / `await searchParams` — see `app/cards/page.tsx`.

Ordering is the whole point: the bail has to be awaited *first*. Moving a cached read
above it compiles fine and passes `npm run build` locally, then fails CI.
