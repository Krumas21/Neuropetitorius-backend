# PROJECT.md

## What is Neuropetitorius?

A B2B AI tutoring API. We sell intelligence-as-a-service to existing educational platforms in the Baltic region. They keep their users, content, branding, and customer relationships. We provide the AI tutor that lives inside their product.

Think of it as **"Stripe for AI tutoring"** — we're invisible to the end user, but we're the engine making the smart conversations happen.

---

## The Pivot

We originally built (and still have all the documentation for) a full B2C consumer tutoring platform. After evaluating market reality and timeline, we pivoted to B2B because:

1. **Faster path to revenue.** Selling 5 platform integrations is faster than acquiring 5,000 individual subscribers.
2. **Lower CAC.** No consumer marketing spend. Sales is direct B2B conversations.
3. **Existing distribution.** Edukamentas already has thousands of students. We don't need to acquire them.
4. **Proof through partners.** Every successful partner integration becomes a case study for the next pitch.
5. **Smaller surface area.** One API is much smaller scope than a full consumer product (web app, mobile app, parent dashboard, teacher portal, billing, support).

---

## Target Customers

**Primary (year 1):**
- **Edukamentas** — Lithuanian K-12 platform, large school presence
- **Eduka** — Lithuanian curriculum-focused EdTech
- **Other Baltic platforms** — Estonia, Latvia equivalents

**Secondary (year 2+):**
- Larger European EdTech platforms
- University-level platforms
- Corporate training platforms

---

## Why Partners Will Pay Us

**The hard problem we solve:** Building a *good* AI tutor is genuinely hard. It's not "just call ChatGPT." A good AI tutor must:

1. **Stay grounded in the actual curriculum** — not give generic Wikipedia answers
2. **Teach via the Socratic method** — not just spoon-feed answers
3. **Handle Lithuanian language properly** — most LLM-powered tools assume English
4. **Be reliable enough for schools to trust** — no hallucinations, no off-topic conversations, no inappropriate content
5. **Integrate cleanly** — partners don't want to rebuild their auth, their UI, or their content pipeline

Building this in-house would take an EdTech platform 6+ months and require AI engineering expertise they don't have. We do it once and sell it to many.

---

## Pricing Hypothesis (to be validated with first partners)

**Two pricing models, partner chooses:**

**Option A — Hosted (we pay LLM costs):**
- €1.50 per active student per month
- Includes all Gemini API costs
- Capped messages per student per day (e.g., 50)
- Simpler for partners, higher margin for us at scale

**Option B — Bring Your Own Key (BYOK):**
- €0.50 per active student per month
- Partner provides their own Gemini API key
- We charge only for our platform layer
- Lower margin but more attractive to large partners with existing AI budgets

**Both options include:** EU data residency, GDPR DPA, all v0.1 features, partner support.

---

## What an Integration Looks Like

A partner platform like Edukamentas integrates us in roughly this flow:

1. **Sign up** — get a partner API key from us (manual onboarding for v0.1)
2. **Upload curriculum** — POST their existing lesson content to `/v1/content/ingest` (one call per topic)
3. **Drop in chat** — when a student opens a lesson, their frontend calls `POST /v1/sessions` to start a tutoring session, then streams messages via `POST /v1/sessions/{id}/messages`
4. **Display the response** — partner renders our streamed text in their existing UI
5. **Done** — that's the entire integration. No data sync, no auth federation, no UI components from us.

The integration should take a competent backend developer **less than one day**. If it takes longer, we lose deals.

---

## What Success Looks Like

**MVP v0.1 success (Month 1–2):**
- Working API deployed to EU staging server
- One test partner integrated end-to-end (could be us with a fake partner identity)
- Demonstrably grounded responses on Lithuanian math curriculum content
- README documentation good enough that a developer can integrate without asking us questions

**v0.2 success (Month 3–4):**
- First paying partner signed
- 100+ active students using the API daily
- Persistent student memory feature added (post-MVP)
- Quiz generation feature added (post-MVP)

**Year 1 success:**
- 3+ paying partner platforms
- 5,000+ active students across all partners
- Monthly recurring revenue covering infrastructure + 1 full-time engineer

---

## Non-Goals (Things We Are Explicitly Not Doing)

- **No consumer-facing product.** No website where students sign up directly. No app store listings. We sell to platforms, not users.
- **No content creation.** Partners bring their own content. We don't write lessons.
- **No teacher dashboards.** Partners build their own dashboards using our event data. We provide the API; they provide the UI.
- **No grade tracking, gradebooks, attendance, scheduling.** Out of scope. We're a tutor, not an LMS.
- **No video, audio, or image generation.** Text in, text out. (Voice and image input might come in v1.0+ but not now.)
- **No fine-tuning custom models.** We use Gemini Flash via API. No model training, no GPUs, no MLOps complexity.

---

## The Pivot Mindset

The biggest risk to this project is **emotional attachment to features from the old consumer plan.** The mascot, the gamification, the parent dashboard, the league leaderboards — none of that belongs in the B2B API. Some partners might want gamification eventually, but that's their problem to build. Our job is to be the boring, reliable AI engine underneath.

When in doubt: **build less.** Ship something tiny that works perfectly, get it in front of partners, and let their feedback drive what comes next.