"""
BacktestEngine — Simple backtesting engine for LEF strategies.
Uses free OHLCV data from CoinGecko API (no API key needed for basic data).

Validates that LEF's Dynasty and Arena strategies work against historical data
before going live. This is the difference between a knowledgeable teen and
a mature trader.

Phase 4 Active Tasks — Task 4.4

Usage:
    python3 republic/tools/backtest_engine.py
"""

import os
import sys
import json
import time
import math
import sqlite3
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent  # republic/

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger("BacktestEngine")


class BacktestEngine:
    """
    Backtests LEF's trading strategies against historical price data.
    """

    # CoinGecko asset ID mapping (symbol -> coingecko id)
    COINGECKO_IDS = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'SOL': 'solana',
        'AVAX': 'avalanche-2',
        'DOGE': 'dogecoin',
        'SUI': 'sui',
        'PEPE': 'pepe',
        'WIF': 'dogwifcoin',
        'BONK': 'bonk',
        'LINK': 'chainlink',
        'ARB': 'arbitrum',
        'OP': 'optimism',
        'FET': 'artificial-superintelligence-alliance',
        'RNDR': 'render-token',
        'XRP': 'ripple'
    }

    def __init__(self):
        self.strategy_config = self._load_strategy_config()
        self.results = {}

    def _load_strategy_config(self) -> dict:
        """Load wealth_strategy.json for strategy parameters."""
        config_path = BASE_DIR / 'config' / 'wealth_strategy.json'
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {}

    def fetch_historical_data(self, asset: str, days: int = 365) -> pd.DataFrame:
        """
        Fetch daily OHLCV from CoinGecko.
        Returns DataFrame with columns: date, open, high, low, close
        """
        cg_id = self.COINGECKO_IDS.get(asset.upper())
        if not cg_id:
            logger.warning(f"No CoinGecko ID for {asset}. Skipping.")
            return pd.DataFrame()

        url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc"
        params = {'vs_currency': 'usd', 'days': str(days)}

        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                logger.warning(f"Rate limited by CoinGecko. Waiting 60s...")
                time.sleep(60)
                resp = requests.get(url, params=params, timeout=30)

            if resp.status_code != 200:
                logger.error(f"CoinGecko API error for {asset}: {resp.status_code}")
                return pd.DataFrame()

            data = resp.json()
            if not data:
                return pd.DataFrame()

            # CoinGecko OHLC returns [[timestamp, open, high, low, close], ...]
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.drop('timestamp', axis=1)
            df = df.sort_values('date').reset_index(drop=True)

            logger.info(f"Fetched {len(df)} candles for {asset} ({days}d)")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch data for {asset}: {e}")
            return pd.DataFrame()

    def run_strategy(self, strategy_name: str, strategy_config: dict,
                     data: pd.DataFrame, asset: str) -> dict:
        """
        Replay a strategy against historical data.

        Dynasty: Buy and hold with take-profit and stop-loss
        Arena: RSI-based mean reversion with tighter stops
        """
        if data.empty or len(data) < 10:
            return {'asset': asset, 'strategy': strategy_name, 'error': 'Insufficient data'}

        take_profit = strategy_config.get('take_profit_threshold', 0.5)
        stop_loss = strategy_config.get('stop_loss_threshold', -0.2)
        initial_capital = 1000.0  # Normalized $1000 starting capital

        prices = data['close'].values
        dates = data['date'].values

        trades = []
        capital = initial_capital
        position = None  # {'entry_price': float, 'entry_idx': int, 'shares': float}
        peak_capital = initial_capital
        max_drawdown = 0.0
        daily_returns = []

        for i in range(1, len(prices)):
            price = prices[i]
            prev_price = prices[i - 1]

            # Track daily return
            daily_ret = (price - prev_price) / prev_price if prev_price > 0 else 0
            daily_returns.append(daily_ret)

            if position is None:
                # Entry logic
                should_enter = False

                if strategy_name == 'DYNASTY':
                    # Dynasty: Buy on pullback (price drops > 5% from recent peak)
                    lookback = min(20, i)
                    recent_high = max(prices[i - lookback:i])
                    pullback = (price - recent_high) / recent_high
                    if pullback < -0.05:
                        should_enter = True

                elif strategy_name == 'ARENA':
                    # Arena: RSI-based entry (simplified RSI < 35)
                    if i >= 14:
                        gains = []
                        losses = []
                        for j in range(i - 14, i):
                            change = prices[j + 1] - prices[j]
                            if change > 0:
                                gains.append(change)
                            else:
                                losses.append(abs(change))

                        avg_gain = sum(gains) / 14 if gains else 0.001
                        avg_loss = sum(losses) / 14 if losses else 0.001
                        rs = avg_gain / avg_loss if avg_loss > 0 else 100
                        rsi = 100 - (100 / (1 + rs))

                        rsi_threshold = self.strategy_config.get('ARENA_PARAMS', {}).get('rsi_buy_threshold', 35.0)
                        if rsi < rsi_threshold:
                            should_enter = True

                if should_enter and capital > 0:
                    shares = capital / price
                    position = {
                        'entry_price': price,
                        'entry_idx': i,
                        'shares': shares,
                        'capital_used': capital
                    }
                    capital = 0

            else:
                # Exit logic
                entry_price = position['entry_price']
                roi = (price - entry_price) / entry_price
                should_exit = False
                exit_reason = ''

                # Take profit
                if roi >= take_profit:
                    should_exit = True
                    exit_reason = 'TAKE_PROFIT'

                # Stop loss
                elif roi <= stop_loss:
                    should_exit = True
                    exit_reason = 'STOP_LOSS'

                if should_exit:
                    exit_value = position['shares'] * price
                    profit = exit_value - position['capital_used']
                    hold_days = i - position['entry_idx']

                    trades.append({
                        'entry_price': entry_price,
                        'exit_price': price,
                        'profit': profit,
                        'roi_pct': roi,
                        'hold_days': hold_days,
                        'reason': exit_reason
                    })

                    capital = exit_value
                    position = None

                    # Update drawdown tracking
                    if capital > peak_capital:
                        peak_capital = capital
                    current_dd = (capital - peak_capital) / peak_capital if peak_capital > 0 else 0
                    max_drawdown = min(max_drawdown, current_dd)

        # Close any open position at end
        if position is not None:
            final_price = prices[-1]
            exit_value = position['shares'] * final_price
            profit = exit_value - position['capital_used']
            roi = (final_price - position['entry_price']) / position['entry_price']
            hold_days = len(prices) - 1 - position['entry_idx']

            trades.append({
                'entry_price': position['entry_price'],
                'exit_price': final_price,
                'profit': profit,
                'roi_pct': roi,
                'hold_days': hold_days,
                'reason': 'STILL_OPEN'
            })
            capital = exit_value

        # Compute metrics
        total_return_pct = (capital - initial_capital) / initial_capital if initial_capital > 0 else 0
        winning_trades = [t for t in trades if t['profit'] > 0]
        losing_trades = [t for t in trades if t['profit'] <= 0]
        win_rate = len(winning_trades) / len(trades) if trades else 0

        # Sharpe ratio (annualized, using daily returns)
        if daily_returns and len(daily_returns) > 1:
            avg_return = sum(daily_returns) / len(daily_returns)
            std_return = (sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns)) ** 0.5
            sharpe = (avg_return / std_return) * (365 ** 0.5) if std_return > 0 else 0
        else:
            sharpe = 0

        # Average hold times
        avg_hold_win = (
            sum(t['hold_days'] for t in winning_trades) / len(winning_trades)
            if winning_trades else 0
        )
        avg_hold_loss = (
            sum(t['hold_days'] for t in losing_trades) / len(losing_trades)
            if losing_trades else 0
        )

        worst_trade = min((t['roi_pct'] for t in trades), default=0)

        return {
            'asset': asset,
            'strategy': strategy_name,
            'total_return_pct': total_return_pct,
            'max_drawdown_pct': max_drawdown,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe,
            'trade_count': len(trades),
            'avg_hold_days_win': avg_hold_win,
            'avg_hold_days_loss': avg_hold_loss,
            'worst_trade_pct': worst_trade,
            'final_capital': capital,
            'trades': trades
        }

    def run_dynasty_backtest(self, days: int = 365) -> dict:
        """Backtest Dynasty strategy across configured assets."""
        dynasty_cfg = self.strategy_config.get('DYNASTY', {})
        assets = dynasty_cfg.get('assets', ['BTC', 'ETH', 'SOL', 'AVAX', 'DOGE'])

        results = {}
        for asset in assets:
            data = self.fetch_historical_data(asset, days)
            if data.empty:
                continue
            result = self.run_strategy('DYNASTY', dynasty_cfg, data, asset)
            results[asset] = result
            time.sleep(1.5)  # Rate limit courtesy

        # Aggregate
        if results:
            total_return = sum(r['total_return_pct'] for r in results.values()) / len(results)
            max_dd = min(r['max_drawdown_pct'] for r in results.values())
            avg_win_rate = sum(r['win_rate'] for r in results.values()) / len(results)
            total_trades = sum(r['trade_count'] for r in results.values())
            avg_sharpe = sum(r['sharpe_ratio'] for r in results.values()) / len(results)

            results['_aggregate'] = {
                'strategy': 'DYNASTY',
                'avg_return_pct': total_return,
                'max_drawdown_pct': max_dd,
                'avg_win_rate': avg_win_rate,
                'total_trades': total_trades,
                'avg_sharpe_ratio': avg_sharpe,
                'assets_tested': list(results.keys())
            }

        self.results['DYNASTY'] = results
        return results

    def run_arena_backtest(self, days: int = 365) -> dict:
        """Backtest Arena strategy across configured assets."""
        arena_cfg = self.strategy_config.get('ARENA', {})
        # Use first 5 Arena assets to respect CoinGecko rate limits
        assets = arena_cfg.get('assets', ['SUI', 'PEPE', 'WIF', 'BONK'])[:5]

        results = {}
        for asset in assets:
            # Strip -USD suffix if present
            clean_asset = asset.replace('-USD', '')
            data = self.fetch_historical_data(clean_asset, days)
            if data.empty:
                continue
            result = self.run_strategy('ARENA', arena_cfg, data, clean_asset)
            results[clean_asset] = result
            time.sleep(1.5)  # Rate limit courtesy

        # Aggregate
        if results:
            total_return = sum(r['total_return_pct'] for r in results.values()) / len(results)
            max_dd = min(r['max_drawdown_pct'] for r in results.values())
            avg_win_rate = sum(r['win_rate'] for r in results.values()) / len(results)
            total_trades = sum(r['trade_count'] for r in results.values())
            avg_sharpe = sum(r['sharpe_ratio'] for r in results.values()) / len(results)

            results['_aggregate'] = {
                'strategy': 'ARENA',
                'avg_return_pct': total_return,
                'max_drawdown_pct': max_dd,
                'avg_win_rate': avg_win_rate,
                'total_trades': total_trades,
                'avg_sharpe_ratio': avg_sharpe,
                'assets_tested': list(results.keys())
            }

        self.results['ARENA'] = results
        return results

    def generate_report(self) -> str:
        """
        Human-readable backtest report.
        Also writes to consciousness_feed so LEF knows its strategy's history.
        """
        lines = []
        lines.append("=" * 60)
        lines.append("LEF STRATEGY BACKTEST REPORT")
        lines.append(f"Generated: {datetime.now().isoformat()[:19]}")
        lines.append("=" * 60)

        for strategy_name, results in self.results.items():
            agg = results.get('_aggregate', {})
            if not agg:
                continue

            lines.append(f"\n--- {strategy_name} STRATEGY ---")
            lines.append(f"Assets tested: {', '.join([a for a in agg.get('assets_tested', []) if not a.startswith('_')])}")
            lines.append(f"Average return: {agg.get('avg_return_pct', 0):.2%}")
            lines.append(f"Max drawdown: {agg.get('max_drawdown_pct', 0):.2%}")
            lines.append(f"Average win rate: {agg.get('avg_win_rate', 0):.0%}")
            lines.append(f"Average Sharpe ratio: {agg.get('avg_sharpe_ratio', 0):.2f}")
            lines.append(f"Total trades: {agg.get('total_trades', 0)}")

            # Per-asset breakdown
            lines.append("\nPer-asset results:")
            for asset, result in results.items():
                if asset.startswith('_'):
                    continue
                if isinstance(result, dict) and 'total_return_pct' in result:
                    lines.append(
                        f"  {asset}: Return={result['total_return_pct']:.2%}, "
                        f"Drawdown={result['max_drawdown_pct']:.2%}, "
                        f"Win Rate={result['win_rate']:.0%}, "
                        f"Trades={result['trade_count']}, "
                        f"Sharpe={result['sharpe_ratio']:.2f}"
                    )

        # Overall assessment
        lines.append("\n" + "=" * 60)
        dynasty_agg = self.results.get('DYNASTY', {}).get('_aggregate', {})
        arena_agg = self.results.get('ARENA', {}).get('_aggregate', {})

        if dynasty_agg and arena_agg:
            d_ret = dynasty_agg.get('avg_return_pct', 0)
            a_ret = arena_agg.get('avg_return_pct', 0)
            if d_ret > a_ret:
                lines.append(f"Dynasty outperforms Arena by {(d_ret - a_ret):.2%}")
            else:
                lines.append(f"Arena outperforms Dynasty by {(a_ret - d_ret):.2%}")

        lines.append("=" * 60)

        report = "\n".join(lines)

        # Write to consciousness_feed
        self._write_to_consciousness_feed(report)

        return report

    def _write_to_consciousness_feed(self, report: str):
        """Write backtest results to consciousness_feed."""
        db_path = os.getenv('DB_PATH', str(BASE_DIR / 'republic.db'))
        try:
            conn = sqlite3.connect(db_path, timeout=30)
            # Truncate for consciousness_feed (keep it concise)
            summary = report[:2000]
            conn.execute(
                "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)",
                ("BacktestEngine", summary, "metabolism_reflection")
            )
            conn.commit()
            conn.close()
            logger.info("[BacktestEngine] Results written to consciousness_feed")
        except Exception as e:
            logger.error(f"[BacktestEngine] Failed to write consciousness_feed: {e}")


def main():
    """Run full backtest suite."""
    engine = BacktestEngine()

    print("Running Dynasty backtest (1 year)...")
    dynasty_results = engine.run_dynasty_backtest(days=365)

    print("\nRunning Arena backtest (1 year)...")
    arena_results = engine.run_arena_backtest(days=365)

    print("\n")
    report = engine.generate_report()
    print(report)


if __name__ == "__main__":
    main()
