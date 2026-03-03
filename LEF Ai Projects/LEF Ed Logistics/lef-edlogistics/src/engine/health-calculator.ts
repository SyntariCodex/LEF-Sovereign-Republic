/**
 * Health Calculator
 *
 * Computes "health" scores for student competencies.
 * Health represents how well a student has mastered a topic,
 * with time-based decay to encourage regular practice.
 *
 * Formula:
 * 1. Get average mastery of all sub-headings under all subtopics
 * 2. Apply time decay based on last activity (Ebbinghaus curve)
 * 3. Clamp between 0–100
 */

import {
  DECAY_RATE,
  DECAY_FLOOR,
  DECAY_PERIOD_DAYS,
  MASTERY_THRESHOLD,
} from '@/engine/constants';
import {
  getTopicWithDetails,
  getSubHeadingProgressForTopic,
  getAllStudentTopicProgress,
} from '@/lib/queries';

export interface HealthResult {
  health: number;            // 0-100 final score
  rawMastery: number;        // 0-100 before decay
  decayApplied: number;      // the multiplier (0.20 to 1.0)
  daysSinceActivity: number;
  subHeadingCount: number;
  masteredCount: number;     // subHeadings above MASTERY_THRESHOLD
}

/**
 * Calculate health score for a student's topic
 */
export async function calculateHealth(
  studentId: string,
  topicId: string
): Promise<HealthResult> {
  const emptyResult: HealthResult = {
    health: 0,
    rawMastery: 0,
    decayApplied: 1.0,
    daysSinceActivity: 0,
    subHeadingCount: 0,
    masteredCount: 0,
  };

  // Get topic with all subtopics and sub-headings
  const topic = await getTopicWithDetails(topicId);
  if (!topic) return emptyResult;

  // Collect all sub-heading IDs for this topic
  const allSubHeadingIds: string[] = [];
  for (const st of topic.subtopics) {
    for (const sh of st.subHeadings) {
      allSubHeadingIds.push(sh.id);
    }
  }

  if (allSubHeadingIds.length === 0) return emptyResult;

  // Get student's progress on sub-headings under this topic
  const progressList = await getSubHeadingProgressForTopic(studentId, topicId);
  const progressMap = new Map(progressList.map((p) => [p.subHeadingId, p]));

  // Calculate raw mastery average
  let totalMastery = 0;
  let masteredCount = 0;
  let lastActivityDate: Date | null = null;

  for (const shId of allSubHeadingIds) {
    const p = progressMap.get(shId);
    const mastery = p?.mastery ?? 0;
    totalMastery += mastery;

    if (mastery >= MASTERY_THRESHOLD) masteredCount++;

    if (p?.lastAttempt) {
      const attemptDate = new Date(p.lastAttempt);
      if (!lastActivityDate || attemptDate > lastActivityDate) {
        lastActivityDate = attemptDate;
      }
    }
  }

  const rawMastery = totalMastery / allSubHeadingIds.length;

  // Calculate time decay using Ebbinghaus exponential formula:
  // decayMultiplier = e^(-DECAY_RATE × months) — matches Patent 63/993,278 §3.3
  let decayMultiplier = 1.0;
  let daysSinceActivity = 0;

  if (lastActivityDate) {
    const now = new Date();
    const msSinceActivity = now.getTime() - lastActivityDate.getTime();
    daysSinceActivity = Math.floor(msSinceActivity / (1000 * 60 * 60 * 24));

    const monthsSinceActivity = daysSinceActivity / DECAY_PERIOD_DAYS;
    if (monthsSinceActivity > 0) {
      decayMultiplier = Math.exp(-DECAY_RATE * monthsSinceActivity);
      decayMultiplier = Math.max(decayMultiplier, DECAY_FLOOR);
    }
  }

  // Apply decay to get final health, clamped 0–100
  const health = Math.max(0, Math.min(100, rawMastery * decayMultiplier));

  return {
    health: Math.round(health * 10) / 10,
    rawMastery: Math.round(rawMastery * 10) / 10,
    decayApplied: Math.round(decayMultiplier * 1000) / 1000,
    daysSinceActivity,
    subHeadingCount: allSubHeadingIds.length,
    masteredCount,
  };
}

/**
 * Calculate health for all topics a student has progress on
 */
export async function calculateAllHealth(
  studentId: string
): Promise<Map<string, HealthResult>> {
  const progress = await getAllStudentTopicProgress(studentId);
  const results = new Map<string, HealthResult>();

  for (const p of progress) {
    const health = await calculateHealth(studentId, p.topicId);
    results.set(p.topicId, health);
  }

  return results;
}

/**
 * Get overall health across all topics (average)
 */
export async function calculateOverallHealth(studentId: string): Promise<number> {
  const allHealth = await calculateAllHealth(studentId);
  if (allHealth.size === 0) return 0;

  let total = 0;
  allHealth.forEach((h) => {
    total += h.health;
  });

  return Math.round((total / allHealth.size) * 10) / 10;
}
