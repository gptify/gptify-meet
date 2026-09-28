# Instructions for the implementation agent

Review the existing repository before changing architecture. Preserve the approved design in design-source.html while mapping it into the project's component and routing system. Do not replace an existing app with the standalone preview wrapper.

First report what already exists, what is partial, and what is absent, citing file paths and relevant tests. Separate verified defects from assumptions. Do not claim backend functionality exists because it appears in this mockup.

## Product review matrix

1. Audio capture: verify microphone AND system loopback on Windows/macOS, permissions, device switching, headphones, sample rates, pause/resume, long sessions, and recovery after sleep/crashes. Confirm the actual platform implementation rather than assuming a library name guarantees loopback support.
2. Transcription: identify model, language support, timestamps, speaker attribution, streaming/batch behavior, model installation and integrity checks. Evaluate Uzbek, mixed Uzbek/Russian, names, amounts, dates, and noisy audio with representative recordings.
3. Meeting intelligence: trace transcription to the actual summarizer. Verify structured decisions/tasks/owners/dates/risks; preserve unknown owners and dates rather than inventing them. Link generated claims to source text where possible.
4. Privacy: trace every outbound network path, including AI providers, analytics, error logs, licensing, updates, model downloads, and Telegram. Distinguish meeting content from operational metadata. Confirm local mode never silently falls back to cloud inference.
5. Storage: identify audio/transcript/database paths, access controls, credential storage, deletion behavior, retention, export, and backups. Verify whether any encryption claim is true. Check sensitive content in logs and crash reports.
6. Telegram: verify setup, recipient identity, token protection, exact-text preview, payload scope, formatting, length handling, retry behavior, and duplicate prevention. Make it clear that exported content leaves the device.
7. Import and archive: verify MP3/WAV/M4A decoding, large/corrupt files, progress, cancellation, indexing, search correctness, and persistence after restart.
8. Desktop delivery: verify Tauri capability scope and IPC validation, frontend build compatibility, model resource use, first-run onboarding, installer signing, supported hardware/OS versions, updates, and accessibility.
9. Commercial readiness: verify trial activation/expiry, license validation and offline grace, actual payment providers, pricing consistency, and enterprise scope. Distinguish shipped features from roadmap claims.
10. Landing page: replace demo actions, add metadata/social previews, real downloads or waitlist, privacy/support/legal routes, mobile/accessibility checks, and hosting configuration. Publish only factual claims supported by the product review.

## Report format

- Brief implementation overview with evidence.
- Severity-ranked findings: user impact, reproducer or code evidence, recommended fix.
- Brief-to-code matrix: implemented / partial / missing / unverified.
- Short release-blocker list and next implementation steps.

## Definition of an end-to-end working product

On supported hardware, install and activate the app, record a real consented meeting with microphone and system audio, obtain a usable Uzbek transcript and structured summary locally, restart and recover the stored meeting, inspect source text, and export only reviewed content to an explicitly chosen Telegram destination. Separately verify imports, failure recovery, retention/deletion, and network behavior. Do not mark this complete using simulated data alone.
