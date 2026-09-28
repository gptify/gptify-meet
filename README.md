# GPTify Meet — approved design handoff

## What you have

- `index.html`: standalone browser preview, including the preview runtime. Open in a modern browser. Internet may be required for fonts and preview assets.
- `design-source.html`: editable HTML fragment containing the product-specific HTML, CSS, and JavaScript. This is the source to use when translating the design into production components.
- `AGENT-HANDOFF.md`: implementation instructions and review checklist.

This is an interactive design prototype, not a deployed website or a working desktop product. No package installation or build is needed to inspect the exported preview. The preview contains Landing, Product, Desktop app, and Identity views. Do not treat the preview runtime as the recommended production application architecture.

## Implemented in the prototype

Responsive page layouts, light/dark theme support, view switching, pricing display switching, example transcript navigation, sample-text search, task checkboxes, local privacy details, and simulated recording/sharing states.

## Not implemented

Actual audio capture, transcription, local model execution, meeting persistence, semantic search, Telegram delivery, model downloads, installation packages, authentication, licensing, billing, enterprise deployment, telemetry policy, and production hosting. Retention settings and all meeting data are illustrative. Buttons explicitly indicate simulated or unavailable functionality.

## Approved direction

Keep the clean SaaS design: Inter typography, violet #7051EF, neutral surfaces, compact product controls, rounded audio-bar mark, and prominent product preview. GPTify Meet is a working name; naming and legal clearance remain separate tasks.

Lead with local processing, then prove Uzbek business outputs and user-controlled Telegram sharing. Bot-free recording is a supporting benefit, not a unique market claim.

Hero: “Uchrashuvingiz — o‘zingizda. Natijasi — jamoangizga.”

Local-privacy claims are conditional on the production pipeline actually running locally. The prototype is not evidence of privacy, security, transcription quality, platform compatibility, or offline functionality.

## Known design/implementation follow-ups

- Move preview-only view tabs, demo labels, and design controls out of production pages.
- Map views to real routes and actions; replace simulated CTAs with actual installer or waitlist destinations.
- Audit font sizes (some dense preview labels are below 12px), contrast, focus, touch targets, and keyboard navigation.
- The accent design control changes the primary token only; harmonize derived tint/text tokens if selecting another palette.
- Finish retention, storage-location, deletion, permission, model-download, and failure-state UX.
- Add verified platform requirements, support contacts, legal pages, and evidence-backed privacy details before launch.
- Annual price is 1,900,000 UZS versus 195,000 UZS monthly: savings 440,000 UZS, about 18.8%. Use “about 19%.”

No actual product repository was available when this package was prepared. The checklist is a review plan, not confirmed findings about the product.
