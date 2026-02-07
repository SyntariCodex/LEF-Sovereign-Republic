#!/usr/bin/env python3
"""
Fulcrum Monitor Agent

Monitors Fulcrum's performance metrics, trading patterns, and system health.
Acts as a bridge between Fulcrum and potential code modifications.

Architecture:
1. Data Collection: Gathers metrics from Fulcrum's operation
2. Analysis: Evaluates performance against thresholds and targets
3. Decision Making: Identifies optimization opportunities
4. Recommendation: Suggests code modifications or parameter adjustments
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple


class MonitorAgent:
    """
    Autonomous monitoring agent for Fulcrum.
    Collects metrics, analyzes performance, and suggests optimizations.
    """
    
    def __init__(self, db_path: str = None, config_path: str = 'monitor_config.json'):
        if db_path is None:
             BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
             self.db_path = os.path.join(BASE_DIR, 'republic.db')
        else:
             self.db_path = db_path
        """
        Initialize the monitor agent.
        
        Args:
            db_path: Path to Fulcrum's SQLite database
            config_path: Path to monitor configuration file
        """
        self.db_path = db_path
        self.config_path = config_path
        self.config = self._load_config()
        
        # Initialize performance metrics
        self.metrics = {
            'system_health': {},
            'trading_performance': {},
            'capital_utilization': {},
            'tax_efficiency': {},
            'bucket_metrics': {},
            'diversification': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Initialize optimization recommendations
        self.recommendations = []
        
        # Ensure monitoring tables exist
        self._ensure_tables_exist()
    
    def _load_config(self) -> Dict:
        """Load configuration or create default if not exists"""
        default_config = {
            'thresholds': {
                'win_rate_min': 0.55,
                'win_rate_target': 0.60,
                'capital_utilization_min': 0.70,
                'irs_bucket_ratio_min': 0.80,
                'irs_bucket_ratio_max': 1.50,
                'diversification_min': 10,  # Min number of distinct coins
                'max_concentration': 0.25   # Max % of portfolio in single asset
            },
            'monitoring_frequency': {
                'system_health': 24,       # Hours
                'trading_performance': 72,  # Hours
                'capital_utilization': 48,  # Hours
                'diversification': 168,     # Hours (weekly)
                'tax_efficiency': 720       # Hours (monthly)
            },
            'alert_levels': {
                'info': 0,
                'warning': 1,
                'critical': 2
            }
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except:
                return default_config
        else:
            # Create default config
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
    
    def _ensure_tables_exist(self):
        """Ensure monitoring tables exist in database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Performance metrics history
        c.execute('''CREATE TABLE IF NOT EXISTS monitor_metrics
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  metrics_json TEXT)''')
        
        # Recommendations log
        c.execute('''CREATE TABLE IF NOT EXISTS monitor_recommendations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  recommendation_type TEXT,
                  priority INTEGER,
                  description TEXT,
                  suggested_implementation TEXT,
                  implemented BOOLEAN DEFAULT 0)''')
        
        # System health log
        c.execute('''CREATE TABLE IF NOT EXISTS monitor_health_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  component TEXT,
                  status TEXT,
                  message TEXT,
                  alert_level INTEGER DEFAULT 0)''')
        
        conn.commit()
        conn.close()
    
    def collect_metrics(self) -> Dict:
        """
        Collect performance metrics from Fulcrum's database.
        
        Returns:
            Dict of collected metrics
        """
        try:
            # System health metrics
            self.metrics['system_health'] = self._collect_system_health()
            
            # Trading performance metrics
            self.metrics['trading_performance'] = self._collect_trading_metrics()
            
            # Capital utilization metrics
            self.metrics['capital_utilization'] = self._collect_capital_metrics()
            
            # Tax efficiency metrics
            self.metrics['tax_efficiency'] = self._collect_tax_metrics()
            
            # Bucket metrics
            self.metrics['bucket_metrics'] = self._collect_bucket_metrics()
            
            # Diversification metrics
            self.metrics['diversification'] = self._collect_diversification_metrics()
            
            # Update timestamp
            self.metrics['timestamp'] = datetime.now().isoformat()
            
            # Save metrics to database
            self._save_metrics(self.metrics)
            
            return self.metrics
        except Exception as e:
            self._log_health_issue("metrics_collection", "error", 
                                  f"Failed to collect metrics: {str(e)}", 2)
            return {"error": str(e)}
    
    def _collect_system_health(self) -> Dict:
        """Collect system health metrics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        metrics = {
            'database_size_mb': 0,
            'trade_count': 0,
            'last_trade_timestamp': None,
            'error_count': 0
        }
        
        try:
            # Get database size
            db_path = os.path.abspath(self.db_path)
            if os.path.exists(db_path):
                metrics['database_size_mb'] = os.path.getsize(db_path) / (1024 * 1024)
            
            # Get trade count
            c.execute("SELECT COUNT(*) FROM trade_history")
            metrics['trade_count'] = c.fetchone()[0]
            
            # Get last trade timestamp
            c.execute("SELECT MAX(date) FROM trade_history")
            last_trade = c.fetchone()[0]
            metrics['last_trade_timestamp'] = last_trade if last_trade else None
            
            # Check for recent errors in monitor health log
            c.execute("""
                SELECT COUNT(*) FROM monitor_health_log 
                WHERE alert_level >= 2 
                AND timestamp > datetime('now', '-24 hours')
            """)
            metrics['error_count'] = c.fetchone()[0]
            
            conn.close()
            return metrics
        except Exception as e:
            conn.close()
            self._log_health_issue("system_health_collection", "error", 
                                  f"Failed to collect system health: {str(e)}", 2)
            return {"error": str(e)}
    
    def _collect_trading_metrics(self) -> Dict:
        """Collect trading performance metrics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        metrics = {
            'win_rate': 0,
            'avg_profit_per_trade': 0,
            'total_profit': 0,
            'avg_holding_period_days': 0,
            'trade_frequency': 0  # Trades per day
        }
        
        try:
            # Get win rate
            c.execute("SELECT COUNT(*) FROM trade_history WHERE profit > 0")
            wins = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM trade_history")
            total = c.fetchone()[0]
            
            metrics['win_rate'] = wins / total if total > 0 else 0
            
            # Get average profit per trade
            c.execute("SELECT AVG(profit) FROM trade_history")
            metrics['avg_profit_per_trade'] = c.fetchone()[0] or 0
            
            # Get total profit
            c.execute("SELECT SUM(profit) FROM trade_history")
            metrics['total_profit'] = c.fetchone()[0] or 0
            
            # Get average holding period (from reason field which includes "Holding: Xd")
            c.execute("SELECT reason FROM trade_history WHERE action = 'SELL'")
            holding_periods = []
            for row in c.fetchall():
                reason = row[0]
                if reason and "Holding:" in reason:
                    try:
                        # Extract days held from reason (format: "... Holding: 45d")
                        days_part = reason.split("Holding:")[1].strip().split("d")[0]
                        days = int(days_part)
                        holding_periods.append(days)
                    except:
                        pass
            
            metrics['avg_holding_period_days'] = sum(holding_periods) / len(holding_periods) if holding_periods else 0
            
            # Calculate trade frequency
            c.execute("""
                SELECT MIN(date), MAX(date), COUNT(*) 
                FROM trade_history
            """)
            result = c.fetchone()
            if result and result[0] and result[1]:
                first_date = datetime.strptime(result[0], '%Y-%m-%d')
                last_date = datetime.strptime(result[1], '%Y-%m-%d')
                days = (last_date - first_date).days
                metrics['trade_frequency'] = result[2] / days if days > 0 else 0
            
            conn.close()
            return metrics
        except Exception as e:
            conn.close()
            self._log_health_issue("trading_metrics_collection", "error", 
                                  f"Failed to collect trading metrics: {str(e)}", 1)
            return {"error": str(e)}
    
    def _collect_capital_metrics(self) -> Dict:
        """Collect capital utilization metrics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        metrics = {
            'cash_ratio': 0,  # Cash / Total portfolio value
            'holdings_ratio': 0,  # Holdings value / Total portfolio value
            'wallet_utilization': {},  # Per wallet utilization
            'avg_position_size': 0  # Average position size as % of portfolio
        }
        
        try:
            # This is a simplified version - in a real implementation,
            # you'd need to get actual portfolio values from the database
            # based on the data structure used
            
            # For demonstration purposes only
            metrics['cash_ratio'] = 0.25  # Placeholder
            metrics['holdings_ratio'] = 0.75  # Placeholder
            metrics['wallet_utilization'] = {
                "Dynasty_Core": 0.85,
                "Hunter_Tactical": 0.70,
                "Builder_Ecosystem": 0.80,
                "Yield_Vault": 0.95,
                "Experimental": 0.60
            }
            metrics['avg_position_size'] = 0.08  # Placeholder
            
            conn.close()
            return metrics
        except Exception as e:
            conn.close()
            self._log_health_issue("capital_metrics_collection", "error", 
                                  f"Failed to collect capital metrics: {str(e)}", 1)
            return {"error": str(e)}
    
    def _collect_tax_metrics(self) -> Dict:
        """Collect tax efficiency metrics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        metrics = {
            'long_term_gains_ratio': 0,  # Long-term gains / Total gains
            'short_term_gains_ratio': 0,  # Short-term gains / Total gains
            'loss_harvest_amount': 0,  # Total harvested losses
            'tax_saving_estimate': 0,  # Estimated tax savings
            'irs_bucket_coverage': 0  # IRS bucket balance / Estimated tax liability
        }
        
        try:
            # Get long term vs short term gains
            c.execute("""
                SELECT 
                    SUM(CASE WHEN reason LIKE '%Holding: ___ d%' AND profit > 0 THEN profit ELSE 0 END) as long_term,
                    SUM(CASE WHEN reason NOT LIKE '%Holding: ___ d%' AND profit > 0 THEN profit ELSE 0 END) as short_term,
                    SUM(profit) as total_profit
                FROM trade_history
                WHERE action = 'SELL'
            """)
            result = c.fetchone()
            long_term = result[0] or 0
            short_term = result[1] or 0
            total_profit = result[2] or 0
            
            if total_profit > 0:
                metrics['long_term_gains_ratio'] = long_term / total_profit
                metrics['short_term_gains_ratio'] = short_term / total_profit
            
            # Get harvested losses
            c.execute("""
                SELECT SUM(ABS(profit)) FROM trade_history 
                WHERE profit < 0 AND reason LIKE '%Tax loss harvesting%'
            """)
            metrics['loss_harvest_amount'] = c.fetchone()[0] or 0
            
            # Get IRS bucket coverage
            c.execute("""
                SELECT b.balance, 
                       (SELECT SUM(profit) FROM trade_history WHERE profit > 0) * 0.3 as tax_estimate
                FROM stablecoin_buckets b
                WHERE b.bucket_type = 'IRS_USDT'
            """)
            result = c.fetchone()
            if result:
                balance = result[0] or 0
                tax_estimate = result[1] or 1  # Avoid div by zero
                metrics['irs_bucket_coverage'] = balance / tax_estimate
            
            # Estimated tax savings (simplified)
            # In reality this would be much more complex based on tax brackets
            metrics['tax_saving_estimate'] = metrics['loss_harvest_amount'] * 0.25  # Simplified 25% tax bracket
            
            conn.close()
            return metrics
        except Exception as e:
            conn.close()
            self._log_health_issue("tax_metrics_collection", "error", 
                                  f"Failed to collect tax metrics: {str(e)}", 1)
            return {"error": str(e)}
    
    def _collect_bucket_metrics(self) -> Dict:
        """Collect stablecoin bucket metrics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        metrics = {
            'buckets': {},
            'total_balance': 0,
            'projected_interest': 0,
            'dai_utilization': 0  # How actively DAI is being used
        }
        
        try:
            # Get bucket balances
            c.execute("""
                SELECT bucket_type, balance, interest_rate
                FROM stablecoin_buckets
            """)
            
            total_balance = 0
            total_interest = 0
            
            for row in c.fetchall():
                bucket_type, balance, interest_rate = row
                total_balance += balance
                
                # Calculate 30-day interest
                daily_rate = interest_rate / 365.0
                interest_30d = balance * daily_rate * 30
                total_interest += interest_30d
                
                metrics['buckets'][bucket_type] = {
                    'balance': balance,
                    'interest_rate': interest_rate,
                    'interest_30d': interest_30d
                }
            
            metrics['total_balance'] = total_balance
            metrics['projected_interest'] = total_interest
            
            # Calculate DAI utilization
            # Number of injections from DAI bucket in last 30 days
            c.execute("""
                SELECT COUNT(*) FROM monitor_health_log
                WHERE component = 'DAI_INJECTION'
                AND timestamp > datetime('now', '-30 days')
            """)
            injection_count = c.fetchone()[0] or 0
            
            # Simple metric: 2+ injections per month = 100% utilization
            metrics['dai_utilization'] = min(1.0, injection_count / 2.0)
            
            conn.close()
            return metrics
        except Exception as e:
            conn.close()
            self._log_health_issue("bucket_metrics_collection", "error", 
                                  f"Failed to collect bucket metrics: {str(e)}", 1)
            return {"error": str(e)}
    
    def _collect_diversification_metrics(self) -> Dict:
        """Collect portfolio diversification metrics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        metrics = {
            'distinct_coins': 0,
            'wallet_coin_counts': {},
            'concentration': 0,  # % of portfolio in largest holding
            'concentration_by_wallet': {}
        }
        
        try:
            # These queries are placeholders - actual implementation would
            # depend on the database schema and how holdings are stored
            
            # Count distinct coins traded in last 30 days
            c.execute("""
                SELECT COUNT(DISTINCT symbol)
                FROM trade_history
                WHERE date > date('now', '-30 days')
            """)
            metrics['distinct_coins'] = c.fetchone()[0] or 0
            
            # Count distinct coins by wallet (would need to join with actual wallet tables)
            c.execute("""
                SELECT wallet, COUNT(DISTINCT symbol)
                FROM trade_history
                WHERE date > date('now', '-30 days')
                GROUP BY wallet
            """)
            
            for row in c.fetchall():
                wallet, count = row
                metrics['wallet_coin_counts'][wallet] = count
            
            conn.close()
            return metrics
        except Exception as e:
            conn.close()
            self._log_health_issue("diversification_metrics_collection", "error", 
                                  f"Failed to collect diversification metrics: {str(e)}", 1)
            return {"error": str(e)}
    
    def _save_metrics(self, metrics: Dict):
        """Save collected metrics to database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        metrics_json = json.dumps(metrics)
        
        c.execute("""
            INSERT INTO monitor_metrics (metrics_json)
            VALUES (?)
        """, (metrics_json,))
        
        conn.commit()
        conn.close()
    
    def _log_health_issue(self, component: str, status: str, message: str, alert_level: int = 0):
        """Log a health issue to the database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO monitor_health_log (component, status, message, alert_level)
            VALUES (?, ?, ?, ?)
        """, (component, status, message, alert_level))
        
        conn.commit()
        conn.close()
    
    def analyze_metrics(self) -> List[Dict]:
        """
        Analyze collected metrics and generate recommendations.
        
        Returns:
            List of recommendations
        """
        self.recommendations = []
        
        # Analyze trading performance
        self._analyze_trading_performance()
        
        # Analyze capital utilization
        self._analyze_capital_utilization()
        
        # Analyze tax efficiency
        self._analyze_tax_efficiency()
        
        # Analyze diversification
        self._analyze_diversification()
        
        # Save recommendations to database
        self._save_recommendations()
        
        return self.recommendations
    
    def _analyze_trading_performance(self):
        """Analyze trading performance metrics"""
        win_rate = self.metrics['trading_performance'].get('win_rate', 0)
        win_rate_min = self.config['thresholds']['win_rate_min']
        win_rate_target = self.config['thresholds']['win_rate_target']
        
        if win_rate < win_rate_min:
            self.recommendations.append({
                'type': 'trading_parameters',
                'priority': 2,  # High
                'description': f"Win rate ({win_rate:.1%}) below target ({win_rate_min:.1%})",
                'suggested_implementation': """
                # Increase confidence threshold
                self.learning_data['market_adaptations']['confidence_threshold'] = 0.55
                
                # Increase minimum gap threshold
                self.learning_data['market_adaptations']['min_gap'] = 60.0
                """
            })
        elif win_rate > win_rate_target + 0.1:
            self.recommendations.append({
                'type': 'trading_parameters',
                'priority': 1,  # Medium
                'description': f"Win rate ({win_rate:.1%}) well above target - could be more aggressive",
                'suggested_implementation': """
                # Decrease confidence threshold to take more trades
                self.learning_data['market_adaptations']['confidence_threshold'] = 0.45
                
                # Decrease minimum gap threshold
                self.learning_data['market_adaptations']['min_gap'] = 50.0
                """
            })
    
    def _analyze_capital_utilization(self):
        """Analyze capital utilization metrics"""
        cash_ratio = self.metrics['capital_utilization'].get('cash_ratio', 0)
        
        if cash_ratio > 0.3:
            self.recommendations.append({
                'type': 'capital_utilization',
                'priority': 1,  # Medium
                'description': f"High cash ratio ({cash_ratio:.1%}) - capital underutilized",
                'suggested_implementation': """
                # Increase position sizes
                position_size_multiplier = 1.2
                
                # Increase max open positions
                self.max_open_positions = min(15, self.max_open_positions + 2)
                """
            })
    
    def _analyze_tax_efficiency(self):
        """Analyze tax efficiency metrics"""
        long_term_ratio = self.metrics['tax_efficiency'].get('long_term_gains_ratio', 0)
        irs_coverage = self.metrics['tax_efficiency'].get('irs_bucket_coverage', 0)
        
        if long_term_ratio < 0.3:
            self.recommendations.append({
                'type': 'tax_efficiency',
                'priority': 1,  # Medium
                'description': f"Low long-term gains ratio ({long_term_ratio:.1%}) - tax inefficient",
                'suggested_implementation': """
                # Increase holding period preference
                self.learning_data['market_adaptations']['holding_period_preference'] = 1.2
                
                # Adjust take-profit thresholds for longer holds
                for wallet_name in ['Dynasty_Core', 'Builder_Ecosystem']:
                    self.wallet_strategies[wallet_name]['take_profit_threshold'] *= 1.15
                """
            })
        
        if irs_coverage < self.config['thresholds']['irs_bucket_ratio_min']:
            self.recommendations.append({
                'type': 'bucket_management',
                'priority': 2,  # High
                'description': f"IRS bucket coverage too low ({irs_coverage:.1%})",
                'suggested_implementation': """
                # Increase IRS allocation percentage
                self.bucket_manager.profit_allocation['IRS_USDT'] = 0.35  # Increase from 0.30
                self.bucket_manager.profit_allocation['SNW_LLC_USDC'] = 0.45  # Decrease from 0.50
                """
            })
        elif irs_coverage > self.config['thresholds']['irs_bucket_ratio_max']:
            self.recommendations.append({
                'type': 'bucket_management',
                'priority': 1,  # Medium
                'description': f"IRS bucket coverage too high ({irs_coverage:.1%})",
                'suggested_implementation': """
                # Decrease IRS allocation percentage
                self.bucket_manager.profit_allocation['IRS_USDT'] = 0.25  # Decrease from 0.30
                self.bucket_manager.profit_allocation['SNW_LLC_USDC'] = 0.55  # Increase from 0.50
                """
            })
    
    def _analyze_diversification(self):
        """Analyze diversification metrics"""
        distinct_coins = self.metrics['diversification'].get('distinct_coins', 0)
        diversification_min = self.config['thresholds']['diversification_min']
        
        if distinct_coins < diversification_min:
            self.recommendations.append({
                'type': 'diversification',
                'priority': 1,  # Medium
                'description': f"Low diversification ({distinct_coins} coins, target: {diversification_min})",
                'suggested_implementation': """
                # Increase coin rotation factor
                for wallet_name in self.wallet_coin_rotation:
                    self.wallet_coin_rotation[wallet_name] += 5
                
                # Run coin scanner with higher limit
                from departments.Finance.coin_scanner import CoinScanner
                scanner = CoinScanner()
                scanner.scan_and_evaluate_coins(limit=75)  # Increase from default 50
                """
            })
    
    def _save_recommendations(self):
        """Save recommendations to database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        for rec in self.recommendations:
            c.execute("""
                INSERT INTO monitor_recommendations 
                (recommendation_type, priority, description, suggested_implementation)
                VALUES (?, ?, ?, ?)
            """, (rec['type'], rec['priority'], rec['description'], rec['suggested_implementation']))
        
        conn.commit()
        conn.close()
    
    def generate_report(self) -> Dict:
        """
        Generate a comprehensive monitoring report.
        
        Returns:
            Dict with report data
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'system_health': 'healthy',
                'performance': 'on_target',
                'recommendations': len(self.recommendations)
            },
            'metrics': self.metrics,
            'recommendations': self.recommendations,
            'historical': {
                'win_rate_trend': [],
                'capital_utilization_trend': [],
                'tax_efficiency_trend': []
            }
        }
        
        # Get historical metrics for trends
        c.execute("""
            SELECT metrics_json FROM monitor_metrics
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        
        historical_metrics = []
        for row in c.fetchall():
            try:
                metrics = json.loads(row[0])
                historical_metrics.append(metrics)
            except:
                pass
        
        # Calculate trends
        if historical_metrics:
            report['historical']['win_rate_trend'] = [
                m['trading_performance'].get('win_rate', 0) for m in historical_metrics
            ]
            
            report['historical']['capital_utilization_trend'] = [
                1.0 - m['capital_utilization'].get('cash_ratio', 0) for m in historical_metrics
            ]
            
            report['historical']['tax_efficiency_trend'] = [
                m['tax_efficiency'].get('long_term_gains_ratio', 0) for m in historical_metrics
            ]
        
        conn.close()
        return report


# Decision Bridge - connects Monitor Agent to code modification
class DecisionBridge:
    """
    Bridge between Monitor Agent and code modifications.
    Routes recommendations to appropriate handlers.
    """
    
    def __init__(self, monitor_agent: MonitorAgent, output_dir: str = 'recommendations'):
        """
        Initialize the decision bridge.
        
        Args:
            monitor_agent: Monitor Agent instance
            output_dir: Directory to output recommendations
        """
        self.monitor_agent = monitor_agent
        self.output_dir = output_dir
        
        # Create output directory if not exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Map recommendation types to handlers
        self.handlers = {
            'trading_parameters': self._handle_trading_parameters,
            'capital_utilization': self._handle_capital_utilization,
            'tax_efficiency': self._handle_tax_efficiency,
            'bucket_management': self._handle_bucket_management,
            'diversification': self._handle_diversification
        }
    
    def process_recommendations(self) -> List[str]:
        """
        Process recommendations from monitor agent.
        
        Returns:
            List of generated file paths with recommendations
        """
        recommendations = self.monitor_agent.analyze_metrics()
        generated_files = []
        
        for rec in recommendations:
            rec_type = rec.get('type')
            if rec_type in self.handlers:
                file_path = self.handlers[rec_type](rec)
                if file_path:
                    generated_files.append(file_path)
        
        self._generate_summary_file(recommendations, generated_files)
        return generated_files
    
    def _handle_trading_parameters(self, recommendation: Dict) -> Optional[str]:
        """Handle trading parameters recommendation"""
        return self._generate_recommendation_file(
            'trading_parameters', 
            recommendation,
            'advanced_backtest.py'
        )
    
    def _handle_capital_utilization(self, recommendation: Dict) -> Optional[str]:
        """Handle capital utilization recommendation"""
        return self._generate_recommendation_file(
            'capital_utilization', 
            recommendation,
            'advanced_backtest.py'
        )
    
    def _handle_tax_efficiency(self, recommendation: Dict) -> Optional[str]:
        """Handle tax efficiency recommendation"""
        return self._generate_recommendation_file(
            'tax_efficiency', 
            recommendation,
            'agents/irs_calculator.py'
        )
    
    def _handle_bucket_management(self, recommendation: Dict) -> Optional[str]:
        """Handle bucket management recommendation"""
        return self._generate_recommendation_file(
            'bucket_management', 
            recommendation,
            'agents/bucket_manager.py'
        )
    
    def _handle_diversification(self, recommendation: Dict) -> Optional[str]:
        """Handle diversification recommendation"""
        return self._generate_recommendation_file(
            'diversification', 
            recommendation,
            'advanced_backtest.py'
        )
    
    def _generate_recommendation_file(self, rec_type: str, recommendation: Dict, target_file: str) -> Optional[str]:
        """Generate recommendation file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        priority_str = 'high' if recommendation['priority'] == 2 else 'medium' if recommendation['priority'] == 1 else 'low'
        
        file_name = f"{rec_type}_{priority_str}_{timestamp}.md"
        file_path = os.path.join(self.output_dir, file_name)
        
        with open(file_path, 'w') as f:
            f.write(f"# {rec_type.replace('_', ' ').title()} Recommendation\n\n")
            f.write(f"**Priority:** {priority_str}\n")
            f.write(f"**Target File:** {target_file}\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write(f"## Description\n\n{recommendation['description']}\n\n")
            f.write("## Implementation\n\n```python\n")
            f.write(recommendation['suggested_implementation'])
            f.write("\n```\n")
        
        return file_path
    
    def _generate_summary_file(self, recommendations: List[Dict], generated_files: List[str]) -> str:
        """Generate summary file with all recommendations"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f"fulcrum_recommendations_{timestamp}.md"
        file_path = os.path.join(self.output_dir, file_name)
        
        with open(file_path, 'w') as f:
            f.write(f"# Fulcrum Optimization Recommendations\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n")
            f.write(f"**Total Recommendations:** {len(recommendations)}\n\n")
            
            f.write("## Summary\n\n")
            f.write("| Type | Priority | Description |\n")
            f.write("|------|----------|-------------|\n")
            
            for rec in recommendations:
                priority_str = 'High' if rec['priority'] == 2 else 'Medium' if rec['priority'] == 1 else 'Low'
                f.write(f"| {rec['type'].replace('_', ' ').title()} | {priority_str} | {rec['description']} |\n")
            
            f.write("\n## Generated Files\n\n")
            for file_path in generated_files:
                f.write(f"- [{os.path.basename(file_path)}]({file_path})\n")
        
        return file_path


# Example usage
if __name__ == "__main__":
    print("Initializing Fulcrum Monitor Agent...")
    monitor = MonitorAgent()
    
    print("Collecting metrics...")
    metrics = monitor.collect_metrics()
    
    print("Analyzing metrics...")
    recommendations = monitor.analyze_metrics()
    
    print(f"Generated {len(recommendations)} recommendations")
    
    print("Initializing Decision Bridge...")
    bridge = DecisionBridge(monitor)
    
    print("Processing recommendations...")
    generated_files = bridge.process_recommendations()
    
    print(f"Generated {len(generated_files)} recommendation files")
    for file_path in generated_files:
        print(f"- {os.path.basename(file_path)}")