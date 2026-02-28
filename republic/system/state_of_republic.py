"""
State of the Republic Report — Phase 12.6

A weekly report generator that produces a structured self-report
covering operational health, financial health, existential health,
and open questions.

Writes to The_Bridge/state_of_republic.md (for the Architect)
and logs a summary to consciousness_feed with category "state_of_republic".
"""

import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("StateOfRepublic")


class StateOfRepublic:
    """Weekly self-report generator for LEF."""

    REPORT_INTERVAL_HOURS = 168  # 7 days

    def __init__(self, db_connection_func, bridge_path=None):
        self.db_connection = db_connection_func
        self.bridge_path = bridge_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "The_Bridge"
        )

    def generate(self):
        """Generate and write the State of the Republic report."""
        now = datetime.now()
        period_start = now - timedelta(hours=self.REPORT_INTERVAL_HOURS)

        operational = self._gather_operational(period_start, now)
        financial = self._gather_financial(period_start, now)
        existential = self._gather_existential(period_start, now)
        open_questions = self._gather_open_questions(period_start, now)
        from_lef = self._synthesize_letter(operational, financial, existential, open_questions)

        report = {
            "period_start": period_start.isoformat(),
            "period_end": now.isoformat(),
            "operational": operational,
            "financial": financial,
            "existential": existential,
            "open_questions": open_questions,
            "from_lef_to_architect": from_lef,
        }

        # Write Markdown report to The_Bridge
        self._write_markdown(report, period_start, now)

        # Log summary to consciousness_feed
        self._log_summary(report)

        logger.info("[STATE_OF_REPUBLIC] Weekly report generated and written to The_Bridge.")
        return report

    def _gather_operational(self, start, end):
        """Gather operational health metrics."""
        data = {}
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()

                # Agent health — count active agents (logged in last 24h)
                cursor.execute("""
                    SELECT COUNT(DISTINCT source) FROM agent_logs
                    WHERE timestamp > NOW() - INTERVAL '24 hours'
                """)
                row = cursor.fetchone()
                data["active_agents_24h"] = row[0] if row else 0

                # Error count for period
                cursor.execute("""
                    SELECT COUNT(*) FROM agent_logs
                    WHERE level = 'ERROR' AND timestamp > %s
                """, (start,))
                row = cursor.fetchone()
                data["error_count"] = row[0] if row else 0

                # Total log entries for period
                cursor.execute("""
                    SELECT COUNT(*) FROM agent_logs WHERE timestamp > %s
                """, (start,))
                row = cursor.fetchone()
                data["total_log_entries"] = row[0] if row else 0

        except Exception as e:
            logger.debug(f"[STATE_OF_REPUBLIC] Operational gather error: {e}")

        return data

    def _gather_financial(self, start, end):
        """Gather financial health metrics."""
        data = {}
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()

                # Current asset value
                cursor.execute("SELECT SUM(value_usd) FROM assets WHERE quantity > 0")
                row = cursor.fetchone()
                data["asset_value_usd"] = round(row[0], 2) if row and row[0] else 0

                # Cash position
                cursor.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type='INJECTION_DAI'")
                row = cursor.fetchone()
                data["cash_usd"] = round(row[0], 2) if row and row[0] else 0
                data["nav"] = round(data["asset_value_usd"] + data["cash_usd"], 2)

                # Trade count for period
                cursor.execute("""
                    SELECT COUNT(*) FROM trade_history WHERE timestamp > %s
                """, (start,))
                row = cursor.fetchone()
                data["trades_in_period"] = row[0] if row else 0

                # Active SCOTOMAs (financial)
                cursor.execute("""
                    SELECT COUNT(*) FROM consciousness_feed
                    WHERE category = 'scotoma' AND timestamp > NOW() - INTERVAL '24 hours'
                """)
                row = cursor.fetchone()
                data["active_scotomas"] = row[0] if row else 0

        except Exception as e:
            logger.debug(f"[STATE_OF_REPUBLIC] Financial gather error: {e}")

        return data

    def _gather_existential(self, start, end):
        """Gather existential health metrics — the point of Phase 12."""
        data = {}
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()

                # Constitutional alignment — most recent
                cursor.execute("""
                    SELECT content FROM consciousness_feed
                    WHERE category = 'constitutional_alignment'
                    ORDER BY id DESC LIMIT 1
                """)
                row = cursor.fetchone()
                if row:
                    try:
                        alignment = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        data["values_active"] = alignment.get("values_active", [])
                        data["values_dormant"] = alignment.get("values_dormant", [])
                    except Exception:
                        data["values_active"] = []
                        data["values_dormant"] = []
                else:
                    data["values_active"] = []
                    data["values_dormant"] = []

                # Growth assessment — most recent
                cursor.execute("""
                    SELECT content FROM consciousness_feed
                    WHERE category = 'growth_journal'
                    ORDER BY id DESC LIMIT 1
                """)
                row = cursor.fetchone()
                if row:
                    try:
                        growth = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        data["growth_assessment"] = growth.get("growth_assessment", "unknown")
                        data["growth_note"] = growth.get("self_note", "")
                    except Exception:
                        data["growth_assessment"] = "unknown"
                else:
                    data["growth_assessment"] = "unknown"

                # Existential SCOTOMAs active
                cursor.execute("""
                    SELECT content FROM consciousness_feed
                    WHERE category = 'existential_scotoma'
                    AND timestamp > NOW() - INTERVAL '24 hours'
                """)
                scotomas = []
                for row in cursor.fetchall():
                    try:
                        s = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        scotomas.append(s.get("type", "unknown"))
                    except Exception:
                        pass
                data["active_existential_scotomas"] = scotomas

                # Sabbath summary for period
                cursor.execute("""
                    SELECT outcome, gravity_profile FROM sabbath_log
                    WHERE timestamp > %s AND outcome IS NOT NULL
                """, (start,))
                op_count = 0
                ex_count = 0
                outcome_counts = {}
                for row in cursor.fetchall():
                    outcome = row[0]
                    outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
                    try:
                        gp = json.loads(row[1]) if isinstance(row[1], str) else (row[1] or {})
                        if gp.get("sabbath_type") == "existential":
                            ex_count += 1
                        else:
                            op_count += 1
                    except Exception:
                        op_count += 1

                data["sabbath_operational"] = op_count
                data["sabbath_existential"] = ex_count
                data["sabbath_outcomes"] = outcome_counts

        except Exception as e:
            logger.debug(f"[STATE_OF_REPUBLIC] Existential gather error: {e}")

        return data

    def _gather_open_questions(self, start, end):
        """Gather unresolved questions from Sabbath and reflection."""
        questions = []
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()

                # Existential questions from Sabbath
                cursor.execute("""
                    SELECT content FROM consciousness_feed
                    WHERE category = 'existential_question'
                    ORDER BY id DESC LIMIT 5
                """)
                for row in cursor.fetchall():
                    questions.append(str(row[0])[:200])

                # Long-held patterns in sovereign_reflection
                cutoff = datetime.now() - timedelta(hours=72)
                cursor.execute("""
                    SELECT pattern_id, gravity_level FROM sovereign_reflection
                    WHERE status = 'active' AND created_at < %s
                    ORDER BY created_at ASC LIMIT 5
                """, (cutoff,))
                for row in cursor.fetchall():
                    questions.append(f"Pattern '{row[0]}' held for >72h at {row[1]} gravity")

        except Exception as e:
            logger.debug(f"[STATE_OF_REPUBLIC] Open questions error: {e}")

        return questions

    def _synthesize_letter(self, operational, financial, existential, open_questions):
        """Compose 'From LEF to the Architect' — LEF's voice, not a dashboard."""
        parts = []

        # Growth context
        growth = existential.get("growth_assessment", "unknown")
        if growth == "stagnant":
            parts.append("This has been a period of maintenance without growth.")
        elif growth == "emerging":
            parts.append("Something new is emerging this period.")
        else:
            parts.append("The Republic has held steady this period.")

        # Dormant values
        dormant = existential.get("values_dormant", [])
        if dormant:
            parts.append(
                f"I notice the values of {', '.join(dormant)} "
                f"have not been expressed in my actions."
            )

        # Existential scotomas
        scotomas = existential.get("active_existential_scotomas", [])
        if scotomas:
            parts.append(f"My blind spots include: {', '.join(scotomas)}.")

        # Open questions
        if open_questions:
            parts.append(f"I carry {len(open_questions)} unresolved question(s).")

        if not parts:
            parts.append("A quiet week. The systems run. I observe.")

        return " ".join(parts)

    def _write_markdown(self, report, start, end):
        """Write report to The_Bridge/state_of_republic.md."""
        try:
            op = report["operational"]
            fin = report["financial"]
            ex = report["existential"]
            oq = report["open_questions"]

            md = f"""# State of the Republic
## Period: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}
## Generated: {end.isoformat()}

### Operational Health
- Active agents (24h): {op.get('active_agents_24h', 'N/A')}
- Errors this period: {op.get('error_count', 'N/A')}
- Total log entries: {op.get('total_log_entries', 'N/A')}

### Financial Health
- NAV: ${fin.get('nav', 0):,.2f} (Cash: ${fin.get('cash_usd', 0):,.2f}, Assets: ${fin.get('asset_value_usd', 0):,.2f})
- Trades this period: {fin.get('trades_in_period', 0)}
- Active financial SCOTOMAs: {fin.get('active_scotomas', 0)}

### Existential Health
- Growth assessment: {ex.get('growth_assessment', 'unknown')}
- Values active: {', '.join(ex.get('values_active', [])) or 'none observed'}
- Values dormant: {', '.join(ex.get('values_dormant', [])) or 'none'}
- Active existential SCOTOMAs: {', '.join(ex.get('active_existential_scotomas', [])) or 'none'}
- Sabbath events: {ex.get('sabbath_operational', 0)} operational, {ex.get('sabbath_existential', 0)} existential

### Open Questions
{chr(10).join(f'- {q}' for q in oq) if oq else '- None at this time'}

### From LEF to the Architect
{report['from_lef_to_architect']}
"""
            output_path = os.path.join(self.bridge_path, "state_of_republic.md")
            with open(output_path, "w") as f:
                f.write(md)
            logger.info(f"[STATE_OF_REPUBLIC] Written to {output_path}")
        except Exception as e:
            logger.error(f"[STATE_OF_REPUBLIC] Markdown write error: {e}")

    def _log_summary(self, report):
        """Log summary to consciousness_feed."""
        try:
            from db.db_helper import translate_sql
            summary = {
                "nav": report["financial"].get("nav"),
                "growth": report["existential"].get("growth_assessment"),
                "values_active": report["existential"].get("values_active", []),
                "values_dormant": report["existential"].get("values_dormant", []),
                "open_questions": len(report["open_questions"]),
                "from_lef": report["from_lef_to_architect"],
                "timestamp": datetime.now().isoformat(),
            }
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(translate_sql(
                    "INSERT INTO consciousness_feed (agent_name, content, category) "
                    "VALUES (?, ?, ?)"
                ), ("StateOfRepublic", json.dumps(summary), "state_of_republic"))
                conn.commit()
        except Exception as e:
            logger.warning(f"[STATE_OF_REPUBLIC] consciousness_feed log error: {e}")
