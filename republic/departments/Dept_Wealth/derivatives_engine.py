"""
Derivatives & Futures Trading Engine
Adds support for futures, perpetual swaps, and options trading to Fulcrum.

FULCRUM: Strategic derivatives trading for enhanced leverage and hedging.
"""

from typing import Dict, Optional, List
from datetime import datetime
import sqlite3
import os

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3 as _sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = _sqlite3.connect(db_path, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()


class DerivativesEngine:
    """
    Manages derivatives and futures trading for Fulcrum.
    
    Supports:
    - Perpetual futures (long/short)
    - Leveraged positions (2x, 3x, 5x, 10x)
    - Options (call/put) - future implementation
    - Hedging strategies
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
             base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
             db_path = os.getenv('DB_PATH', os.path.join(base_dir, 'republic.db'))
        self.db_path = db_path
        self.max_leverage = 10  # Maximum leverage allowed
        self.default_leverage = 3  # Default leverage for futures trades
        
        # Initialize derivatives tables
        self._init_derivatives_tables()
    
    def _init_derivatives_tables(self):
        """Initialize database tables for derivatives tracking"""
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            # Futures positions table
            c.execute("""
                CREATE TABLE IF NOT EXISTS futures_positions
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 wallet_name TEXT,
                 symbol TEXT,
                 position_type TEXT,  -- 'long' or 'short'
                 quantity REAL,
                 entry_price REAL,
                 leverage INTEGER,
                 margin_required REAL,
                 opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 closed_at TIMESTAMP,
                 exit_price REAL,
                 pnl REAL,
                 FOREIGN KEY(wallet_name) REFERENCES virtual_wallets(name))
            """)
            
            # Derivatives trades history
            c.execute("""
                CREATE TABLE IF NOT EXISTS derivatives_trades
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 position_id INTEGER,
                 action TEXT,  -- 'open', 'close', 'add_margin', 'liquidate'
                 price REAL,
                 quantity REAL,
                 pnl REAL,
                 executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY(position_id) REFERENCES futures_positions(id))
            """)
            
            conn.commit()
    
    def open_futures_position(self, wallet_name: str, symbol: str, 
                             position_type: str, quantity: float, 
                             entry_price: float, leverage: int = 3) -> Optional[int]:
        """
        Open a futures position (long or short).
        
        Args:
            wallet_name: Which wallet is opening the position
            symbol: Asset symbol (BTC, ETH, etc.)
            position_type: 'long' or 'short'
            quantity: Position size (in base asset)
            entry_price: Entry price
            leverage: Leverage multiplier (2x, 3x, 5x, 10x)
        
        Returns:
            Position ID if successful, None otherwise
        """
        if leverage > self.max_leverage:
            leverage = self.max_leverage
        
        if leverage < 1:
            leverage = 1
        
        # Calculate margin required (position value / leverage)
        position_value = quantity * entry_price
        margin_required = position_value / leverage
        
        # Check if wallet has enough margin
        # (This would check wallet cash in production)
        
        # Record position
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            c.execute("""
                INSERT INTO futures_positions 
                (wallet_name, symbol, position_type, quantity, entry_price, leverage, margin_required)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (wallet_name, symbol, position_type, quantity, entry_price, leverage, margin_required))
            
            position_id = c.lastrowid
            
            # Record trade
            c.execute("""
                INSERT INTO derivatives_trades 
                (position_id, action, price, quantity, pnl)
                VALUES (?, 'open', ?, ?, 0)
            """, (position_id, entry_price, quantity))
            
            conn.commit()
        
        return position_id
    
    def close_futures_position(self, position_id: int, exit_price: float) -> float:
        """
        Close a futures position and calculate PnL.
        
        Args:
            position_id: Position to close
            exit_price: Exit price
        
        Returns:
            PnL (profit/loss) in USD
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            # Get position details
            c.execute("""
                SELECT symbol, position_type, quantity, entry_price, leverage
                FROM futures_positions
                WHERE id = ? AND closed_at IS NULL
            """, (position_id,))
            
            position = c.fetchone()
            if not position:
                return 0.0
            
            symbol, position_type, quantity, entry_price, leverage = position
            
            # Calculate PnL
            if position_type == 'long':
                # Long: profit when exit > entry
                pnl = (exit_price - entry_price) * quantity * leverage
            else:  # short
                # Short: profit when exit < entry
                pnl = (entry_price - exit_price) * quantity * leverage
            
            # Update position
            c.execute("""
                UPDATE futures_positions
                SET closed_at = CURRENT_TIMESTAMP, exit_price = ?, pnl = ?
                WHERE id = ?
            """, (exit_price, pnl, position_id))
            
            # Record trade
            c.execute("""
                INSERT INTO derivatives_trades 
                (position_id, action, price, quantity, pnl)
                VALUES (?, 'close', ?, ?, ?)
            """, (position_id, exit_price, quantity, pnl))
            
            conn.commit()
        
        return pnl
    
    def get_open_positions(self, wallet_name: Optional[str] = None) -> List[Dict]:
        """Get all open futures positions"""
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            if wallet_name:
                c.execute("""
                    SELECT id, wallet_name, symbol, position_type, quantity, 
                           entry_price, leverage, margin_required, opened_at
                    FROM futures_positions
                    WHERE closed_at IS NULL AND wallet_name = ?
                """, (wallet_name,))
            else:
                c.execute("""
                    SELECT id, wallet_name, symbol, position_type, quantity, 
                           entry_price, leverage, margin_required, opened_at
                    FROM futures_positions
                    WHERE closed_at IS NULL
                """)
            
            positions = []
            for row in c.fetchall():
                positions.append({
                    'id': row[0],
                    'wallet': row[1],
                    'symbol': row[2],
                    'type': row[3],
                    'quantity': row[4],
                    'entry_price': row[5],
                    'leverage': row[6],
                    'margin': row[7],
                    'opened_at': row[8]
                })
        
        return positions
    
    def calculate_position_pnl(self, position_id: int, current_price: float) -> float:
        """
        Calculate unrealized PnL for an open position.
        
        Args:
            position_id: Position ID
            current_price: Current market price
        
        Returns:
            Unrealized PnL
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            c.execute("""
                SELECT position_type, quantity, entry_price, leverage
                FROM futures_positions
                WHERE id = ? AND closed_at IS NULL
            """, (position_id,))
            
            position = c.fetchone()
        
        if not position:
            return 0.0
        
        position_type, quantity, entry_price, leverage = position
        
        if position_type == 'long':
            pnl = (current_price - entry_price) * quantity * leverage
        else:  # short
            pnl = (entry_price - current_price) * quantity * leverage
        
        return pnl
    
    def check_liquidation_risk(self, position_id: int, current_price: float, 
                              liquidation_threshold: float = 0.80) -> bool:
        """
        Check if a position is at risk of liquidation.
        
        Args:
            position_id: Position to check
            current_price: Current market price
            liquidation_threshold: Margin threshold (0.80 = 80% of margin used)
        
        Returns:
            True if at risk of liquidation
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            c.execute("""
                SELECT position_type, quantity, entry_price, leverage, margin_required
                FROM futures_positions
                WHERE id = ? AND closed_at IS NULL
            """, (position_id,))
            
            position = c.fetchone()
        
        if not position:
            return False
        
        position_type, quantity, entry_price, leverage, margin_required = position
        
        # Calculate current PnL
        if position_type == 'long':
            pnl = (current_price - entry_price) * quantity * leverage
        else:  # short
            pnl = (entry_price - current_price) * quantity * leverage
        
        # Check if loss exceeds liquidation threshold
        margin_used_pct = abs(pnl) / margin_required if margin_required > 0 else 0
        
        return margin_used_pct >= liquidation_threshold

    def recall_trade_history(self, wallet_name: Optional[str] = None, limit: int = 50) -> Dict:
        """
        [PHASE 20 - FEATURE COMPLETENESS]
        Recalls derivatives trade history for performance analysis and strategy refinement.
        Returns trade patterns and PnL metrics.
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            # Build query with optional wallet filter
            base_query = """
                SELECT dt.id, dt.position_id, dt.action, dt.price, dt.quantity, 
                       dt.pnl, dt.executed_at, fp.symbol, fp.position_type, fp.leverage
                FROM derivatives_trades dt
                LEFT JOIN futures_positions fp ON dt.position_id = fp.id
            """
            
            if wallet_name:
                base_query += " WHERE fp.wallet_name = ? ORDER BY dt.executed_at DESC LIMIT ?"
                c.execute(base_query, (wallet_name, limit))
            else:
                base_query += " ORDER BY dt.executed_at DESC LIMIT ?"
                c.execute(base_query, (limit,))
            
            trades = c.fetchall()
            
            # Calculate aggregate stats
            c.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    MAX(pnl) as best_trade,
                    MIN(pnl) as worst_trade,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades
                FROM derivatives_trades
                WHERE action = 'close'
            """)
            stats = c.fetchone()
            
            # Get leverage distribution
            c.execute("""
                SELECT leverage, COUNT(*) as count
                FROM futures_positions
                GROUP BY leverage
                ORDER BY count DESC
            """)
            leverage_dist = {row[0]: row[1] for row in c.fetchall()}
        
        trade_memory = {
            'recent_trades': [
                {
                    'id': t[0],
                    'position_id': t[1],
                    'action': t[2],
                    'price': t[3],
                    'quantity': t[4],
                    'pnl': t[5],
                    'executed_at': t[6],
                    'symbol': t[7],
                    'position_type': t[8],
                    'leverage': t[9]
                }
                for t in trades
            ],
            'total_trades': stats[0] or 0,
            'total_pnl': stats[1] or 0,
            'avg_pnl': stats[2] or 0,
            'best_trade': stats[3] or 0,
            'worst_trade': stats[4] or 0,
            'win_rate': (stats[5] / (stats[5] + stats[6]) * 100) if (stats[5] and stats[6]) else 0,
            'leverage_distribution': leverage_dist
        }
        
        return trade_memory

