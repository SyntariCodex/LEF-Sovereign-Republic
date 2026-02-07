#!/usr/bin/env python3
"""
GLADIATOR DASHBOARD (The Arena)
Run via: python3 republic/tools/gladiator_dashboard.py
"""
import curses
import sqlite3
import time
import os
import sys

# Setup DB Path (Root/republic.db)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'republic.db')

def fetch_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Profile Stats
    c.execute("SELECT level, xp, next_level_xp FROM agent_rpg_stats WHERE name='AgentGladiator'")
    row = c.fetchone()
    level, xp, next_xp = row if row else (1, 0, 1000)
    
    # 2. Bankroll (Scout Fund)
    c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type='SCOUT_FUND_USDC'")
    row = c.fetchone()
    bankroll = row[0] if row else 10000.0 # Default if bucket missing
    
    # 3. Performance
    c.execute("SELECT count(*), sum(case when status='WON' then 1 else 0 end), sum(pnl) FROM gladiator_ledger WHERE status!='OPEN'")
    total, won, pnl = c.fetchone()
    if not total: total, won, pnl = (0, 0, 0.0)
    win_rate = (won / total * 100) if total > 0 else 0.0
    
    # 4. Open Bets
    c.execute("SELECT status, side, amount, market_title FROM gladiator_ledger ORDER BY id DESC LIMIT 15")
    ledger = c.fetchall()
    
    conn.close()
    return {
        "level": level, "xp": xp, "next_xp": next_xp,
        "bankroll": bankroll,
        "total_bets": total + len(ledger), # Approx
        "win_rate": win_rate,
        "pnl": pnl or 0.0,
        "ledger": ledger
    }

def draw_dashboard(stdscr):
    # Colors
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)   # Header
    curses.init_pair(2, curses.COLOR_GREEN, -1)  # Money/Win
    curses.init_pair(3, curses.COLOR_RED, -1)    # Loss
    curses.init_pair(4, curses.COLOR_YELLOW, -1) # Pending
    
    stdscr.nodelay(True)
    curses.curs_set(0)

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        
        data = fetch_data()
        
        # TITLE
        title = " GLADIATOR ARENA DASHBOARD - [PAPER TRADING] "
        stdscr.attron(curses.color_pair(1) | curses.A_REVERSE)
        stdscr.addstr(0, 0, title.center(w))
        stdscr.attroff(curses.color_pair(1) | curses.A_REVERSE)
        
        # PROFILE BOX
        box_y = 2
        stdscr.addstr(box_y, 2, "╔" + "═"*40 + "╗")
        stdscr.addstr(box_y+1, 2, f"║ PROFILE {' ' * 31}║")
        stdscr.addstr(box_y+2, 2, f"║ Level: {data['level']:<2}   XP: {data['xp']}/{data['next_xp']:<15}║")
        stdscr.addstr(box_y+3, 2, f"║ Bankroll: ${data['bankroll']:<24,.2f}║")
        stdscr.addstr(box_y+4, 2, "╚" + "═"*40 + "╝")
        
        # PERFORMANCE BOX
        pg_x = 45
        stdscr.addstr(box_y, pg_x, "╔" + "═"*40 + "╗")
        stdscr.addstr(box_y+1, pg_x, f"║ PERFORMANCE {' ' * 27}║")
        stdscr.addstr(box_y+2, pg_x, f"║ Total Bets: {data['total_bets']:<5} Win Rate: {data['win_rate']:.1f}%{' '*6}║")
        
        pnl_str = f"${data['pnl']:,.2f}"
        color = curses.color_pair(2) if data['pnl'] >= 0 else curses.color_pair(3)
        stdscr.addstr(box_y+3, pg_x, "║ PnL: ", curses.A_NORMAL)
        stdscr.addstr(pnl_str, color | curses.A_BOLD)
        stdscr.addstr(f"{' '*(34 - len(pnl_str))}║") # Padding hack
        stdscr.addstr(box_y+4, pg_x, "╚" + "═"*40 + "╝")
        
        # LEDGER
        ly = 8
        stdscr.addstr(ly, 2, "Active Ledger (Last 15):")
        stdscr.addstr(ly+1, 2, "-"* (w-4))
        stdscr.addstr(ly+2, 2, f"{'STATUS':<10} {'SIDE':<6} {'AMOUNT':<10} {'MARKET'}")
        
        curr_y = ly + 3
        for row in data['ledger']:
            if curr_y >= h - 1: break
            status, side, amount, title = row
            
            # Color Logic
            color = curses.color_pair(4) # Yellow default
            if status == 'WON': color = curses.color_pair(2)
            if status == 'LOST': color = curses.color_pair(3)
            if status == 'OPEN': color = curses.color_pair(4)
            
            line = f"{status:<10} {side:<6} ${amount:<9.1f} {title[:w-30]}"
            stdscr.addstr(curr_y, 2, line, color)
            curr_y += 1
            
        stdscr.refresh()
        
        # Input
        try:
            k = stdscr.getch()
            if k == ord('q'): break
        except curses.error: pass
        
        time.sleep(2)

if __name__ == "__main__":
    try:
        curses.wrapper(draw_dashboard)
    except KeyboardInterrupt:
        sys.exit(0)
