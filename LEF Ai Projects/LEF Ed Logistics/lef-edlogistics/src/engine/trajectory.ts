/**
 * =============================================================================
 * TRAJECTORY ENGINE: Forward Prediction
 * =============================================================================
 *
 * Projects a student's health forward in time. Uses the same Ebbinghaus decay
 * formula that the health calculator uses backward, but runs it forward to
 * answer: "What happens if we don't intervene?"
 *
 * This is the second act of the demo narrative:
 *   Act 1 (pedagogy.ts): Looking backward — finding root causes
 *   Act 2 (trajectory.ts): Looking forward — predicting future failure
 *   Act 3 (blind-test API): Proving it works
 *
 * =============================================================================
 */

import {
  DECAY_RATE,
  DECAY_FLOOR,
  DECAY_PERIOD_DAYS,
  HEALTH_WARNING,
  HEALTH_URGENT,
  HEALTH_GOOD,
  UNLOCK_THRESHOLD,
} from '@/engine/constants';
import { calculateAllHealth } from '@/engine/health-calculator';
import type { HealthResult } from '@/engine/health-calculator';
import {
  getDependentTopics,
  getTopicPrerequisites,
  getAllTopics,
  getTopicWithDetails,
} from '@/lib/queries';

// =============================================================================
// TYPES
// =============================================================================

export interface HealthProjectionPoint {
  week: number;           // 0 = now, 1 = next week, etc.
  health: number;         // projected health at that week
  status: 'GOOD' | 'WARNING' | 'URGENT' | 'CRITICAL';
}

export interface RiskCrossing {
  topicId: string;
  topicName: string;
  currentHealth: number;
  threshold: 'WARNING' | 'URGENT';
  thresholdValue: number;
  weeksUntilCrossing: number;
  projectedHealthAtCrossing: number;
}

export interface DAGImpact {
  topicId: string;
  topicName: string;
  currentHealth: number;
  currentlyBlocked: boolean;
  willBeBlocked: boolean;
  weekUntilBlocked: number | null;
  blockedBy: Array<{
    topicId: string;
    topicName: string;
    currentHealth: number;
    projectedHealth: number;
  }>;
}

export interface StudentTrajectory {
  studentId: string;
  projectionWeeks: number;
  generatedAt: string;
  topicProjections: Array<{
    topicId: string;
    topicName: string;
    currentHealth: number;
    rawMastery: number;
    daysSinceActivity: number;
    projectedCurve: HealthProjectionPoint[];
  }>;
  riskCrossings: RiskCrossing[];
  dagImpacts: DAGImpact[];
  summary: {
    topicsAtRisk: number;
    topicsGoingUrgent: number;
    topicsWillBlock: number;
    earliestRisk: RiskCrossing | null;
  };
}

// =============================================================================
// PURE MATH FUNCTIONS (no database calls)
// =============================================================================

/**
 * Classify a health value into a status category.
 */
function classifyStatus(health: number): 'GOOD' | 'WARNING' | 'URGENT' | 'CRITICAL' {
  if (health >= HEALTH_GOOD) return 'GOOD';
  if (health >= HEALTH_WARNING) return 'WARNING';
  if (health >= HEALTH_URGENT) return 'URGENT';
  return 'CRITICAL';
}

/**
 * Project a single health value forward N periods (months).
 *
 * Uses Ebbinghaus exponential decay — matches Patent 63/993,278 §3.3:
 *   futureDays = currentDaysSinceActivity + (period * DECAY_PERIOD_DAYS)
 *   futureMonths = futureDays / DECAY_PERIOD_DAYS
 *   futureHealth = rawMastery * max(DECAY_FLOOR, e^(-DECAY_RATE × futureMonths))
 *
 * This assumes NO new practice. If the student practices, the decay resets.
 * The prediction shows "what happens if we don't intervene."
 */
export function projectHealthForward(
  rawMastery: number,
  currentDaysSinceActivity: number,
  weeksAhead: number
): HealthProjectionPoint[] {
  const points: HealthProjectionPoint[] = [];

  for (let week = 0; week <= weeksAhead; week++) {
    const futureDays = currentDaysSinceActivity + (week * DECAY_PERIOD_DAYS);
    const futureMonthsSinceActivity = futureDays / DECAY_PERIOD_DAYS;

    let decayMultiplier: number;
    if (futureMonthsSinceActivity <= 0) {
      decayMultiplier = 1.0;
    } else {
      decayMultiplier = Math.exp(-DECAY_RATE * futureMonthsSinceActivity);
      decayMultiplier = Math.max(decayMultiplier, DECAY_FLOOR);
    }

    const health = Math.max(0, Math.min(100, rawMastery * decayMultiplier));
    const rounded = Math.round(health * 10) / 10;

    points.push({
      week,
      health: rounded,
      status: classifyStatus(rounded),
    });
  }

  return points;
}

/**
 * Find when a topic's health will cross a threshold.
 *
 * Algebraic solution using Ebbinghaus exponential — matches Patent 63/993,278 §3.3:
 *   rawMastery * e^(-DECAY_RATE × months) = threshold
 *   e^(-DECAY_RATE × months) = threshold / rawMastery
 *   -DECAY_RATE × months = ln(threshold / rawMastery)
 *   months = -ln(threshold / rawMastery) / DECAY_RATE
 *
 * Edge cases:
 * - If rawMastery * DECAY_FLOOR > threshold → floor prevents crossing → return null
 * - If health is already below threshold → return 0 (already crossed)
 * - If rawMastery <= threshold → return 0 (already at or below)
 */
export function findThresholdCrossing(
  rawMastery: number,
  currentDaysSinceActivity: number,
  threshold: number
): number | null {
  // If rawMastery is already at or below threshold, already crossed
  if (rawMastery <= threshold) return 0;

  // Check if the decay floor prevents ever crossing
  const floorHealth = rawMastery * DECAY_FLOOR;
  if (floorHealth >= threshold) return null;

  // Check if current health is already below threshold
  const currentMonths = currentDaysSinceActivity / DECAY_PERIOD_DAYS;
  const currentDecay = currentMonths > 0
    ? Math.max(Math.exp(-DECAY_RATE * currentMonths), DECAY_FLOOR)
    : 1.0;
  const currentHealth = rawMastery * currentDecay;

  if (currentHealth <= threshold) return 0;

  // Algebraic solution: months = -ln(ratio) / DECAY_RATE
  const ratio = threshold / rawMastery;
  const totalMonthsToThreshold = -Math.log(ratio) / DECAY_RATE;
  const totalDaysToThreshold = totalMonthsToThreshold * DECAY_PERIOD_DAYS;
  const remainingDays = totalDaysToThreshold - currentDaysSinceActivity;
  const remainingWeeks = remainingDays / 7; // Return value stays in weeks for UI compatibility

  // If remaining weeks is negative or zero, already crossed
  if (remainingWeeks <= 0) return 0;

  return Math.round(remainingWeeks * 10) / 10;
}

// =============================================================================
// DAG IMPACT PROJECTION (uses database)
// =============================================================================

/**
 * Project forward through the DAG: which topics will become blocked?
 *
 * For each topic the student has data on:
 * 1. Get its dependents (downstream topics)
 * 2. For each dependent, check all its prerequisites
 * 3. If any prerequisite's projected health drops below UNLOCK_THRESHOLD,
 *    the dependent topic will become blocked
 */
export async function projectDAGImpacts(
  studentId: string,
  weeksAhead: number
): Promise<DAGImpact[]> {
  const allHealth = await calculateAllHealth(studentId);
  const impacts: DAGImpact[] = [];

  // Build a set of all topics the student has data for
  const topicIds = Array.from(allHealth.keys());

  // For each topic, check if it will become blocked by decaying prerequisites
  for (const topicId of topicIds) {
    const topic = await getTopicWithDetails(topicId);
    if (!topic) continue;

    const prerequisites = await getTopicPrerequisites(topicId);
    if (prerequisites.length === 0) continue;

    // Check current state: is this already blocked?
    let currentlyBlocked = false;
    let willBeBlocked = false;
    let earliestBlock: number | null = null;
    const blockedByList: DAGImpact['blockedBy'] = [];

    for (const prereq of prerequisites) {
      const prereqHealth = allHealth.get(prereq.id);
      if (!prereqHealth) continue;

      // Currently blocked?
      if (prereqHealth.health < UNLOCK_THRESHOLD) {
        currentlyBlocked = true;
      }

      // Will the prerequisite decay below unlock threshold?
      const crossingWeeks = findThresholdCrossing(
        prereqHealth.rawMastery,
        prereqHealth.daysSinceActivity,
        UNLOCK_THRESHOLD
      );

      if (crossingWeeks !== null && crossingWeeks <= weeksAhead) {
        willBeBlocked = true;

        // Calculate projected health at crossing point
        const futureDays = prereqHealth.daysSinceActivity + (crossingWeeks * DECAY_PERIOD_DAYS);
        const futureMonths = futureDays / DECAY_PERIOD_DAYS;
        const decayMult = Math.max(Math.exp(-DECAY_RATE * futureMonths), DECAY_FLOOR);
        const projectedHealth = Math.round(prereqHealth.rawMastery * decayMult * 10) / 10;

        blockedByList.push({
          topicId: prereq.id,
          topicName: prereq.name,
          currentHealth: prereqHealth.health,
          projectedHealth,
        });

        if (earliestBlock === null || crossingWeeks < earliestBlock) {
          earliestBlock = crossingWeeks;
        }
      }
    }

    // Only include topics that will be affected
    if (currentlyBlocked || willBeBlocked) {
      const topicHealth = allHealth.get(topicId);
      impacts.push({
        topicId,
        topicName: topic.name,
        currentHealth: topicHealth?.health ?? 0,
        currentlyBlocked,
        willBeBlocked,
        weekUntilBlocked: willBeBlocked ? earliestBlock : null,
        blockedBy: blockedByList,
      });
    }
  }

  // Sort by soonest blockage
  impacts.sort((a, b) => {
    const aWeek = a.weekUntilBlocked ?? Infinity;
    const bWeek = b.weekUntilBlocked ?? Infinity;
    return aWeek - bWeek;
  });

  return impacts;
}

// =============================================================================
// FULL TRAJECTORY
// =============================================================================

/**
 * Full trajectory: combines health projection + threshold crossings + DAG impacts
 * for all of a student's active topics.
 */
export async function projectStudentTrajectory(
  studentId: string,
  weeksAhead: number = 12
): Promise<StudentTrajectory> {
  const allHealth = await calculateAllHealth(studentId);
  const topicProjections: StudentTrajectory['topicProjections'] = [];
  const riskCrossings: RiskCrossing[] = [];

  for (const [topicId, healthResult] of allHealth.entries()) {
    const topic = await getTopicWithDetails(topicId);
    if (!topic) continue;

    // Project health forward
    const projectedCurve = projectHealthForward(
      healthResult.rawMastery,
      healthResult.daysSinceActivity,
      weeksAhead
    );

    topicProjections.push({
      topicId,
      topicName: topic.name,
      currentHealth: healthResult.health,
      rawMastery: healthResult.rawMastery,
      daysSinceActivity: healthResult.daysSinceActivity,
      projectedCurve,
    });

    // Check for WARNING crossing
    const warningCrossing = findThresholdCrossing(
      healthResult.rawMastery,
      healthResult.daysSinceActivity,
      HEALTH_WARNING
    );
    if (warningCrossing !== null && warningCrossing > 0 && warningCrossing <= weeksAhead) {
      // Calculate projected health at crossing
      const futureDays = healthResult.daysSinceActivity + (warningCrossing * DECAY_PERIOD_DAYS);
      const futureMonths = futureDays / DECAY_PERIOD_DAYS;
      const decayMult = Math.max(Math.exp(-DECAY_RATE * futureMonths), DECAY_FLOOR);
      const projectedHealth = Math.round(healthResult.rawMastery * decayMult * 10) / 10;

      riskCrossings.push({
        topicId,
        topicName: topic.name,
        currentHealth: healthResult.health,
        threshold: 'WARNING',
        thresholdValue: HEALTH_WARNING,
        weeksUntilCrossing: warningCrossing,
        projectedHealthAtCrossing: projectedHealth,
      });
    }

    // Check for URGENT crossing
    const urgentCrossing = findThresholdCrossing(
      healthResult.rawMastery,
      healthResult.daysSinceActivity,
      HEALTH_URGENT
    );
    if (urgentCrossing !== null && urgentCrossing > 0 && urgentCrossing <= weeksAhead) {
      const futureDays = healthResult.daysSinceActivity + (urgentCrossing * DECAY_PERIOD_DAYS);
      const futureMonths = futureDays / DECAY_PERIOD_DAYS;
      const decayMult = Math.max(Math.exp(-DECAY_RATE * futureMonths), DECAY_FLOOR);
      const projectedHealth = Math.round(healthResult.rawMastery * decayMult * 10) / 10;

      riskCrossings.push({
        topicId,
        topicName: topic.name,
        currentHealth: healthResult.health,
        threshold: 'URGENT',
        thresholdValue: HEALTH_URGENT,
        weeksUntilCrossing: urgentCrossing,
        projectedHealthAtCrossing: projectedHealth,
      });
    }
  }

  // Sort risk crossings by soonest first
  riskCrossings.sort((a, b) => a.weeksUntilCrossing - b.weeksUntilCrossing);

  // Get DAG impacts
  const dagImpacts = await projectDAGImpacts(studentId, weeksAhead);

  // Build summary
  const warningCrossings = riskCrossings.filter((r) => r.threshold === 'WARNING');
  const urgentCrossings = riskCrossings.filter((r) => r.threshold === 'URGENT');

  const summary = {
    topicsAtRisk: warningCrossings.length,
    topicsGoingUrgent: urgentCrossings.length,
    topicsWillBlock: dagImpacts.filter((d) => d.willBeBlocked && !d.currentlyBlocked).length,
    earliestRisk: riskCrossings.length > 0 ? riskCrossings[0] : null,
  };

  return {
    studentId,
    projectionWeeks: weeksAhead,
    generatedAt: new Date().toISOString(),
    topicProjections,
    riskCrossings,
    dagImpacts,
    summary,
  };
}
