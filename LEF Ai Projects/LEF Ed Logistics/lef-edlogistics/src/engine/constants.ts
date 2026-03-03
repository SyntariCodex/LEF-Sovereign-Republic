// src/engine/constants.ts

/**
 * LEF EdLogistics — Centralized Engine Constants
 *
 * All thresholds that drive pedagogical decisions are defined here.
 * Changing a value here changes system behavior everywhere.
 * Each constant includes its pedagogical rationale.
 */

// === MASTERY & HEALTH ===

/** Mastery percentage required to consider a skill "learned" */
export const MASTERY_THRESHOLD = 80;

/** Health percentage below which a student needs urgent intervention */
export const HEALTH_URGENT = 40;

/** Health percentage below which a student gets a warning */
export const HEALTH_WARNING = 60;

/** Health percentage above which a student is progressing well */
export const HEALTH_GOOD = 80;

/** Health percentage required on ALL prerequisites to unlock a dependent topic */
export const UNLOCK_THRESHOLD = 60;

// === DECAY MODEL ===
// Based on Ebbinghaus forgetting curve: ADJUSTED_CONFIDENCE = BASE_SCORE × e^(-λ × months)
// Parameters match Patent 63/993,278 (LEF Ed Provisional, filed Feb 28 2026) §3.3
// and arXiv Paper 1 §3.3. DO NOT change without updating both the patent and the paper.

/** Monthly decay coefficient λ in the Ebbinghaus exponential formula e^(-λ × months) */
export const DECAY_RATE = 0.12;

/** Minimum decay multiplier — confidence never drops below 55% of its original score */
export const DECAY_FLOOR = 0.55;

/** Number of days that constitute one decay period (one calendar month) */
export const DECAY_PERIOD_DAYS = 30;

// === ERROR CLASSIFICATION ===
// Based on learning science: Bloom's taxonomy, Vygotsky's ZPD

/** Seconds — if a student fails in under this time, it's a SLIP (careless, they know it) */
export const SLIP_TIME_THRESHOLD_SECONDS = 30;

/** Seconds — if a student fails after this much time, it's a GAP (genuine confusion) */
export const GAP_TIME_THRESHOLD_SECONDS = 300;

/** Days — if a student was at 80%+ mastery but is now failing after this many days, it's ROT (decay) */
export const ROT_DETECTION_DAYS = 14;

// === SAFETY RAILS ===

/** Consecutive failures before the system escalates to a human teacher */
export const SPIRAL_BREAKER_THRESHOLD = 3;
