"""
Metabolism Domain Observer — Watches trading performance and proposes strategy changes.

Reads from:
- realized_pnl table (trade outcomes)
- TradeAnalyst reports in consciousness_feed (daily performance)
- wealth_strategy.json (current config)
- Backtest results (if available)

Can propose changes to:
- Strategy allocation weights (Dynasty % vs Arena %)
- Take-profit and stop-loss thresholds
- Asset inclusion/exclusion
- Position sizing parameters

Design reference: External Observer Reports/EVOLUTION_ARCHITECTURE.md — Domain 1
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent  # republic/
PROJECT_DIR = BASE_DIR.parent  # LEF Ai/
WEALTH_STRATEGY_PATH = str(BASE_DIR / 'config' / 'wealth_strategy.json')


class MetabolismObserver:
    """Observes trading performance and proposes config changes."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def observe(self) -> dict:
        """
        Collect trading performance data.
        Returns patterns with evidence and confidence level.
        """
        patterns = []

        try:
            patterns.extend(self._analyze_strategy_performance())
        except Exception as e:
            logger.warning(f"[METABOLISM_OBS] Strategy analysis failed: {e}")

        try:
            patterns.extend(self._analyze_asset_performance())
        except Exception as e:
            logger.warning(f"[METABOLISM_OBS] Asset analysis failed: {e}")

        try:
            patterns.extend(self._analyze_threshold_effectiveness())
        except Exception as e:
            logger.warning(f"[METABOLISM_OBS] Threshold analysis failed: {e}")

        return {
            'domain': 'metabolism',
            'patterns': patterns,
            'timestamp': datetime.now().isoformat()
        }

    def _get_strategy_config(self) -> dict:
        """Load current wealth strategy config."""
        try:
            with open(WEALTH_STRATEGY_PATH, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"[METABOLISM_OBS] Could not read wealth_strategy.json: {e}")
            return {}

    def _query_realized_pnl(self, days: int = 90) -> list:
        """Query realized_pnl table for trades in the given window."""
        try:
            from db.db_helper import db_connection
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            with db_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT asset, profit_amount, roi_pct, timestamp "
                    "FROM realized_pnl WHERE timestamp >= ? "
                    "ORDER BY timestamp DESC",
                    (cutoff,)
                )
                rows = cursor.fetchall()
                return [
                    {
                        'asset': row[0] if isinstance(row, tuple) else row['asset'],
                        'profit_amount': row[1] if isinstance(row, tuple) else row['profit_amount'],
                        'roi_pct': row[2] if isinstance(row, tuple) else row['roi_pct'],
                        'timestamp': row[3] if isinstance(row, tuple) else row['timestamp'],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"[METABOLISM_OBS] realized_pnl query failed: {e}")
            return []

    def _classify_trade_strategy(self, asset: str, config: dict) -> str:
        """Determine which strategy a trade belongs to based on asset lists."""
        dynasty_assets = config.get('DYNASTY', {}).get('assets', [])
        arena_assets = config.get('ARENA', {}).get('assets', [])

        # Normalize: strip -USD suffix if present
        clean_asset = asset.replace('-USD', '').replace('-usd', '')

        if clean_asset in dynasty_assets:
            return 'DYNASTY'
        elif clean_asset in arena_assets:
            return 'ARENA'
        return 'UNKNOWN'

    def _analyze_strategy_performance(self) -> list:
        """
        Compare Dynasty vs Arena over 7d, 30d, 90d windows.
        Flag if one consistently underperforms.
        """
        patterns = []
        config = self._get_strategy_config()
        if not config:
            return patterns

        for window_days, window_label in [(7, '7d'), (30, '30d'), (90, '90d')]:
            trades = self._query_realized_pnl(days=window_days)
            if not trades:
                continue

            # Group by strategy
            dynasty_trades = [t for t in trades if self._classify_trade_strategy(t['asset'], config) == 'DYNASTY']
            arena_trades = [t for t in trades if self._classify_trade_strategy(t['asset'], config) == 'ARENA']

            for strategy, strategy_trades in [('DYNASTY', dynasty_trades), ('ARENA', arena_trades)]:
                if len(strategy_trades) < 3:
                    continue  # Need minimum sample

                wins = [t for t in strategy_trades if (t.get('profit_amount') or 0) > 0]
                win_rate = len(wins) / len(strategy_trades) if strategy_trades else 0
                total_pnl = sum(t.get('profit_amount', 0) or 0 for t in strategy_trades)

                # Flag strategies with poor performance
                if win_rate < 0.25 and len(strategy_trades) >= 5:
                    patterns.append({
                        'description': f"{strategy} win rate critically low ({win_rate:.0%}) over {window_label}",
                        'evidence': f"{len(wins)}/{len(strategy_trades)} winning trades, total P&L: ${total_pnl:.2f}",
                        'confidence': 'high' if len(strategy_trades) >= 10 else 'medium',
                        'strategy': strategy,
                        'metric': 'win_rate',
                        'value': win_rate,
                        'window': window_label,
                    })

                if total_pnl < -100 and len(strategy_trades) >= 5:
                    patterns.append({
                        'description': f"{strategy} cumulative loss exceeds $100 over {window_label}",
                        'evidence': f"Total P&L: ${total_pnl:.2f} across {len(strategy_trades)} trades",
                        'confidence': 'high' if len(strategy_trades) >= 10 else 'medium',
                        'strategy': strategy,
                        'metric': 'cumulative_loss',
                        'value': total_pnl,
                        'window': window_label,
                    })

        return patterns

    def _analyze_asset_performance(self) -> list:
        """
        Per-asset win rate and P&L.
        Flag repeated losers for blacklist consideration.
        """
        patterns = []
        trades = self._query_realized_pnl(days=90)
        if not trades:
            return patterns

        # Group by asset
        asset_stats = {}
        for t in trades:
            asset = t.get('asset', 'UNKNOWN')
            if asset not in asset_stats:
                asset_stats[asset] = {'wins': 0, 'losses': 0, 'total_pnl': 0, 'trades': 0}
            asset_stats[asset]['trades'] += 1
            pnl = t.get('profit_amount', 0) or 0
            asset_stats[asset]['total_pnl'] += pnl
            if pnl > 0:
                asset_stats[asset]['wins'] += 1
            else:
                asset_stats[asset]['losses'] += 1

        for asset, stats in asset_stats.items():
            if stats['trades'] < 3:
                continue  # Need minimum sample

            win_rate = stats['wins'] / stats['trades']

            # Flag assets with 0% win rate and 3+ trades
            if win_rate == 0 and stats['trades'] >= 3:
                patterns.append({
                    'description': f"Asset {asset} has 0% win rate across {stats['trades']} trades",
                    'evidence': f"0/{stats['trades']} wins, total P&L: ${stats['total_pnl']:.2f}",
                    'confidence': 'high' if stats['trades'] >= 5 else 'medium',
                    'asset': asset,
                    'metric': 'zero_win_rate',
                    'value': stats['total_pnl'],
                })

            # Flag assets with significant cumulative loss
            if stats['total_pnl'] < -50 and win_rate < 0.3:
                patterns.append({
                    'description': f"Asset {asset} consistently losing: {win_rate:.0%} win rate, ${stats['total_pnl']:.2f} total",
                    'evidence': f"{stats['wins']}/{stats['trades']} wins over 90d",
                    'confidence': 'high' if stats['trades'] >= 5 else 'medium',
                    'asset': asset,
                    'metric': 'consistent_loser',
                    'value': stats['total_pnl'],
                })

        return patterns

    def _analyze_threshold_effectiveness(self) -> list:
        """
        How often do trades hit take-profit vs stop-loss?
        If stop-loss hit rate > 70%, threshold may be too tight.
        If take-profit never hit, threshold may be too aggressive.
        """
        patterns = []
        config = self._get_strategy_config()
        if not config:
            return patterns

        trades = self._query_realized_pnl(days=90)
        if not trades:
            return patterns

        for strategy in ['DYNASTY', 'ARENA']:
            strat_config = config.get(strategy, {})
            tp = strat_config.get('take_profit_threshold', strat_config.get('take_profit', 0))
            sl = strat_config.get('stop_loss_threshold', strat_config.get('stop_loss', 0))

            strategy_trades = [
                t for t in trades
                if self._classify_trade_strategy(t['asset'], config) == strategy
            ]

            if len(strategy_trades) < 5:
                continue

            # Check how ROI relates to thresholds
            tp_hits = [t for t in strategy_trades if (t.get('roi_pct') or 0) >= (tp * 100 if tp < 1 else tp)]
            sl_hits = [t for t in strategy_trades if (t.get('roi_pct') or 0) <= (sl * 100 if abs(sl) < 1 else sl)]

            tp_rate = len(tp_hits) / len(strategy_trades)
            sl_rate = len(sl_hits) / len(strategy_trades)

            if tp_rate == 0 and len(strategy_trades) >= 5:
                patterns.append({
                    'description': f"{strategy} take-profit ({tp:.0%}) never hit in {len(strategy_trades)} trades",
                    'evidence': f"0/{len(strategy_trades)} trades reached TP. Current TP: {tp:.0%}",
                    'confidence': 'high' if len(strategy_trades) >= 10 else 'medium',
                    'strategy': strategy,
                    'metric': 'tp_never_hit',
                    'value': tp,
                })

            if sl_rate > 0.7 and len(strategy_trades) >= 5:
                patterns.append({
                    'description': f"{strategy} stop-loss ({sl:.0%}) hit rate too high: {sl_rate:.0%}",
                    'evidence': f"{len(sl_hits)}/{len(strategy_trades)} trades hit SL. May be too tight.",
                    'confidence': 'high',
                    'strategy': strategy,
                    'metric': 'sl_too_tight',
                    'value': sl,
                })

        return patterns

    def generate_proposals(self, patterns: list) -> list:
        """
        Convert patterns into concrete config change proposals.
        Each proposal follows the schema in EVOLUTION_ARCHITECTURE.md.
        """
        proposals = []
        config = self._get_strategy_config()

        for pattern in patterns:
            metric = pattern.get('metric', '')
            strategy = pattern.get('strategy', '')
            asset = pattern.get('asset', '')

            # Take-profit never hit → propose lowering it
            if metric == 'tp_never_hit' and strategy:
                current_tp = pattern.get('value', 0)
                # Propose halving the TP threshold (but floor at 5%)
                new_tp = max(0.05, current_tp / 2)
                proposals.append({
                    'domain': 'metabolism',
                    'change_description': f"Lower {strategy} take-profit from {current_tp:.0%} to {new_tp:.0%}",
                    'config_path': 'republic/config/wealth_strategy.json',
                    'config_key': f'{strategy}.take_profit_threshold',
                    'old_value': current_tp,
                    'new_value': round(new_tp, 2),
                    'evidence': {
                        'data_source': 'realized_pnl',
                        'observation_period': '90 days',
                        'confidence': pattern.get('confidence', 'medium'),
                        'supporting_data': pattern.get('evidence', ''),
                    },
                    'risk_assessment': 'Lower TP means smaller gains per winning trade. Offset by higher win rate.',
                    'reversible': True,
                })

            # Stop-loss too tight → propose loosening it
            elif metric == 'sl_too_tight' and strategy:
                current_sl = pattern.get('value', 0)
                # Propose widening SL by 50% (more negative)
                new_sl = round(current_sl * 1.5, 2)
                proposals.append({
                    'domain': 'metabolism',
                    'change_description': f"Widen {strategy} stop-loss from {current_sl:.0%} to {new_sl:.0%}",
                    'config_path': 'republic/config/wealth_strategy.json',
                    'config_key': f'{strategy}.stop_loss_threshold',
                    'old_value': current_sl,
                    'new_value': new_sl,
                    'evidence': {
                        'data_source': 'realized_pnl',
                        'observation_period': '90 days',
                        'confidence': pattern.get('confidence', 'medium'),
                        'supporting_data': pattern.get('evidence', ''),
                    },
                    'risk_assessment': 'Wider SL increases max loss per trade. Offset by fewer stop-outs.',
                    'reversible': True,
                })

            # Asset with zero win rate → propose removal from strategy
            elif metric == 'zero_win_rate' and asset:
                # Find which strategy this asset belongs to
                for strat in ['DYNASTY', 'ARENA']:
                    assets = config.get(strat, {}).get('assets', [])
                    clean_asset = asset.replace('-USD', '').replace('-usd', '')
                    if clean_asset in assets:
                        new_assets = [a for a in assets if a != clean_asset]
                        proposals.append({
                            'domain': 'metabolism',
                            'change_description': f"Remove {clean_asset} from {strat} (0% win rate)",
                            'config_path': 'republic/config/wealth_strategy.json',
                            'config_key': f'{strat}.assets',
                            'old_value': assets,
                            'new_value': new_assets,
                            'evidence': {
                                'data_source': 'realized_pnl',
                                'observation_period': '90 days',
                                'confidence': pattern.get('confidence', 'medium'),
                                'supporting_data': pattern.get('evidence', ''),
                            },
                            'risk_assessment': f'Removing {clean_asset} reduces diversification. Offset by eliminating consistent loser.',
                            'reversible': True,
                        })
                        break

            # Strategy with critically low win rate → propose reducing allocation
            elif metric == 'win_rate' and strategy:
                current_alloc = config.get(strategy, {}).get('allocation_pct', 0)
                # Reduce allocation by 25%
                new_alloc = round(max(0.05, current_alloc * 0.75), 2)
                other_strategy = 'ARENA' if strategy == 'DYNASTY' else 'DYNASTY'
                other_alloc = round(1.0 - new_alloc, 2)

                proposals.append({
                    'domain': 'metabolism',
                    'change_description': f"Reduce {strategy} allocation from {current_alloc:.0%} to {new_alloc:.0%}",
                    'config_path': 'republic/config/wealth_strategy.json',
                    'config_key': f'{strategy}.allocation_pct',
                    'old_value': current_alloc,
                    'new_value': new_alloc,
                    'evidence': {
                        'data_source': 'realized_pnl',
                        'observation_period': pattern.get('window', '90d'),
                        'confidence': pattern.get('confidence', 'medium'),
                        'supporting_data': pattern.get('evidence', ''),
                    },
                    'risk_assessment': f'Lower {strategy} allocation shifts capital to {other_strategy}. Monitor for rebalancing effects.',
                    'reversible': True,
                })

        # Deduplicate: only keep one proposal per config_key
        seen_keys = set()
        unique_proposals = []
        for p in proposals:
            key = p.get('config_key', '')
            if key not in seen_keys:
                seen_keys.add(key)
                unique_proposals.append(p)

        return unique_proposals
