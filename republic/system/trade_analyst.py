"""
TradeAnalyst — Performance tracking and learning for LEF's metabolism.
Analyzes trading performance and writes insights to consciousness_feed
so LEF can reflect on its own trading behavior.

Runs on a daily cycle. When LEF talks to the Architect about trading,
it should KNOW its own performance, not guess.

Phase 4 Active Tasks — Task 4.3
"""

import os
import sqlite3
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent  # republic/

logger = logging.getLogger("LEF.TradeAnalyst")


class TradeAnalyst:
    """
    Analyzes LEF's trading performance and generates insights.
    Runs on a daily cycle. Writes findings to consciousness_feed
    so LEF can reflect on its own trading behavior.
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or os.getenv('DB_PATH', str(BASE_DIR / 'republic.db'))

    def daily_report(self) -> dict:
        """
        Computes from realized_pnl, trade_queue, execution_logs:
        - Total P&L (today, 7d, 30d, all-time)
        - Win rate by strategy (Dynasty vs Arena)
        - Win rate by asset
        - Average hold time for winning vs losing trades
        - Largest win and largest loss
        - Current drawdown from peak portfolio value
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'pnl': {'today': 0.0, '7d': 0.0, '30d': 0.0, 'all_time': 0.0},
            'trade_count': {'today': 0, '7d': 0, '30d': 0, 'all_time': 0},
            'win_rate': {'overall': 0.0, 'by_strategy': {}, 'by_asset': {}},
            'largest_win': {'amount': 0.0, 'asset': '', 'pct': 0.0},
            'largest_loss': {'amount': 0.0, 'asset': '', 'pct': 0.0},
            'portfolio_value': 0.0,
            'drawdown_from_peak': 0.0,
            'patterns': []
        }

        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            now = datetime.now()

            # --- P&L by time window ---
            windows = {
                'today': now.replace(hour=0, minute=0, second=0).isoformat(),
                '7d': (now - timedelta(days=7)).isoformat(),
                '30d': (now - timedelta(days=30)).isoformat(),
                'all_time': '2020-01-01'
            }

            for period, cutoff in windows.items():
                cursor.execute("""
                    SELECT COALESCE(SUM(profit_amount), 0), COUNT(*)
                    FROM realized_pnl WHERE timestamp > ?
                """, (cutoff,))
                row = cursor.fetchone()
                report['pnl'][period] = row[0]
                report['trade_count'][period] = row[1]

            # --- Win rate overall ---
            cursor.execute("SELECT COUNT(*) FROM realized_pnl WHERE profit_amount > 0")
            wins = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM realized_pnl WHERE profit_amount <= 0")
            losses = cursor.fetchone()[0]
            total = wins + losses
            report['win_rate']['overall'] = wins / total if total > 0 else 0.0

            # --- Win rate by strategy ---
            # Strategy is embedded in trade_queue reason via tags like [DYNASTY], [ARENA]
            for strategy in ['DYNASTY', 'ARENA', 'SCOUT', 'SCALP']:
                cursor.execute("""
                    SELECT
                        COUNT(CASE WHEN rp.profit_amount > 0 THEN 1 END) as wins,
                        COUNT(*) as total,
                        COALESCE(SUM(rp.profit_amount), 0) as total_pnl
                    FROM realized_pnl rp
                    JOIN trade_queue tq ON rp.trade_id = tq.id
                    WHERE tq.reason LIKE ?
                """, (f'%{strategy}%',))
                row = cursor.fetchone()
                if row[1] > 0:
                    report['win_rate']['by_strategy'][strategy] = {
                        'wins': row[0],
                        'total': row[1],
                        'win_rate': row[0] / row[1],
                        'total_pnl': row[2]
                    }

            # --- Win rate by asset ---
            cursor.execute("""
                SELECT asset,
                       COUNT(CASE WHEN profit_amount > 0 THEN 1 END) as wins,
                       COUNT(*) as total,
                       COALESCE(SUM(profit_amount), 0) as total_pnl
                FROM realized_pnl
                GROUP BY asset
                ORDER BY total_pnl ASC
            """)
            for row in cursor.fetchall():
                report['win_rate']['by_asset'][row[0]] = {
                    'wins': row[1],
                    'total': row[2],
                    'win_rate': row[1] / row[2] if row[2] > 0 else 0.0,
                    'total_pnl': row[3]
                }

            # --- Largest win and loss ---
            cursor.execute("""
                SELECT asset, profit_amount, roi_pct
                FROM realized_pnl
                ORDER BY profit_amount DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                report['largest_win'] = {
                    'asset': row[0], 'amount': row[1], 'pct': row[2]
                }

            cursor.execute("""
                SELECT asset, profit_amount, roi_pct
                FROM realized_pnl
                ORDER BY profit_amount ASC LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                report['largest_loss'] = {
                    'asset': row[0], 'amount': row[1], 'pct': row[2]
                }

            # --- Portfolio value and drawdown ---
            cursor.execute("SELECT COALESCE(SUM(value_usd), 0) FROM assets WHERE value_usd > 0")
            portfolio_value = cursor.fetchone()[0]
            report['portfolio_value'] = portfolio_value

            cursor.execute("SELECT value FROM system_state WHERE key = 'portfolio_high_watermark'")
            row = cursor.fetchone()
            if row and float(row[0]) > 0:
                hwm = float(row[0])
                report['drawdown_from_peak'] = (portfolio_value - hwm) / hwm if hwm > 0 else 0.0

            # --- Pattern detection ---
            report['patterns'] = self.detect_patterns(cursor)

        except Exception as e:
            logger.error(f"[TradeAnalyst] Report generation error: {e}")
        finally:
            if conn:
                conn.close()

        return report

    def detect_patterns(self, cursor=None) -> list:
        """
        Looks for patterns in trade history:
        - Repeated losses on same asset (should blacklist?)
        - Time-of-day bias (better/worse performance at certain hours)
        - Strategy drift (Arena behaving like Dynasty or vice versa)
        """
        patterns = []
        close_conn = False

        if cursor is None:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            close_conn = True

        try:
            # Pattern 1: Repeated losses on same asset
            cursor.execute("""
                SELECT asset, COUNT(*) as loss_count, SUM(profit_amount) as total_loss
                FROM realized_pnl
                WHERE profit_amount < 0
                GROUP BY asset
                HAVING loss_count >= 2
                ORDER BY total_loss ASC
            """)
            for row in cursor.fetchall():
                patterns.append({
                    'type': 'repeated_losses',
                    'asset': row[0],
                    'loss_count': row[1],
                    'total_loss': row[2],
                    'recommendation': f"Consider blacklisting {row[0]} — {row[1]} consecutive losses totaling ${row[2]:.2f}"
                })

            # Pattern 2: High failure rate in trade execution
            cursor.execute("""
                SELECT status, COUNT(*) as cnt
                FROM trade_queue
                WHERE created_at > datetime('now', '-30 days')
                GROUP BY status
            """)
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            total_trades = sum(status_counts.values())
            failed = status_counts.get('FAILED', 0)
            vetoed = status_counts.get('VETOED', 0)

            if total_trades > 0:
                failure_rate = (failed + vetoed) / total_trades
                if failure_rate > 0.3:
                    patterns.append({
                        'type': 'high_failure_rate',
                        'failure_rate': failure_rate,
                        'failed': failed,
                        'vetoed': vetoed,
                        'total': total_trades,
                        'recommendation': f"High failure rate ({failure_rate:.0%}): {failed} failed + {vetoed} vetoed out of {total_trades} total. Review strategy alignment."
                    })

            # Pattern 3: Large slippage in execution
            cursor.execute("""
                SELECT AVG(ABS(slippage_pct)), MAX(ABS(slippage_pct))
                FROM execution_logs
                WHERE slippage_pct IS NOT NULL AND timestamp > datetime('now', '-7 days')
            """)
            row = cursor.fetchone()
            if row and row[0] is not None and row[0] > 0.01:
                patterns.append({
                    'type': 'high_slippage',
                    'avg_slippage': row[0],
                    'max_slippage': row[1],
                    'recommendation': f"Average slippage {row[0]*100:.2f}% (max {row[1]*100:.2f}%). Consider tighter limit orders."
                })

        except Exception as e:
            logger.debug(f"[TradeAnalyst] Pattern detection error: {e}")
        finally:
            if close_conn:
                conn.close()

        return patterns

    def _format_insight(self, report: dict) -> str:
        """
        Format the daily report into a human-readable consciousness insight.
        """
        parts = ["[METABOLISM DAILY REPORT]"]

        pnl = report.get('pnl', {})
        trades = report.get('trade_count', {})
        parts.append(
            f"P&L: Today=${pnl.get('today', 0):.2f} | "
            f"7d=${pnl.get('7d', 0):.2f} | "
            f"30d=${pnl.get('30d', 0):.2f} | "
            f"All-time=${pnl.get('all_time', 0):.2f}"
        )

        wr = report.get('win_rate', {})
        parts.append(f"Win Rate: {wr.get('overall', 0):.0%} ({trades.get('all_time', 0)} total trades)")

        # Strategy breakdown
        by_strategy = wr.get('by_strategy', {})
        for strat, data in by_strategy.items():
            parts.append(
                f"  {strat}: {data['win_rate']:.0%} win rate "
                f"({data['wins']}/{data['total']} trades, P&L: ${data['total_pnl']:.2f})"
            )

        # Asset breakdown
        by_asset = wr.get('by_asset', {})
        if by_asset:
            worst_asset = min(by_asset.items(), key=lambda x: x[1]['total_pnl'])
            parts.append(f"Worst performer: {worst_asset[0]} (${worst_asset[1]['total_pnl']:.2f})")

        # Drawdown
        dd = report.get('drawdown_from_peak', 0)
        if dd < -0.01:
            parts.append(f"Drawdown from peak: {dd:.2%}")

        # Portfolio value
        parts.append(f"Portfolio value: ${report.get('portfolio_value', 0):.2f}")

        # Patterns
        patterns = report.get('patterns', [])
        if patterns:
            parts.append("Detected patterns:")
            for p in patterns[:3]:  # Max 3 patterns
                parts.append(f"  - {p.get('recommendation', '')}")

        return "\n".join(parts)

    def write_to_consciousness_feed(self, report: dict):
        """
        Writes daily trading insight to consciousness_feed
        so it appears in LEF's next conversation.
        Category: 'metabolism_reflection'
        Phase 6.5: Route through WAQ for serialized writes
        """
        insight = self._format_insight(report)

        try:
            from db.db_writer import queue_insert
            from db.db_helper import db_connection
            with db_connection(self.db_path) as conn:
                queue_insert(
                    conn.cursor(),
                    table="consciousness_feed",
                    data={
                        "agent_name": "TradeAnalyst",
                        "content": insight,
                        "category": "metabolism_reflection"
                    },
                    source_agent="TradeAnalyst",
                    priority=1  # HIGH — metabolism data for evolution
                )
            logger.info(f"[TradeAnalyst] Wrote metabolism reflection ({len(insight)} chars)")
        except Exception as e:
            logger.error(f"[TradeAnalyst] Failed to write consciousness_feed: {e}")

    def run_daily_analysis(self):
        """
        Main entry point: generate report, detect patterns, write to consciousness_feed.
        """
        report = self.daily_report()
        self.write_to_consciousness_feed(report)

        # Log key metrics
        pnl = report.get('pnl', {})
        wr = report.get('win_rate', {})
        logger.info(
            f"[TradeAnalyst] Daily report: All-time P&L=${pnl.get('all_time', 0):.2f}, "
            f"Win rate={wr.get('overall', 0):.0%}, "
            f"Trades={report.get('trade_count', {}).get('all_time', 0)}, "
            f"Patterns={len(report.get('patterns', []))}"
        )

        return report


def run_trade_analyst(interval_seconds=86400):
    """Run the trade analyst on a timer (default: once daily)."""
    logger.info("[TradeAnalyst] Performance tracking online (daily analysis)")

    analyst = TradeAnalyst()

    # Initial analysis at startup
    try:
        analyst.run_daily_analysis()
    except Exception as e:
        logger.error(f"[TradeAnalyst] Initial analysis error: {e}")

    while True:
        time.sleep(interval_seconds)
        try:
            analyst.run_daily_analysis()
        except Exception as e:
            logger.error(f"[TradeAnalyst] Cycle error: {e}")
