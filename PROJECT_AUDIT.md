# ArchScope V4 Project Audit

## Summary

ArchScope V4 is a functioning Flask prototype for browsing a demo architecture catalogue, searching Brave when configured, and saving a browser-local research board. The core demo routes work, but the application is not ready to represent a production architecture-research product.

## Findings

### High priority

1. **Board-import cross-site scripting (XSS) risk**
   - `static/app.js` accepts arbitrary board objects from an imported JSON file and later inserts `id` values into inline `onclick` JavaScript.
   - An imported value containing JavaScript-string syntax can break out of that handler and execute code in the visitor's browser.
   - Avoid inline event handlers. Render buttons with DOM APIs and attach event listeners; validate imported fields against an explicit schema.

2. **Project assets are generated placeholders, not research assets**
   - `/api/project/<pid>` creates assets from each project's count fields rather than retrieving real plans, sections, photographs, or details.
   - The generated entries use generic names such as `Plans 1`, a generic source label, and Google-search links. This does not provide genuine source attribution or reliable research material.
   - Replace this with a persistent asset catalogue containing verified source URLs, licences, attribution, thumbnails, metadata, and project relationships.

### Medium priority

3. **The catalogue's “Live + catalogue” status is inaccurate**
   - `/api/projects` always returns only the local `DEMO` data.
   - It labels the response `hybrid` merely because `BRAVE_API_KEY` exists, and the frontend displays “Live + catalogue.”
   - Either integrate live catalogue data into this endpoint or label it accurately as a demo catalogue.

4. **A malformed saved board can stop all frontend initialization**
   - Startup immediately runs `JSON.parse(localStorage.getItem('archscopeBoard') || '[]')` without error handling.
   - If browser storage is corrupted or manually edited, JavaScript stops before the project grid is loaded.
   - Parse storage in `try/catch`, reset invalid data safely, and notify the user.

5. **Saved local search results cannot be reopened as projects**
   - Local search results are reduced to `{ id, title, type, thumbnail, url }` before they are saved.
   - The board only provides “Open project” when an item has `architect`; therefore, these saved local projects lose that action.
   - Preserve a project identifier/type explicitly and use it to choose the open-project action.

6. **Live-search calls have no cache, throttling, or abuse controls**
   - Every eligible search may call Brave's web and image APIs, each with a 15-second timeout.
   - Repeated requests can consume API quota and occupy application workers when the upstream service is slow.
   - Add request validation, per-client rate limits, short-lived caching, upstream timeout/error metrics, and a bounded concurrency strategy.

7. **Search quality is simplistic and accepts invalid modes**
   - Local matches use an “any query word” check, which can produce broad false positives for multi-word queries.
   - Invalid `mode` values silently skip live-search tasks rather than returning a validation error.
   - Validate query parameters and use token scoring, phrase matching, or a proper search index.

### Maintenance and delivery risks

8. **No automated test suite**
   - The repository has no API, frontend, or integration tests.
   - Add tests for project filtering, project 404s, search modes/fallbacks, board import validation, and browser interactions.

9. **Dependencies are unpinned**
   - `requirements.txt` lists package names without versions.
   - Builds are not reproducible and may break as Flask, Requests, or Gunicorn release incompatible versions.
   - Pin compatible version ranges or use a lockfile and a repeatable CI build.

10. **Confusing local directory layout**
    - The real Git repository is nested under `archscope-v4/archscope-v4` in the supplied workspace.
    - An older `archscope-v3/archscope-v2` copy is also present locally. It is ignored by Git, but it can cause developers to run or edit the wrong version.
    - Keep one canonical project directory and exclude virtual environments and retired copies from distribution archives.

## Validation performed

- Python syntax compilation passed for `app.py`.
- JavaScript syntax checking passed for `static/app.js`.
- Flask test-client checks passed for `/health`, `/api/projects`, filtering, known/unknown project lookup, search fallback, and static file serving when launched from the project directory.
- The checked routes confirm that the demo application operates, but they do not validate Brave live-search results because those depend on configured external credentials.

## Recommended order of work

1. Fix imported-board XSS and resilient local-storage loading.
2. Correct the misleading catalogue/live-search labels.
3. Replace synthetic project assets with real, attributable records.
4. Add API/frontend tests and dependency pinning.
5. Add caching, rate limiting, and better search semantics before public deployment.
