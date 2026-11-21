# Design System — URL CHECKER / Analyst Console

The interface is a quiet, instrument-grade triage console. Its job is to make one
URL verdict feel measured, readable and inspectable. Structure comes from
alignment, spacing and hairline rules — not from stacked decorative cards.

Branding is **URL CHECKER** everywhere: page `<title>`, desktop rail, mobile top
bar, hero attribution and footer. The logo is a black rounded-square mark with a
clean white `//` inside it. The favicon repeats that mark.

The **navigation is the only frosted surface** on the page. Both the desktop rail
and the mobile top bar use a semi-transparent white background with
`backdrop-filter: blur(18px) saturate(150%)`. No card, panel, button or report
element uses a blur or glass effect.

Backend modules, routes and the `/api/predict` contract are unchanged.

## Rejected directions

Do not reintroduce: the Instagram app shell (stories, post cards, social actions,
bottom tabs), the warm radar, the near-black instrument theme, the Signal Field
Guide paper look, the old `Signal` / `RS CHECKER` name, section number indicators,
the hero badge/description/metrics bar, a Known Limitations block, or footer tech
badges.

## Stack and build contract

- React 18 + Vite. Source lives in `src/`; production build goes to `website/`.
- `vite.config.js` uses `base: './'`, `outDir: 'website'`, `emptyOutDir: false`
  and a dev proxy for `/api` → `http://127.0.0.1:8000`.
- FastAPI keeps serving `website/` through `StaticFiles`.
- The old static DOM/global-hook contract (`js/app.js`, canvas ids, globals) is
  superseded and must not be reintroduced.

## Layout

Exactly six top-level regions, none numbered:

1. `#hero` — headline and two actions only. No badge, no description, no stats.
2. `#how-to` — three single-word steps: Paste, Scan, Verify.
3. `#scan` — one address field, one Check button, three sample links.
4. `#output` — empty state, then the report.
5. `#quote` — one closing pull quote.
6. `<footer id="footer">` — section links and `Developer RS ARUNKUMAR`.

Desktop (≥861px): fixed 210–244px left rail with wordmark and section links.
Mobile: sticky frosted top bar with a horizontal section scroller.

## Tokens

```css
--canvas:        #11161c;  /* deep charcoal */
--surface:       #192129;
--surface-sunk:  #222c36;
--ink:           #f2f5f7;
--ink-soft:      #c1ccd5;
--ink-muted:     #8b9aa7;
--line:          #2c3843;
--line-strong:   #40505e;
--signal:        #e0a33c;  /* warm amber */
--signal-deep:   #c3861f;
--signal-wash:   #382b16;
--safe:          #4ec38f;
--safe-wash:     #16342a;
--risk:          #e0705f;
--risk-wash:     #3b2220;

--font-display:  'Sora', 'Segoe UI', system-ui, sans-serif;
--font-body:     'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-data:     ui-monospace, SFMono-Regular, 'Cascadia Code', Consolas, monospace;
```

Monospace is reserved for addresses, scores and weights — functional data, not
decoration. Sample links use an italic Sora style instead. The accent is a
muted warm amber; neon blue, pink and purple are never used.

## Report anatomy

On submit the report shows: authoritative verdict, phishing probability,
confidence, decision threshold, a risk bar, three detail groups (Address
structure, Domain features, Heuristics), ranked character signals, collapsible
supporting context, and model provenance. Address facts are derived from the
submitted URL only; the UI states that certificate validity and live redirects
are not verified here.

## Type and motion

- Display: Sora 600/700 with tight tracking. Body: Inter 400/500/600.
- Labels are short and plain; no decorative section numbers anywhere.
- Reveal-on-scroll for a few blocks; report entry is a single restrained move.
- `prefers-reduced-motion: reduce` collapses all transitions and makes every
  revealed element visible immediately.

## QA gates

- `npm run build` succeeds; only current hashed assets remain in `website/assets/`.
- Zero horizontal overflow at 1440 / 1024 / 820 / 768 / 390 / 320 and zero console errors.
- Blur appears only on the visible navigation bar at every width.
- Six regions, no numbered headings, no Instagram artifacts, no Known Limitations text.
- `google.com` → SAFE `0.67%`, confidence `99.3%`, threshold `0.50`, 6 signals.
- Phishing sample → PHISHING `99.97%`; report class switches to `is-risk`.
