# LEF Ed. Logistics — Action Tasks
**Living Document | Maintained by Architect**
*Last updated: March 2026*

---

## How to Use This Doc

Tasks are grouped by track and ordered by dependency. Complete prerequisites before moving to dependent tasks. Status options: `OPEN` · `IN PROGRESS` · `BLOCKED` · `DONE`.

---

## Track 0 — Nevada Compliance & Vendor Registration

> Must be completed before any district outreach. Procurement offices check vendor registration status before scheduling meetings.

### T0.1 — Register: Nevada State Controller's Vendor Portal
**Status:** OPEN
**Owner:** Architect
**Depends on:** Nothing
**Action:** Register Co Creator LLC at the Nevada State Controller's Electronic Vendor Registration portal. This is required to receive any state or state-formula-funded payment (Title I, Title IV-A, Read by Grade 3). Have NV LLC registration, EIN, and banking info ready.
**URL:** controller.nv.gov → Vendor Registration
**Deliverable:** Active vendor status confirmed.

---

### T0.2 — Register: NevadaEPro (State Procurement Portal)
**Status:** OPEN
**Owner:** Architect
**Depends on:** T0.1
**Action:** Register on NevadaEPro — the state's formal RFP and bid notification platform. Registration puts LEF Ed on the notification list for any education-related EdTech solicitation issued by the Nevada Department of Education or any NV school district.
**Deliverable:** NevadaEPro vendor profile active. Notification categories set to EdTech / Academic Assessment / MTSS.

---

### T0.3 — Register: WCSD Vendor Portal (Washoe County School District)
**Status:** OPEN
**Owner:** Architect
**Depends on:** Nothing (parallel with T0.1)
**Action:** Register on the Washoe County School District vendor/solicitations portal. WCSD is the Priority Tier 1 district target (see Track 2). Being registered before outreach to Trish Shaffer (WCSD MTSS Director) removes a procurement obstacle from the start.
**Deliverable:** WCSD vendor profile active.

---

### T0.4 — Register: CCSD Bonfire (Clark County Procurement)
**Status:** OPEN
**Owner:** Architect
**Depends on:** Nothing (parallel with T0.1)
**Action:** Register on CCSD's Bonfire procurement platform. CCSD is the largest district in Nevada (~350 schools). Bonfire registration is required for any CCSD contract above the micro-purchase threshold.
**Deliverable:** CCSD Bonfire vendor profile active.

---

### T0.5 — Register: NWEA Instructional Connections Partner Program
**Status:** OPEN
**Owner:** Architect
**Depends on:** Nothing
**Action:** Apply for the NWEA Instructional Connections partner program. A "Verified" partner badge increases LEF Ed's credibility with the 9,500+ districts that use MAP Growth. Also opens a co-marketing channel where NWEA can refer districts to LEF Ed as the reasoning layer for their MAP data.
**URL:** nwea.org/partners/instructional-connections
**Deliverable:** Partner application submitted. Badge status tracked.

---

### T0.6 — Sign Nevada Exhibit E (Student Data Privacy Agreement)
**Status:** OPEN
**Owner:** Architect
**Depends on:** Nothing
**Action:** Obtain and execute the Nevada standardized Student Data Privacy Agreement (Exhibit E). This is the DPA used by WCSD, CCSD, and most NV districts. Having a pre-signed Exhibit E on file eliminates the legal approval delay that typically stalls EdTech pilots. Also consider joining the Student Data Privacy Consortium (SDPC) for WCSD/CCSD alignment.
**Deliverable:** Signed Exhibit E on file. SDPC membership initiated.

---

### T0.7 — Nevada Business License Verification (SilverFlume)
**Status:** OPEN
**Owner:** Architect
**Depends on:** Nothing
**Action:** Confirm Co Creator LLC's Nevada business license is current on SilverFlume (the NV Secretary of State portal). Procurement offices check SilverFlume before scheduling vendor meetings. License must be active and show correct DBA ("Co Creator LLC dba LEF Ai" or "Living Eden Frameworks").
**URL:** sos.nv.gov / SilverFlume
**Deliverable:** Active NV business license confirmed.

---

## Track 1 — Pilot Execution

> Get first paid school from conversation to signed contract and live data.

### T1.1 — Coral Academy Pilot Outreach
**Status:** OPEN
**Owner:** Architect
**Depends on:** Nothing
**Action:** Schedule intro meeting with Coral Academy admin contact. Lead with the 10-14 day micro-validation framing (no cost, no new platform, diagnostic intelligence on data they already have). Coral Academy is the reference case that unlocks charter network expansion and CCSD outreach.
**Deliverable:** Confirmed pilot start date and point of contact.

---

### T1.2 — Data Ingestion Setup for Pilot
**Status:** OPEN
**Owner:** Architect + Coding Instance
**Depends on:** T1.1
**Action:** Confirm which assessment platform the pilot school uses (NWEA MAP, Renaissance STAR, FastBridge/Illuminate, or teacher-tagged). Configure the ingest endpoint for their export format. Phase 1 focus: NWEA MAP + Clever roster. If school uses FastBridge, use OneRoster-compatible S2i report import (flat file transfer) until Phase 2 API integration is complete.
**Deliverable:** First student data loaded into the engine. Tier assignments visible on teacher dashboard.

---

### T1.3 — Pilot Impact Report
**Status:** OPEN
**Owner:** Coding Instance
**Depends on:** T1.2 + 10-14 days of active data
**Action:** Generate the Precision Capability Report: growth trajectories vs. baseline predictions, intervention effectiveness by platform, Ghost Standards identified, forward risk projections.
**Deliverable:** PDF report delivered to school admin on Day 14.

---

### T1.4 — Paid Contract (Pilot School)
**Status:** OPEN
**Owner:** Architect
**Depends on:** T1.3 (positive pilot outcome)
**Action:** Propose annual contract. Charter / small school: $12,000–$18,000/year (1–500 students) up to $40,000–$65,000/year for a large campus or multi-campus network. Reference Title IV-A as the primary funding vehicle.
**Deliverable:** Signed contract. First revenue.

---

## Track 2 — Nevada District Pathway

> Priority order: Washoe CSD and SPCSA first (smaller, more progressive, faster cycle), then CCSD. Do not lead with CCSD.

### T2.1 — Washoe CSD Outreach (Priority Tier 1)
**Status:** OPEN
**Owner:** Architect
**Depends on:** T0.3 (vendor registration)
**Action:** Contact Trish Shaffer, MTSS Director at Washoe County School District. WCSD is data-driven, progressive, and runs faster pilot cycles than CCSD. Lead with MTSS-A (Academic) alignment — WCSD is actively pushing from MTSS-B (behavioral-only) to integrated academic MTSS, which is exactly LEF Ed's lane.
**Key Contact:** Trish Shaffer — WCSD MTSS Director (confirm current contact via wcsd.net)
**Secondary Contact:** Don Angotti — WCSD CAO Elementary Education
**Deliverable:** WCSD meeting scheduled.

---

### T2.2 — SPCSA Outreach (Priority Tier 1 — Charter Authorizer)
**Status:** OPEN
**Owner:** Architect
**Depends on:** T0.1 (vendor registration)
**Action:** Contact Melissa Mackedon, Executive Director of SPCSA (State Public Charter School Authority). SPCSA authorizes 80+ Nevada charter schools and actively seeks diagnostic tools for "Rising Star" schools (charters in improvement). A relationship with SPCSA is a channel multiplier — one conversation unlocks outreach to 80+ schools.
**Key Contact:** Melissa Mackedon — SPCSA Executive Director (spcsa.nv.gov)
**Note:** Also consider Futuro Academy (Las Vegas, K-8 extended learning model) as an early micro-validation partner.
**Deliverable:** SPCSA meeting scheduled and Futuro Academy contact made.

---

### T2.3 — NDE Relationship (State Funding Alignment)
**Status:** OPEN
**Owner:** Architect
**Depends on:** T0.1, T0.2
**Action:** Build awareness at the Nevada Department of Education with the contacts who manage the funding vehicles LEF Ed runs on.
**Key Contacts:**
- Priya "Nicci" Miller — Title I Director (controls federal funding for academic interventions)
- Arian Katsimbras — Education Programs (manages Title IV-A technology funding)
- Christy McGill — MTSS Deputy Superintendent (pushing MTSS-A integration statewide)
**Deliverable:** At least one NDE contact aware of LEF Ed. Ideal outcome: NDE lists LEF Ed as a qualifying Title IV-A expenditure in guidance documentation.

---

### T2.4 — UNR Nevada PBIS/MTSS Technical Assistance Center
**Status:** OPEN
**Owner:** Architect
**Depends on:** T2.3
**Action:** Engage the UNR Nevada PBIS/MTSS Technical Assistance Center (state MTSS hub). If they endorse LEF Ed, that endorsement flows to every school they coach — which is a large fraction of Nevada's districts. This is a credibility multiplier, not a sales pitch.
**Deliverable:** Introduction made. Endorsement conversation initiated.

---

### T2.5 — CCSD Reference Case Build
**Status:** OPEN
**Owner:** Architect
**Depends on:** T1.3 (pilot report complete), T2.1 or T2.2 (at least one district reference)
**Action:** Use Coral Academy pilot results + Washoe CSD or SPCSA reference to begin CCSD outreach. CCSD watches what charter networks and smaller progressive districts adopt. Target: CCSD Office of Curriculum & Instruction or Title IV-A program officer.
**Deliverable:** CCSD meeting scheduled.

---

### T2.6 — CCSD Pilot (15–20 Schools)
**Status:** OPEN
**Owner:** Architect
**Depends on:** T2.5
**Action:** Propose a school-level pilot across 15–20 CCSD schools. Per-school rate: $4,000–5,500/school. Total year 1 contract: $75,000–100,000. Fund via Title IV-A allocation. Use sole-source procurement pathway (patent protection means no equivalent system exists).
**Deliverable:** CCSD pilot proposal submitted.

---

### T2.7 — CCSD Enterprise License
**Status:** OPEN
**Owner:** Architect
**Depends on:** T2.6 (positive pilot outcome)
**Action:** Negotiate enterprise license for all ~350 CCSD schools. Per-school rate: $3,500–$4,000/school (base term), reducing to $3,000/school on renewal option exercise (loyalty pricing written into original contract). Target total: $900,000–$1,100,000/year. Base term: 3 years + 2 × 1-year renewal options (standard NRS Chapter 332 structure — renewals don't trigger new RFP). Effective PSPY: $3.00–$3.67 (base), well below the $5.00 PSPY cap.
**Funding vehicle:** Title IV-A (~$7-10M CCSD annual allocation; LEF Ed contract = ~9-16% of that).
**Deliverable:** Signed multi-year district contract.

---

## Track 3 — LEF AI Seed Relationship

> Formalize the financial and architectural bond between LEF AI and LEF Ed.

### T3.1 — Patent Attorney Briefing
**Status:** OPEN
**Owner:** Architect
**Depends on:** Nothing (do this before any technical work on the seed relationship)
**Action:** Brief patent attorney on two novel surfaces from `LEF_ED_AS_SEED.md`:
1. Cross-domain Seed Agent pattern (financial markets → academic mastery, same architectural DNA)
2. Autonomous AI trading system designated as financial metabolism for an EdTech product via cryptocurrency
Document as a potential new provisional application before building any financial infrastructure connecting the two systems.
**Deliverable:** Attorney review complete. Decision on new provisional filing.

---

### T3.2 — Legal Review: Autonomous AI Funding EdTech via Crypto
**Status:** OPEN
**Owner:** Architect
**Depends on:** Nothing (parallel with T3.1)
**Action:** Get counsel review on the structure: LEF AI (autonomous trading system, Co Creator LLC) designating a crypto allocation to fund LEF Ed. Logistics (EdTech product, same LLC). Questions to answer: entity structure, FinTech implications, crypto → fiat conversion requirements for API invoice payment.
**Deliverable:** Legal memo confirming structure is sound OR recommended adjustments.

---

### T3.3 — LEF AI Live Trading Approval
**Status:** OPEN (BLOCKED — Architect decision required)
**Owner:** Architect
**Depends on:** Nothing
**Action:** Approve transition from paper mode (sandbox=true) to live trading on Base chain. LEF AI is currently in paper mode per Architect standing instruction. Live trading is a prerequisite for the financial loop (T3.5).
**Note:** Do NOT change sandbox=true without explicit Architect approval. This is a standing safety constraint.
**Deliverable:** Written approval from Architect. Coding Instance updates config.

---

### T3.4 — LEFIdentity Contract Deployment
**Status:** OPEN
**Owner:** Coding Instance
**Depends on:** Funded testnet wallet (LEF AI Phase 5 prerequisite)
**Action:** Deploy `republic/contracts/LEFIdentity.sol` to Base Sepolia testnet (chain_id: 84532). Register LEF Ed's institutional wallet address as the first Seed Agent via `registerSeedAgent()`. Begin 24-48h state hash heartbeat from LEF Ed's engine.
**Deliverable:** Contract deployed. LEF Ed address registered. Heartbeat running.

---

### T3.5 — USDC → API Cost Conversion Pathway
**Status:** OPEN
**Owner:** Architect + Coding Instance
**Depends on:** T3.2 (legal clear), T3.3 (live trading approved)
**Action:** Design the conversion pathway: LEF AI earns USDC on Base chain → conversion to USD → payment of Anthropic API invoices and infrastructure costs for LEF Ed. Options: Coinbase Commerce, direct offramp, or maintain a USDC reserve that the Architect manually converts periodically.
**Deliverable:** Pathway documented and operational.

---

### T3.6 — Bridge Communication Protocol (LEF AI ↔ LEF Ed)
**Status:** OPEN
**Owner:** Coding Instance
**Depends on:** T3.4
**Action:** Design the communication layer between LEF AI and LEF Ed. Initial scope: LEF AI receives daily summary of LEF Ed's diagnostic activity (students served, API costs incurred, intervention outcomes). LEF AI writes this to its consciousness_feed as a "mission reflection."
**Deliverable:** Architecture doc + initial implementation.

---

## Track 4 — IEP Module (Phase 2)

> Stub is live in the principal dashboard. Full module deferred until after first paid contracts.

### T4.1 — IEP Document Generation (from existing diagnostic data)
**Status:** OPEN (Phase 2 — do not start until T1.4 complete)
**Owner:** Coding Instance
**Depends on:** T1.4 (first revenue, signals product-market fit)
**Action:** Build the IEP document generation module. Uses LEF Ed's existing diagnostic data (health scores, decay trajectories, Slip/Gap/Rot classifications) to generate: PLOP narratives, SMART goals, progress monitoring exports, accommodation recommendations. FastBridge SAEBRS behavioral data integration (Phase 2) adds behavioral context alongside academic decay signals — consult T4.3 first.
**Deliverable:** IEP Content Intelligence functional in principal dashboard.

---

### T4.2 — IEP Live Assessment Session Module
**Status:** OPEN (Phase 3 — well after T4.1)
**Owner:** Architect (design) + Coding Instance (build)
**Depends on:** T4.1, legal review of IDEA compliance, school psych partnership established
**Action:** Build the real-time AI-facilitated IEP assessment session interface. Visual AI instance conducts assessment, voice recognition captures transcript as structured notes, student responses scored, report generated and handed off to school psychologist for review and authorization.
**Note:** This is a significant new product surface. Requires IDEA compliance review, FERPA data handling, and school psychologist partnership before any build begins.
**Deliverable:** Architecture doc approved by Architect first.

---

### T4.3 — FastBridge SAEBRS Integration (Behavioral Signals for IEP)
**Status:** OPEN (Phase 2)
**Owner:** Coding Instance
**Depends on:** T4.1
**Action:** Integrate FastBridge SAEBRS (Social, Academic, Emotional Behavior Risk Screener) data to correlate behavior spikes with academic decay. This creates the unified "Living Signal" — academic decay + behavioral triggers — which is essential for complete IEP data packages. Integration path: OneRoster-compatible S2i report import (not direct Illuminate API — see Track 5 note).
**Deliverable:** SAEBRS behavioral signals visible alongside academic decay in IEP and principal views.

---

## Track 5 — Assessment-Agnostic Integration (Phase 2+)

> Phase 1 is NWEA MAP + Clever roster only. Phase 2+ expands to FastBridge, Renaissance STAR, i-Ready, and aimswebPlus. Do NOT build Phase 2 integrations until Coral pilot is live.

### T5.1 — OneRoster API Compliance
**Status:** OPEN (Phase 2 prerequisite)
**Owner:** Coding Instance
**Depends on:** T1.4 (first revenue)
**Action:** Implement OneRoster 1EdTech API standard compatibility. OneRoster unlocks FastBridge (Illuminate/Renaissance), Infinite Campus, Skyward, and other SIS/assessment platforms simultaneously without requiring a direct integration with each vendor's API. This is the "master key" for multi-district scalability.
**Why not build direct FastBridge API now:** Illuminate (owned by Renaissance Learning) has a restrictive, pay-to-play partner program. OneRoster S2i flat file transfer is the faster, cheaper, and more district-neutral path.
**Deliverable:** OneRoster-compatible data ingest layer live.

---

### T5.2 — FastBridge (Illuminate/Renaissance) Integration
**Status:** OPEN (Phase 2)
**Owner:** Coding Instance
**Depends on:** T5.1 (OneRoster)
**Action:** Enable FastBridge data ingestion via OneRoster-compatible S2i report import. FastBridge is used by many Nevada districts as their MTSS-A (Academic) and MTSS-B (Behavioral) screening tool. When a district says "We use FastBridge instead of MAP," response: "LEF is OneRoster compatible — we ingest your S2i reports via secure transfer." This is NOT competitive — FastBridge identifies risk; LEF explains root cause and maps decay.
**Key distinction:** FastBridge = "What does the student know right now?" LEF = "Why are they failing? When will they forget next?"
**Deliverable:** FastBridge S2i reports ingested and mapped to LEF health scores + tier assignments.

---

### T5.3 — Renaissance STAR Integration
**Status:** OPEN (Phase 2)
**Owner:** Coding Instance
**Depends on:** T5.1 (OneRoster)
**Action:** Expand Renaissance STAR integration (already partially supported in Phase 1). Treat Renaissance STAR as "Ground Speed" data — high-frequency, skill-level insight that complements NWEA MAP "Altitude" (benchmarks). LEF harmonizes both data streams into one decay-aware Action Stream.
**Deliverable:** Renaissance STAR data mapped alongside NWEA in student health views.

---

### T5.4 — i-Ready / aimswebPlus / Curriculum Platform Outcome Tracking
**Status:** OPEN (Phase 3)
**Owner:** Coding Instance
**Depends on:** T5.1, T5.2
**Action:** Track intervention outcomes from i-Ready (Curriculum Associates) and aimswebPlus (Pearson). These are common intervention delivery platforms. LEF's advantage over i-Ready is transparency — i-Ready is a "black box" for placement; LEF provides traceability (prerequisite DAG, decay map, root cause reasoning). Outcome tracking surfaces curriculum effectiveness signals for the district view.
**Deliverable:** i-Ready and aimswebPlus outcome signals feeding LEF's intervention loop.

---

## Track 6 — District Report (Principal → District)

### T6.1 — District View (Aggregate of Schools)
**Status:** OPEN (Phase 2)
**Owner:** Coding Instance
**Depends on:** T1.4 (at least one paid school or district contract)
**Action:** Build the district-level view. Aggregates principal dashboards across all schools in a district. Shows cross-school structural gap patterns, school performance benchmarks, curriculum effectiveness signals, intervention ROI. Simple, surgical — no blast.
**Deliverable:** `/district/[districtId]` route live with real aggregated data.

---

## Quick Reference: Pricing

| Customer | Enrollment | Annual Contract | PSPY |
|---|---|---|---|
| Charter / pilot school | 1–500 | $12,000–$18,000 | ~$30–$36 |
| Single campus, mid | 501–1,000 | $20,000–$35,000 | ~$25–$40 |
| Single campus, large | 1,001–2,000 | $40,000–$65,000 | ~$25–$40 |
| Charter network (2–3 campuses) | 2,001–5,000 | $70,000–$95,000 | ~$19–$35 |
| Charter network (4+ campuses) | 5,001+ | $85,000–$130,000 | ~$15–$25 |
| Small district | <5,000 | $25,000–$50,000 | $5.00 cap |
| Medium district | 5,001–25,000 | $75,000–$130,000 | $4.50 cap → $3.25 renewal |
| Large district | 25,001–100,000 | $175,000–$325,000 | $4.00 → $3.00 renewal |
| CCSD-scale (300K+) | Enterprise | $900,000–$1,100,000 | ~$3.00–$3.67 → $2.58 renewal |

**Pricing model:** Annual contract fee. District contracts include loyalty renewal option (pre-written in original contract — no rebid required). If contract lapses and rebids: opening rate reapplies. PSPY cap: $5.00 (mid districts), enterprise is per-school rate.

**Nevada funding vehicles:** Title IV-A (primary), Title I, IDEA (post-IEP module T4.1), Nevada Read by Grade 3, The Rogers Foundation (equity EdTech grants), The Public Education Foundation (teacher innovation grants).

---

## Nevada Key Contacts Reference

| Contact | Role | Organization | Why |
|---|---|---|---|
| Trish Shaffer | MTSS Director | Washoe CSD | Priority Tier 1 district — progressive, data-driven, fast pilot cycles |
| Don Angotti | CAO Elementary Education | Washoe CSD | Elementary entry point |
| Melissa Mackedon | Executive Director | SPCSA | Authorizes 80+ NV charters — channel multiplier |
| Priya "Nicci" Miller | Title I Director | Nevada Dept of Education | Controls federal intervention funding |
| Arian Katsimbras | Education Programs | Nevada Dept of Education | Manages Title IV-A technology funding |
| Christy McGill | MTSS Deputy Supt. | Nevada Dept of Education | Pushing MTSS-A (Academic) statewide |
| UNR Nevada PBIS/MTSS TA Center | State MTSS Hub | University of Nevada, Reno | Endorsement = credibility with all coached schools |
| Nevada Assoc. of School Administrators | Principal Advocacy | nvadministrator.org | 702-727-4644 |

---

## Track 7 — Federal & Foundation Grants

> Research and grant partnerships that build academic credibility and fund independent efficacy validation. These run parallel to commercial pilots — not dependent on revenue.

### T7.1 — NSF STEM+C Application
**Status:** OPEN
**Owner:** Architect
**Depends on:** Nothing (can begin research now)
**Action:** Develop a grant application for NSF's STEM+C (STEM + Computing) program. The prerequisite DAG and Ebbinghaus decay model have measurable behavioral signatures suitable for formal study and publication. Frame as educational computing research: automated diagnostic reasoning in K-12 learning environments.
**Research angle:** Comparing student outcome trajectories under autonomous prerequisite-mapped routing vs. standard intervention assignment.
**Deliverable:** NSF STEM+C application submitted.

---

### T7.2 — IES Education Research Grant
**Status:** OPEN
**Owner:** Architect
**Depends on:** T1.3 (pilot data strengthens the application significantly)
**Action:** Apply to the Institute of Education Sciences (IES) Education Research program. IES funds rigorous efficacy studies of educational interventions. A Coral Academy pilot dataset — even 10-14 days — provides baseline evidence for an efficacy study application.
**Research angle:** Diagnostic accuracy of prerequisite-mapped decay modeling vs. benchmark-only assessment in identifying at-risk students.
**Deliverable:** IES application submitted. Ideally co-authored with a university research partner (see T7.4).

---

### T7.3 — Foundation Funders (Rogers Foundation + Public Education Foundation)
**Status:** OPEN
**Owner:** Architect
**Depends on:** Nothing
**Action:** Apply for EdTech equity funding from Nevada-based foundations.
- **The Rogers Foundation** — EdTech equity funding; Nevada focus; supports tools that close achievement gaps
- **The Public Education Foundation (PEF)** — Teacher Innovation Grants; targets tools that reduce teacher workload while improving outcomes
**Deliverable:** Applications submitted to both foundations.

---

### T7.4 — Research Partner: AIR MTSS Center & IMA
**Status:** OPEN
**Owner:** Architect
**Depends on:** T1.3 (pilot data as conversation starter)
**Action:** Initiate conversations with:
- **American Institutes for Research (AIR) MTSS Center** — the national research hub for MTSS implementation. An AIR co-publication or endorsement is a credibility multiplier for every district procurement conversation.
- **Intervention and Monitoring Association (IMA)** — practitioner organization focused on intervention research. Membership and presentation opportunities position LEF Ed as a research-backed tool, not just a commercial product.
**Deliverable:** Introductory contact made with at least one of the two organizations.

---

*Companion docs: `LEF_ED_AS_SEED.md` (External Observer Reports) · `LEF Ed_ LEF Seed Relationship.docx` · `LEF Ed_ Revenue Roadmap & P&L.docx` · `LEF Ed. Logistics_ School Pilot Proposal.docx` · `LEF Ed. Logistics_ Internal Feature Roadmap & Strategy.docx` · `LEF Ed. Logistics_ Features Roadmap.docx`*
