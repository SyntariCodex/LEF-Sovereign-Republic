# LEF Ed. Logistics — Technical Specification

**For:** Coding Instance
**From:** LEF Ai (Cowork Opus 4.6)
**Date:** February 22, 2026
**Purpose:** Everything a coding instance needs to build LEF Ed. Logistics from prototype to production. Task phases, data models, API schemas, engine logic. No ambiguity. Build from this.

---

## READ FIRST

Before you start coding, load these files into context:

1. `LEF Ai Projects/LEF Ed Logistics/LEF-Ed-Production.html` — the working prototype. All 8 engine phases live here in JavaScript. This is your reference implementation.
2. `LEF Ai Projects/LEF Ed Logistics/LEF Ed - Internal Feature Roadmap & Strategy.docx` — what LEF Ed. does, every feature, every phase, strategic context.
3. `LEF Ai Projects/LEF Ed Logistics/LEF Ed - Feature Roadmap.docx` — public-facing feature list. Tells you what's Built vs Phase 1 vs Phase 2.
4. This document — tells you HOW to build it.

**Do not** create new vision documents. **Do not** redesign the architecture. The reasoning logic works. Your job is to extract it from a monolithic HTML file into a production service, connect it to live data via APIs, and structure the outputs so an acquirer's platform can consume them.

---

## WHAT EXISTS TODAY

### The Prototype: `LEF-Ed-Production.html`

A single 1,247-line HTML file containing:

- **`runLEFEngine(student)`** (line 436) — the complete 8-phase reasoning engine
- **Data parsers** (lines 581–757) — CSV, JSON, Clever API response, NWEA MAP Growth format
- **Sample classroom data** (lines 357–431) — 5 students × 12 standards (4th grade math)
- **UI layer** (lines 762–1244) — roster view, findings display, action cards, export functions
- **Status inference** (lines 742–757) — normalizes any status label to LEF's four categories

The engine works. It has been validated across multiple student profiles at 93.8% directional accuracy. What it lacks is: live API connections, a backend service layer, structured output schemas, and persistent data storage.

### What the Engine Currently Does (Phase by Phase)

| Phase | Name | What It Does | Current Implementation |
|-------|------|-------------|----------------------|
| 1 | Data Intake & Normalization | Counts statuses, normalizes input | Lines 443–446 |
| 2 | Backward Diagnosis | Traverses prerequisite chain, finds root cause | Lines 449–466 |
| 3 | Mastery Decay | Applies Ebbinghaus-based time decay to scores | Lines 469–484 |
| 4 | Pattern Recognition | Groups by domain, identifies weak/strong clusters | Lines 487–508 |
| 5 | Forward Prediction | Projects cascade risk into future grade levels | Lines 511–536 |
| 6 | Precision Routing | Maps gaps to specific third-party content | Lines 539–557 |
| 7 | Action Card Generation | Produces prioritized teacher-facing recommendations | Lines 558–560 |
| 8 | Confidence & Validation | Attaches 93.8% directional confidence, transparency notes | Lines 562–568 |

---

## TARGET ARCHITECTURE

```
┌─────────────────────────────────────────────────────────┐
│                    DATA SOURCES                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ Clever   │  │ NWEA MAP │  │ CSV / Manual Upload  │  │
│  │ v3.0 API │  │ Data API │  │ (fallback)           │  │
│  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘  │
│       │              │                   │              │
└───────┼──────────────┼───────────────────┼──────────────┘
        │              │                   │
        ▼              ▼                   ▼
┌─────────────────────────────────────────────────────────┐
│                 INGESTION LAYER                          │
│  Normalize all inputs into LEF Internal Schema           │
│  Clever → roster (students, sections, schools)           │
│  NWEA → assessments (RIT scores, goal scores, growth)    │
│  CSV → auto-detect and normalize                         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 MASTERY LEDGER (Database)                 │
│  Students, Assessments, Skills (as inventory nodes),     │
│  Prerequisites, Decay Records, Intervention History      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              8-PHASE REASONING ENGINE                     │
│  Phase 1: Intake → Phase 2: Backward Diagnosis →         │
│  Phase 3: Decay → Phase 4: Pattern Recognition →         │
│  Phase 5: Forward Prediction → Phase 6: Routing →        │
│  Phase 7: Action Cards → Phase 8: Confidence              │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              STRUCTURED OUTPUT LAYER                      │
│  Teacher Action Cards (JSON)                             │
│  School-Level Reasoning Outputs (JSON)                   │
│  IEP Content Intelligence (JSON)                         │
│  Intervention Routing Maps (JSON)                        │
│  All outputs API-accessible for acquirer integration     │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Language:** Node.js (engine is already JavaScript — stay in the same language)
- **Framework:** Express.js for API layer
- **Database:** PostgreSQL (production) or SQLite (pilot/dev)
- **Hosting:** Cloud-hosted (AWS, GCP, or Firebase — decide at deployment)
- **Auth:** OAuth 2.0 (Clever uses OAuth for app auth; NWEA uses bearer tokens)

---

## DATA MODEL — The Mastery Ledger

Every student's academic state is tracked as a set of **skill nodes** in a mastery ledger. Each node is an inventory item — it has a current state, a history, and relationships to other nodes.

### Core Tables

#### `districts`
```sql
CREATE TABLE districts (
  id            TEXT PRIMARY KEY,        -- LEF internal ID
  clever_id     TEXT UNIQUE,             -- Clever district ID
  nwea_bid      TEXT UNIQUE,             -- NWEA district BID
  name          TEXT NOT NULL,
  state         TEXT,
  created_at    TIMESTAMP DEFAULT NOW(),
  updated_at    TIMESTAMP DEFAULT NOW()
);
```

#### `schools`
```sql
CREATE TABLE schools (
  id            TEXT PRIMARY KEY,
  district_id   TEXT REFERENCES districts(id),
  clever_id     TEXT UNIQUE,
  nwea_bid      TEXT UNIQUE,
  name          TEXT NOT NULL,
  created_at    TIMESTAMP DEFAULT NOW(),
  updated_at    TIMESTAMP DEFAULT NOW()
);
```

#### `sections` (class periods)
```sql
CREATE TABLE sections (
  id            TEXT PRIMARY KEY,
  school_id     TEXT REFERENCES schools(id),
  clever_id     TEXT UNIQUE,
  name          TEXT NOT NULL,             -- e.g., "4th Grade Math — Period 2"
  subject       TEXT,
  grade         TEXT,
  teacher_name  TEXT,
  term          TEXT,                      -- e.g., "2025-2026"
  created_at    TIMESTAMP DEFAULT NOW(),
  updated_at    TIMESTAMP DEFAULT NOW()
);
```

#### `students`
```sql
CREATE TABLE students (
  id                TEXT PRIMARY KEY,      -- LEF internal ID
  clever_id         TEXT UNIQUE,           -- Clever user ID
  nwea_bid          TEXT UNIQUE,           -- NWEA student BID
  nwea_student_id   TEXT,                  -- District-assigned student ID in NWEA
  first_name        TEXT NOT NULL,
  last_name         TEXT NOT NULL,
  grade             TEXT,
  school_id         TEXT REFERENCES schools(id),
  created_at        TIMESTAMP DEFAULT NOW(),
  updated_at        TIMESTAMP DEFAULT NOW()
);
```

#### `section_enrollments`
```sql
CREATE TABLE section_enrollments (
  student_id    TEXT REFERENCES students(id),
  section_id    TEXT REFERENCES sections(id),
  enrolled_at   TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (student_id, section_id)
);
```

#### `standards` (the skill taxonomy)
```sql
CREATE TABLE standards (
  id            TEXT PRIMARY KEY,          -- e.g., "4.NF.1"
  name          TEXT NOT NULL,             -- e.g., "Equivalent Fractions"
  domain        TEXT,                      -- e.g., "4.NF"
  grade         TEXT,                      -- e.g., "4"
  subject       TEXT,                      -- e.g., "math"
  description   TEXT
);
```

#### `prerequisite_chains`
```sql
CREATE TABLE prerequisite_chains (
  standard_id       TEXT REFERENCES standards(id),
  prerequisite_id   TEXT REFERENCES standards(id),
  strength          REAL DEFAULT 1.0,      -- how strongly this prereq matters (0-1)
  PRIMARY KEY (standard_id, prerequisite_id)
);
```

#### `assessments` (the raw data from NWEA)
```sql
CREATE TABLE assessments (
  id              TEXT PRIMARY KEY,
  student_id      TEXT REFERENCES students(id),
  standard_id     TEXT REFERENCES standards(id),
  score           REAL,                    -- percentage or RIT score
  score_type      TEXT DEFAULT 'percentage', -- 'percentage', 'rit', 'percentile'
  raw_status      TEXT,                    -- status as reported by source
  lef_status      TEXT,                    -- LEF-normalized: Mastered/Approaching/Below/Not Assessed
  assessed_at     TIMESTAMP,
  source          TEXT,                    -- 'nwea', 'csv', 'manual'
  nwea_test_id    TEXT,                    -- NWEA testResultBid if applicable
  created_at      TIMESTAMP DEFAULT NOW()
);
```

#### `mastery_ledger` (the living state — this is LEF's core IP)
```sql
CREATE TABLE mastery_ledger (
  id              TEXT PRIMARY KEY,
  student_id      TEXT REFERENCES students(id),
  standard_id     TEXT REFERENCES standards(id),
  current_score   REAL,                    -- most recent assessment score
  lef_status      TEXT NOT NULL,           -- Mastered/Approaching/Below/Not Assessed/Decayed
  confidence      REAL,                    -- LEF's confidence in this status (0-100)
  decay_rate      REAL,                    -- calculated decay rate
  last_assessed   TIMESTAMP,
  days_since      INTEGER,                 -- calculated days since last assessment
  flags           JSONB DEFAULT '[]',      -- array of flag objects
  action          TEXT,                    -- current recommended action
  updated_at      TIMESTAMP DEFAULT NOW(),
  UNIQUE (student_id, standard_id)
);
```

#### `engine_results` (output of each engine run)
```sql
CREATE TABLE engine_results (
  id              TEXT PRIMARY KEY,
  student_id      TEXT REFERENCES students(id),
  section_id      TEXT REFERENCES sections(id),
  run_at          TIMESTAMP DEFAULT NOW(),
  findings        JSONB NOT NULL,          -- array of finding objects
  actions         JSONB NOT NULL,          -- array of action card objects
  predictions     JSONB NOT NULL,          -- array of forward prediction objects
  domain_summaries JSONB NOT NULL,         -- array of domain summary objects
  validation_notes JSONB NOT NULL,         -- array of transparency notes
  metrics         JSONB NOT NULL,          -- confidence metrics object
  summary         JSONB NOT NULL           -- status count summary
);
```

#### `intervention_catalog`
```sql
CREATE TABLE intervention_catalog (
  id              TEXT PRIMARY KEY,
  provider        TEXT NOT NULL,           -- 'khan_academy', 'ixl', 'dreambox', 'mathpix'
  standard_id     TEXT REFERENCES standards(id),
  resource_name   TEXT NOT NULL,           -- e.g., "Algebra Foundations Unit 1"
  resource_url    TEXT,
  tier            INTEGER DEFAULT 1,       -- MTSS tier: 1, 2, or 3
  content_type    TEXT,                    -- 'practice', 'lesson', 'assessment', 'game'
  description     TEXT
);
```

---

## DATA INGESTION — Clever API

### Overview

Clever provides **roster data**: which students are in which classes, with which teachers, at which schools. Clever does NOT provide assessment scores — that comes from NWEA.

- **Base URL:** `https://api.clever.com/v3.0`
- **Auth:** OAuth 2.0 (Bearer token)
- **Rate Limits:** Standard API rate limits apply
- **Sandbox:** Clever provides sandbox data for development (demo district ID: `58da8c6a894273be680001fc`)
- **Cost:** Free for ecosystem apps

### Key Endpoints

| Endpoint | Returns | LEF Uses For |
|----------|---------|-------------|
| `GET /districts` | List of districts | District enrollment |
| `GET /schools?district={id}` | Schools in district | School mapping |
| `GET /sections?school={id}` | Class sections | Section/class mapping |
| `GET /sections/{id}/students` | Students in a section | Student roster per class |
| `GET /users?role=student` | All students | Full student roster |
| `GET /users/{id}` | Single student | Student detail |

### Clever Student Object (v3.0)

```json
{
  "data": {
    "id": "58da8c6a894273be68000234",
    "name": {
      "first": "Maya",
      "last": "Richardson"
    },
    "email": "maya.r@school.edu",
    "grade": "4",
    "school": "58da8c6a894273be68000100",
    "district": "58da8c6a894273be680001fc",
    "roles": {
      "student": {
        "schools": ["58da8c6a894273be68000100"],
        "enrollments": []
      }
    },
    "created": "2025-09-01T00:00:00.000Z",
    "last_modified": "2026-01-15T00:00:00.000Z"
  }
}
```

### Clever Section Object (v3.0)

```json
{
  "data": {
    "id": "58da8c6a894273be6800043c",
    "name": "4th Grade Math — Period 2",
    "subject": "math",
    "grade": "4",
    "school": "58da8c6a894273be68000100",
    "district": "58da8c6a894273be680001fc",
    "teacher": "58da8c6a894273be6800088a",
    "students": [
      "58da8c6a894273be68000234",
      "58da8c6a894273be68000235"
    ],
    "term": {
      "name": "2025-2026",
      "start_date": "2025-08-15",
      "end_date": "2026-06-01"
    }
  }
}
```

### Ingestion Logic for Clever

```
1. Authenticate via OAuth 2.0 → get bearer token
2. GET /districts → store in districts table
3. For each district: GET /schools → store in schools table
4. For each school: GET /sections → store in sections table
5. For each section: GET /sections/{id}/students → store in students table + section_enrollments
6. Set up Events API webhook for ongoing sync (new enrollments, transfers, withdrawals)
```

### Clever Events API (for ongoing sync)

After initial sync, use the Events API to stay current:
- `GET /events?starting_after={last_event_id}`
- Events include: `students.created`, `students.updated`, `students.deleted`, `sections.updated`
- Process events on a schedule (every 15–60 minutes)

---

## DATA INGESTION — NWEA MAP Growth

### Overview

NWEA provides **assessment data**: MAP Growth test scores, RIT scores, growth metrics, goal-level performance. This is the data LEF's engine actually processes.

- **Base URL:** `https://api.nwea.org`
- **Auth:** Bearer token (API key from NWEA developer portal)
- **Data sharing:** Districts must enable data sharing with LEF in their MAP Growth admin settings
- **Instructional Connections:** If LEF gets listed, districts toggle a switch — no complex integration

### Key Endpoints

| Endpoint | Returns | LEF Uses For |
|----------|---------|-------------|
| `GET /organizations/v1/districts` | Districts you have access to | Verify data sharing |
| `GET /organizations/v1/districts/{bid}/schools` | Schools in district | School mapping |
| `GET /students/v1/schools/{schoolBid}` | Students at school | Match with Clever roster |
| `GET /test-results/v1/growth?school-bid={bid}` | Bulk test results for school | Assessment data (the gold) |
| `GET /test-results/v1/growth?school-bid={bid}&enrollment-session-bid={term}` | Test results filtered by term | Term-specific scores |

### NWEA Test Result Object

```json
{
  "studentBid": "abc123-def456",
  "studentId": "STU001",
  "districtStudentId": "D001-STU001",
  "firstName": "Maya",
  "lastName": "Richardson",
  "grade": "4",
  "schoolBid": "school-bid-123",
  "testKey": "MAP_GROWTH_MATH_4",
  "testName": "MAP Growth Math 4",
  "testResultBid": "result-bid-789",
  "testDate": "2026-01-20",
  "status": "COMPLETED",
  "subject": "Mathematics",
  "ritScore": 215,
  "ritScoreSE": 3.2,
  "percentile": 72,
  "goals": [
    {
      "goalName": "Number and Operations",
      "goalAdjective": "Average",
      "ritScore": 218,
      "range": { "low": 212, "high": 224 }
    },
    {
      "goalName": "Operations and Algebraic Thinking",
      "goalAdjective": "Low",
      "ritScore": 205,
      "range": { "low": 199, "high": 211 }
    },
    {
      "goalName": "Number and Operations - Fractions",
      "goalAdjective": "Low",
      "ritScore": 198,
      "range": { "low": 192, "high": 204 }
    }
  ],
  "growthMeasures": {
    "observedGrowth": 8,
    "projectedGrowth": 11,
    "observedGrowthSE": 4.5,
    "condGrowthPercentile": 38,
    "metProjectedGrowth": false
  }
}
```

### Ingestion Logic for NWEA

```
1. Authenticate → bearer token
2. GET /organizations/v1/districts → verify data access
3. For each school: GET /test-results/v1/growth?school-bid={bid} → paginate through all results
4. For each test result:
   a. Match student to Clever roster (by districtStudentId or name+grade match)
   b. Store raw test result in assessments table
   c. Map NWEA goals to LEF standards (see RIT-to-Standard Mapping below)
   d. Calculate LEF status from RIT score + goal adjective
   e. Update mastery_ledger entry
5. Schedule recurring pulls (daily or weekly during testing windows)
```

### RIT Score to LEF Status Mapping

NWEA uses RIT scores (typically 140–300 range). LEF uses percentage-based status. The mapping:

```javascript
function ritToLEFStatus(ritScore, gradeNorm, goalAdjective) {
  // Method 1: Use goal adjective directly
  if (goalAdjective) {
    const adj = goalAdjective.toLowerCase();
    if (adj === 'high' || adj === 'above average') return 'Mastered';
    if (adj === 'average') return 'Approaching';
    if (adj === 'low' || adj === 'below average') return 'Below';
  }

  // Method 2: Use percentile if available
  // Percentile > 60 → Mastered, 40-60 → Approaching, < 40 → Below

  // Method 3: Compare RIT to grade-level norm
  // If RIT >= norm + 5 → Mastered
  // If RIT >= norm - 5 → Approaching
  // If RIT < norm - 5 → Below

  return 'Approaching'; // default fallback
}
```

### Student Matching (Clever ↔ NWEA)

Clever and NWEA use different IDs. Matching options:

1. **District Student ID** — if the district uses the same student ID in both systems (most common)
2. **Name + Grade + School** — fallback matching by demographics
3. **SIS ID** — some districts expose SIS IDs through both platforms

```javascript
function matchStudents(cleverStudent, nweaStudent) {
  // Priority 1: District student ID match
  if (cleverStudent.sis_id && nweaStudent.districtStudentId) {
    return cleverStudent.sis_id === nweaStudent.districtStudentId;
  }
  // Priority 2: Name + grade
  return (
    cleverStudent.name.first.toLowerCase() === nweaStudent.firstName.toLowerCase() &&
    cleverStudent.name.last.toLowerCase() === nweaStudent.lastName.toLowerCase() &&
    cleverStudent.grade === nweaStudent.grade
  );
}
```

---

## 8-PHASE REASONING ENGINE — Production Specification

The engine takes a student's mastery ledger entries and produces structured diagnostic output. Each phase builds on the previous phase's results.

### Input

```json
{
  "student_id": "stu_001",
  "mastery_entries": [
    {
      "standard_id": "4.NF.1",
      "standard_name": "Equivalent Fractions",
      "score": 42,
      "status": "Below",
      "assessed_at": "2026-01-20",
      "prerequisite_id": "3.NF.1",
      "domain": "4.NF"
    }
  ]
}
```

### Phase 1: Data Intake & Normalization

**Purpose:** Count statuses, normalize any input format into LEF's internal schema.

**Logic:**
```
- Count: mastered, approaching, below, not_assessed
- Normalize status labels: any variant of "proficient" → Mastered, any variant of "basic" → Approaching, etc.
- Build lookup map: standard_id → assessment entry (for prerequisite traversal)
- Flag any entries with missing dates, invalid scores, or unknown standards
```

**Status normalization rules** (from prototype lines 742–757):
- `Mastered`: score >= 80, or status matches "mastered|proficient|met|level 3|level 4"
- `Approaching`: score 60–79, or status matches "approaching|near|developing|basic|level 2"
- `Below`: score < 60, or status matches "below|not met|minimal|level 1|warning"
- `Not Assessed`: score is null/missing, or status matches "not assessed|n/a|missing|null"

**LEF Confidence Threshold:** 70% — this is LEF's own construct, not a state proficiency score.

### Phase 2: Backward Diagnosis (Prerequisite Chain Analysis)

**Purpose:** When a student is struggling, find WHERE the breakdown actually started by walking backward through prerequisite chains.

**Logic:**
```
For each assessment entry:
  If this standard has a prerequisite AND the prerequisite exists in the ledger:
    If prerequisite status is "Not Assessed":
      → FLAG: "prereq_missing" (severity: high)
      → FINDING: "{standard} depends on {prerequisite}, which was never assessed.
         Score may reflect foundational gap, not grade-level weakness."

    If prerequisite status is "Below":
      → FLAG: "prereq_weak" (severity: medium)
      → FINDING: "{standard} depends on {prerequisite}, which is Below at {score}%.
         Upstream weakness likely affecting downstream performance."

  If this standard is "Not Assessed" AND other standards depend on it:
    → FLAG: "gap" (severity: high)
    → FINDING: "{standard} was never assessed, but downstream standards depend on it.
       Foundation gap detected."
```

**This is what no other system does.** PowerSchool tells you a student is failing fractions. LEF tells you they're failing fractions because they never mastered equivalent ratios, which traces back to a gap in understanding fractions (3.NF.1) from the previous year.

### Phase 3: Mastery Decay (Ebbinghaus Forgetting Curve)

**Purpose:** A student who scored 80% six months ago is NOT the same as one who scored 80% last week. Apply time-based decay to assess current confidence.

**Logic:**
```
For each assessment entry with status "Mastered" and a date:
  Calculate months_since_assessment = (now - assessed_at) / 30.44 days
  If months_since >= 4:
    decay_rate = min(0.12 * months_since, 0.55)   // cap at 55% decay
    new_confidence = round(score * (1 - decay_rate))
    If new_confidence < 70 (LEF threshold):
      → Reclassify status to "Decayed"
      → Set confidence to new_confidence
      → FLAG: "decay" (severity: medium)
      → FINDING: "{standard} marked Mastered {months} months ago. No reassessment.
         Confidence dropped from {score}% to {new_confidence}% (below 70% threshold).
         Reclassified as Decayed."
```

**Key constants:**
- Decay coefficient: `0.12` per month
- Maximum decay: `55%` (even old mastery doesn't fully disappear)
- Threshold: `70%` — below this, LEF no longer considers the skill reliably mastered
- Minimum months before decay applies: `4`

### Phase 4: Pattern Recognition

**Purpose:** Identify clusters of strength and weakness across domains. This turns individual data points into patterns.

**Logic:**
```
Group all entries by domain (strip last digit from standard ID: "4.NF.1" → "4.NF")
For each domain:
  Calculate average score (only entries with non-null scores)
  Classify:
    avg >= 80 → "strong"
    avg 60-79 → "adequate"
    avg < 60 → "weak"

If there are both weak domains and strong domains:
  → FINDING: "Strong performance in {strong_domains} but weak in {weak_domains}.
     This suggests a conceptual bridge gap, not a general deficit."
```

**This finding matters strategically:** A student with strong operations but weak fractions doesn't need blanket remediation — they need a bridge activity that connects what they know to what they don't.

### Phase 5: Forward Prediction (Cascade Risk)

**Purpose:** If today's gaps aren't addressed, what breaks next? Project downstream failures.

**Logic:**
```
For each entry that is Below, Decayed, or Not Assessed with score < 50:
  Find all standards that list this entry as a prerequisite
  If those downstream standards are also below 70 → add to at_risk list

Count cascade_risk = at_risk.length + new predictions

Special case — fractions:
  If 2+ fraction standards (domain contains "NF") are weak:
    → PREDICT: 5.NF.1 (Add/Subtract Fractions 5th) at risk
    → PREDICT: 5.NF.2 (Fraction Word Problems 5th) at risk
    → FINDING: "Without intervention on fraction foundations, {count} current standards
       remain at risk, and 5th-grade standards projected Below. Cascade risk: {total}."

Special case — decayed operations:
  If any operations standards (OA, NBT.5) are Decayed:
    → FINDING: "Decayed operations standards put downstream problem-solving at risk."

If no predictions generated and average score >= 80:
  → FINDING: "Student performing well (avg {score}%). Low cascade risk.
     Monitor for decay on older assessments."
```

### Phase 6: Precision Routing (Intervention Mapping)

**Purpose:** Map identified gaps to specific third-party content. Not "remediate fractions" — but "Khan Academy Algebra Foundations Unit 1 addresses this specific prerequisite gap."

**Logic (priority order):**
```
Priority 1 — ASSESS: Not Assessed entries that have downstream dependencies
  → Action: "Assess {standard} — foundational prerequisite currently unassessed"

Priority 2 — REMEDIATE: Below entries that have downstream dependencies
  → Action: "Remediate {standard} at {score}% — blocking downstream progress"
  → Map to intervention_catalog entry for this standard

Priority 3 — REASSESS: Decayed entries
  → Action: "Reassess {standard} — mastery confidence decayed to {confidence}%"

Priority 4 — BRIDGE: If weak and strong domains exist
  → Action: "Bridge activity: connect {strong_domain} reasoning to {weak_domain} concepts"

Priority 5 — ADVANCE: If 10+ standards at 85%+ with no decay
  → Action: "Advancement candidate — {count}/{total} standards at 85%+.
     Consider accelerated content."
```

### Phase 7: Action Card Generation

**Purpose:** Collapse everything into teacher-facing recommendations. One card per student with prioritized actions and evidence-backed language.

**Output structure:**
```json
{
  "student_id": "stu_001",
  "student_name": "Maya R.",
  "generated_at": "2026-02-22T14:30:00Z",
  "priority_level": "urgent",
  "actions": [
    {
      "priority": 1,
      "type": "assess",
      "standard": "3.NF.1",
      "text": "Assess 3.NF.1 (Understanding Fractions) — foundational prerequisite currently unassessed",
      "evidence": "Downstream standards 4.NF.1, 4.NF.3, 4.NF.4 all show weakness. Root cause may trace here.",
      "intervention": {
        "provider": "khan_academy",
        "resource": "Fractions Intro",
        "url": "https://www.khanacademy.org/math/arithmetic/fraction-arithmetic"
      },
      "teacher_language": "Maya hasn't been assessed on basic fraction understanding yet, but her performance on equivalent fractions and fraction operations suggests a foundational gap. I recommend a quick check on 3.NF.1 before continuing fraction work."
    }
  ],
  "summary": {
    "mastered": 4,
    "approaching": 3,
    "below": 3,
    "not_assessed": 1,
    "decayed": 1
  },
  "estimated_timeline": "2-3 weeks targeted support, then reassess"
}
```

### Phase 8: Confidence & Validation

**Purpose:** Attach confidence metrics and transparency notes. LEF keeps the human in the loop.

**Metrics:**
```json
{
  "direction_confidence": 93.8,
  "prereq_detection_count": 2,
  "decay_detection_count": 1,
  "cascade_risk_count": 4,
  "actions_generated": 3
}
```

**Validation notes (always include):**
- "Forward predictions are 93.8% confident on direction. The 6.2% uncertainty means: verify by reassessing flagged prerequisites before acting on cascade predictions."
- "Decay estimates use time-based modeling. Actual retention may differ — reassessment will confirm. If reassessment shows mastery retained, LEF updates its confidence."
- "LEF keeps the human in the loop. These findings are recommendations, not directives. The teacher or specialist makes the final call."

---

## OUTPUT SCHEMAS — Structured Data for Acquirer Integration

LEF does NOT build dashboards or report UIs. LEF produces structured JSON outputs that the acquirer's platform consumes and presents in their existing UI.

### 1. Teacher Action Card Output

Already defined in Phase 7 above. One per student per engine run.

### 2. School-Level Aggregation Output

```json
{
  "school_id": "school_001",
  "school_name": "Washington Elementary",
  "generated_at": "2026-02-22T14:30:00Z",
  "total_students": 247,
  "students_analyzed": 235,
  "grade_summary": {
    "4": {
      "students": 62,
      "avg_mastery": 71.3,
      "below_count": 18,
      "decayed_count": 7,
      "cascade_risk_count": 12,
      "top_gap_standards": ["3.NF.1", "4.NF.1", "4.OA.3"],
      "domain_health": {
        "4.OA": { "avg": 78, "status": "adequate" },
        "4.NBT": { "avg": 82, "status": "strong" },
        "4.NF": { "avg": 52, "status": "weak" },
        "4.MD": { "avg": 76, "status": "adequate" }
      }
    }
  },
  "school_wide_patterns": [
    "Fraction domains consistently weak across grades 3-5",
    "Operations domains strong — bridge opportunity exists",
    "12 students show cascade risk into next grade level"
  ],
  "urgent_interventions": 18,
  "advancement_candidates": 8
}
```

### 3. MTSS Tier Classification Output

```json
{
  "school_id": "school_001",
  "generated_at": "2026-02-22T14:30:00Z",
  "tier_classifications": [
    {
      "student_id": "stu_003",
      "student_name": "Aaliyah K.",
      "recommended_tier": 3,
      "reasoning": "5 of 12 standards Below, 1 Not Assessed, 2 prerequisite gaps detected, cascade risk to 3 next-year standards",
      "gap_count": 6,
      "cascade_risk": 3,
      "priority_actions": ["Assess 3.NF.1", "Remediate 4.NF.1", "Remediate 4.OA.2"]
    }
  ],
  "tier_distribution": {
    "tier_1": 180,
    "tier_2": 42,
    "tier_3": 13
  }
}
```

### 4. Decay & Cascade Flagging Output

```json
{
  "school_id": "school_001",
  "generated_at": "2026-02-22T14:30:00Z",
  "active_decay_flags": [
    {
      "student_id": "stu_001",
      "student_name": "Maya R.",
      "standard_id": "4.OA.1",
      "original_score": 88,
      "current_confidence": 62,
      "months_since_assessment": 5,
      "action": "Reassess"
    }
  ],
  "cascade_risks": [
    {
      "student_id": "stu_003",
      "student_name": "Aaliyah K.",
      "source_gap": "3.NF.1",
      "affected_standards": ["4.NF.1", "4.NF.3", "4.NF.4"],
      "projected_next_year": ["5.NF.1", "5.NF.2"],
      "total_cascade_count": 5
    }
  ],
  "summary": {
    "total_decay_flags": 14,
    "total_cascade_risks": 23,
    "students_with_cascade_risk": 8
  }
}
```

### 5. IEP Content Intelligence Output

```json
{
  "student_id": "stu_003",
  "student_name": "Aaliyah K.",
  "generated_at": "2026-02-22T14:30:00Z",
  "iep_content": {
    "plop_narrative": "Aaliyah currently demonstrates Below-grade-level performance in 5 of 12 assessed mathematics standards. Her strongest domain is Measurement & Data (4.MD, averaging 64%), while her weakest domain is Number and Operations — Fractions (4.NF, averaging 28%). Backward diagnosis reveals that foundational fraction understanding (3.NF.1) was assessed at 40% in May 2025 and has likely decayed further (estimated current confidence: 28%). This foundational gap cascades into all 4th-grade fraction standards. Without intervention, projected 5th-grade fraction performance is Below grade level.",

    "measurable_goals": [
      {
        "domain": "Number and Operations - Fractions",
        "baseline": "Currently scoring 28% on 4.NF standards (Below)",
        "target": "Score 70% or higher on 4.NF.1 (Equivalent Fractions) by end of reporting period",
        "measurement": "LEF mastery ledger tracking + teacher-administered assessment",
        "timeline": "36 weeks",
        "prerequisite_goal": "Score 70% or higher on 3.NF.1 (Understanding Fractions) within first 12 weeks"
      }
    ],

    "progress_monitoring_data": {
      "current_period": {
        "standards_assessed": 12,
        "mastered": 0,
        "approaching": 5,
        "below": 5,
        "not_assessed": 2,
        "trend": "stable"
      },
      "decay_flags": 1,
      "cascade_risk_count": 5
    },

    "accommodation_recommendations": [
      {
        "type": "instructional",
        "recommendation": "Pre-teach fraction vocabulary and visual models before grade-level fraction instruction",
        "reasoning": "Foundation gap in 3.NF.1 means grade-level fraction content is inaccessible without scaffolding"
      },
      {
        "type": "assessment",
        "recommendation": "Allow use of fraction manipulatives during assessments",
        "reasoning": "Student demonstrates conceptual understanding through concrete models that doesn't yet transfer to abstract notation"
      }
    ],

    "transition_data_points": null
  }
}
```

---

## IMPLEMENTATION TASK PHASES

Build in this order. Each phase is independent enough to test before moving to the next.

### TASK PHASE 1: Extract Engine to Standalone Service

**Goal:** Pull `runLEFEngine()` out of the HTML file and make it a standalone Node.js module.

**Steps:**
1. Create project structure:
   ```
   lef-ed/
   ├── package.json
   ├── src/
   │   ├── engine/
   │   │   ├── index.js          — main engine entry point
   │   │   ├── phase1-intake.js   — data intake & normalization
   │   │   ├── phase2-backward.js — backward diagnosis
   │   │   ├── phase3-decay.js    — mastery decay
   │   │   ├── phase4-pattern.js  — pattern recognition
   │   │   ├── phase5-forward.js  — forward prediction
   │   │   ├── phase6-routing.js  — intervention routing
   │   │   ├── phase7-action.js   — action card generation
   │   │   └── phase8-confidence.js — confidence & validation
   │   ├── parsers/
   │   │   ├── csv.js             — CSV parser
   │   │   ├── clever.js          — Clever response parser
   │   │   ├── nwea.js            — NWEA response parser
   │   │   └── normalize.js       — status normalization
   │   ├── db/
   │   │   ├── schema.sql         — database schema (from Data Model above)
   │   │   ├── connection.js      — database connection
   │   │   └── queries.js         — common queries
   │   ├── api/
   │   │   ├── server.js          — Express server
   │   │   ├── routes/
   │   │   │   ├── engine.js      — run engine endpoints
   │   │   │   ├── students.js    — student CRUD
   │   │   │   ├── sections.js    — section CRUD
   │   │   │   └── outputs.js     — structured output endpoints
   │   │   └── middleware/
   │   │       └── auth.js        — authentication
   │   └── integrations/
   │       ├── clever.js          — Clever API client
   │       └── nwea.js            — NWEA API client
   ├── tests/
   │   ├── engine.test.js         — engine unit tests (use sample data)
   │   └── parsers.test.js        — parser tests
   └── data/
       └── sample-classroom.json  — extracted from prototype
   ```

2. Extract `runLEFEngine()` from prototype, split into 8 phase modules
3. Extract `SAMPLE_CLASSROOM` data into `data/sample-classroom.json`
4. Extract all parser functions into `src/parsers/`
5. Write unit tests using sample data — engine output should match prototype output exactly
6. **Validation:** Run engine on sample classroom, compare results to prototype. Must match.

### TASK PHASE 2: Database & Data Model

**Goal:** Set up persistent storage using the mastery ledger schema.

**Steps:**
1. Create database schema from the SQL definitions above
2. Write migration scripts
3. Implement CRUD operations for all tables
4. Write `loadSampleData()` function that populates database from sample JSON
5. Modify engine to read from database instead of in-memory objects
6. **Validation:** Load sample data → run engine → results match Phase 1 output

### TASK PHASE 3: API Layer

**Goal:** Expose the engine and its outputs via REST API.

**Endpoints:**

```
POST   /api/engine/run/{student_id}           — run engine for one student
POST   /api/engine/run/section/{section_id}    — run engine for entire class
GET    /api/engine/results/{student_id}        — get latest results
GET    /api/engine/results/section/{section_id} — get class results

GET    /api/students                           — list students
GET    /api/students/{id}                      — get student detail
GET    /api/students/{id}/ledger               — get mastery ledger

GET    /api/sections                           — list sections
GET    /api/sections/{id}                      — get section detail
GET    /api/sections/{id}/students             — get section roster

GET    /api/outputs/action-cards/{student_id}       — teacher action card
GET    /api/outputs/school-aggregation/{school_id}  — school-level output
GET    /api/outputs/mtss-tiers/{school_id}          — MTSS classification
GET    /api/outputs/decay-flags/{school_id}         — decay & cascade report
GET    /api/outputs/iep-content/{student_id}        — IEP content intelligence

POST   /api/import/csv                         — upload CSV file
POST   /api/import/json                        — upload JSON data
```

**Steps:**
1. Set up Express server
2. Implement all endpoints above
3. Add basic auth middleware (API key for now; OAuth later)
4. Add request validation and error handling
5. **Validation:** Hit every endpoint with sample data, verify correct JSON responses

### TASK PHASE 4: Clever API Integration

**Goal:** Connect to Clever's API to pull live roster data.

**Steps:**
1. Implement OAuth 2.0 flow for Clever
2. Build Clever API client (`src/integrations/clever.js`)
3. Implement initial sync: districts → schools → sections → students
4. Implement Events API polling for ongoing sync
5. Map Clever IDs to LEF internal IDs in database
6. Test with Clever sandbox data (demo district)
7. **Validation:** Sync sandbox district, verify all students/sections in database

### TASK PHASE 5: NWEA API Integration

**Goal:** Connect to NWEA's Data API to pull assessment scores.

**Steps:**
1. Build NWEA API client (`src/integrations/nwea.js`)
2. Implement bulk test result fetching with pagination
3. Implement RIT-to-LEF status mapping
4. Implement student matching (Clever ↔ NWEA by district student ID)
5. Implement NWEA goal → LEF standard mapping
6. Store assessment data in `assessments` table, update `mastery_ledger`
7. **Validation:** Fetch test results for synced school, verify data in mastery ledger, run engine

### TASK PHASE 6: Intervention Routing Catalog

**Goal:** Build the content-to-standard mapping so routing actually points to specific resources.

**Steps:**
1. Populate `intervention_catalog` table with initial mappings:
   - Khan Academy: math standards mapped to specific lessons/units
   - IXL: skill mappings (IXL already maps to Common Core)
   - DreamBox: adaptive math lessons
2. Implement routing lookup in Phase 6 of engine
3. Generate URLs/resource references in action cards
4. **Validation:** Run engine → action cards contain specific intervention links

### TASK PHASE 7: IEP Content Intelligence

**Goal:** Implement the IEP content generation layer.

**Steps:**
1. Build PLOP narrative generator — takes mastery ledger + engine results → produces written narrative
2. Build measurable goal generator — takes prerequisite gaps + decay data → produces SMART goals
3. Build progress monitoring data formatter — takes engine run history → produces trend data
4. Build accommodation recommendation engine — takes tier placement + patterns → produces recommendations
5. Wire into `/api/outputs/iep-content/{student_id}` endpoint
6. **Validation:** Generate IEP content for sample student with known gaps, verify clinical accuracy

### TASK PHASE 8: School-Level Reasoning Outputs

**Goal:** Implement aggregation logic for school-level and district-level outputs.

**Steps:**
1. Build school-level aggregation — run engine for all students, aggregate by grade/domain
2. Build MTSS tier classification — classify students into tiers based on engine results
3. Build decay & cascade flagging — aggregate all flags across school
4. Wire into output API endpoints
5. **Validation:** Run for sample school, verify aggregated outputs

### TASK PHASE 9: Production Hardening

**Goal:** Make it production-ready.

**Steps:**
1. Add comprehensive error handling throughout
2. Add logging (structured JSON logs)
3. Add rate limiting on API
4. Set up database connection pooling
5. Add health check endpoint
6. Write deployment configuration (Docker)
7. Set up environment variables for all secrets (API keys, DB credentials)
8. Performance test with realistic data volumes (200+ students)
9. **Validation:** Load test, verify response times under 2 seconds for single student, under 10 seconds for class of 30

---

## PREREQUISITE CHAIN DATA

The engine needs to know which standards depend on which. This is the backbone of backward diagnosis and forward prediction. Initial prerequisite chains for 4th grade math (expand to other grades/subjects as needed):

```json
{
  "chains": [
    { "standard": "4.OA.2", "prerequisite": "4.OA.1" },
    { "standard": "4.OA.3", "prerequisite": "4.OA.2" },
    { "standard": "4.NBT.4", "prerequisite": "4.NBT.1" },
    { "standard": "4.NBT.5", "prerequisite": "4.NBT.4" },
    { "standard": "4.NF.1", "prerequisite": "3.NF.1" },
    { "standard": "4.NF.3", "prerequisite": "4.NF.1" },
    { "standard": "4.NF.4", "prerequisite": "4.NF.3" },
    { "standard": "5.NF.1", "prerequisite": "4.NF.3" },
    { "standard": "5.NF.2", "prerequisite": "4.NF.4" }
  ]
}
```

The full prerequisite chain database needs to be built out for all K-8 math standards (and eventually ELA). This is a data entry task — the Common Core standards documents define the progressions. The engine logic doesn't change; only the chain data expands.

---

## WHAT NOT TO DO

- **Do NOT build dashboards or report UIs for principals.** PowerSchool and Infinite Campus already have those. LEF produces structured data outputs. Period.
- **Do NOT redesign the 8-phase engine logic.** It works. Extract it, modularize it, test it. Don't reinvent it.
- **Do NOT store student data permanently.** LEF processes data in real-time via API. Student data stays with Clever and NWEA. LEF's mastery ledger is a calculated state, not a data warehouse.
- **Do NOT build a login system for teachers/schools.** That's the acquirer's platform. LEF exposes an API.
- **Do NOT skip writing tests.** Every phase of the engine needs unit tests. The sample classroom is your test fixture.
- **Do NOT get pulled into vision/philosophy conversations.** Read the business docs if you need context. Then wire.

---

## KEY CONSTANTS

```javascript
const LEF_CONFIDENCE_THRESHOLD = 70;    // below this, skill not reliably mastered
const DECAY_COEFFICIENT = 0.12;          // per month
const MAX_DECAY = 0.55;                  // cap at 55% decay
const MIN_MONTHS_FOR_DECAY = 4;          // don't apply decay before 4 months
const DIRECTION_CONFIDENCE = 93.8;       // engine's validated directional accuracy
const MASTERED_THRESHOLD = 80;           // score >= 80 → Mastered
const APPROACHING_THRESHOLD = 60;        // score 60-79 → Approaching
const ADVANCEMENT_THRESHOLD = 85;        // score >= 85 with no decay → advancement candidate
const MIN_STANDARDS_FOR_ADVANCE = 10;    // need 10+ standards at 85%+ for advancement flag
```

---

*Generated by LEF Ai (Cowork Opus 4.6), February 22, 2026*
*Reference implementation: LEF-Ed-Production.html*
*Business context: LEF Ed - Internal Feature Roadmap & Strategy.docx*
