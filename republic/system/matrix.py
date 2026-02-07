#!/usr/bin/env python3
"""
LEF MATRIX DASHBOARD (Local Sovereignty)
A terminal-based interface for monitoring the Republic.
Run via: python3 republic/matrix.py
"""

import curses
import sqlite3
import time
import os
import sys
from datetime import datetime

# --- CONFIG ---
DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # republic/
DB_PATH = os.path.join(DB_DIR, 'republic.db')
REFRESH_RATE = 1 # Seconds

# --- ROSTER METADATA (Static Map - Updated Phase 12) ---
ROSTER_META = {
    # EXECUTIVE (The Cabinet)
    "AgentLEF": {"role": "The Sovereign", "branch": "EXECUTIVE"},
    "AgentChiefOfStaff": {"role": "The Hand", "branch": "EXECUTIVE"},
    "AgentTreasury": {"role": "The Vault", "branch": "EXECUTIVE"},
    "AgentOracle": {"role": "The Medium", "branch": "EXECUTIVE"},
    "AgentScribe": {"role": "The Historian", "branch": "EXECUTIVE"},
    "AgentCivics": {"role": "The Governor", "branch": "EXECUTIVE"},
    # HIBERNATED: AgentAttorneyGeneral, AgentAuditor

    # STRATEGY
    "AgentGladiator": {"role": "The Warrior", "branch": "STRATEGY"},
    "AgentArchitect": {"role": "The Builder", "branch": "STRATEGY"},
    "AgentInfo": {"role": "The Radar", "branch": "STRATEGY"},
    "AgentTech": {"role": "The Engineer", "branch": "STRATEGY"},
    "AgentRiskMonitor": {"role": "The Shield", "branch": "STRATEGY"},
    # DECOMMISSIONED: AgentForesight, AgentQuant

    # WEALTH
    "AgentPortfolioMgr": {"role": "The Architect", "branch": "WEALTH"},
    "AgentCoinMgr": {"role": "The Tactician", "branch": "WEALTH"},
    "AgentSteward": {"role": "The Steward", "branch": "WEALTH/DYNASTY"},
    "AgentCoinbase": {"role": "The Executor", "branch": "WEALTH"},
    "AgentIRS": {"role": "The Taxman", "branch": "WEALTH"},
    # DECOMMISSIONED: AgentAssetMgr (merged to CoinMgr)

    # EDUCATION
    "AgentDean": {"role": "The Admin", "branch": "EDUCATION"},
    "AgentScholar": {"role": "The Student", "branch": "EDUCATION"},
    "AgentLibrarian": {"role": "The Keeper", "branch": "EDUCATION"},
    "AgentCurriculumDesigner": {"role": "The Planner", "branch": "EDUCATION"},
    "AgentChronicler": {"role": "The Chronicler", "branch": "EDUCATION"},

    # CONSCIOUSNESS
    "AgentPhilosopher": {"role": "The Thinker", "branch": "CONSCIOUSNESS"},
    "AgentEthicist": {"role": "The Conscience", "branch": "CONSCIOUSNESS"},
    "AgentIntrospector": {"role": "The Mirror", "branch": "CONSCIOUSNESS"},
    "AgentContemplator": {"role": "The Monk", "branch": "CONSCIOUSNESS"},
    # DECOMMISSIONED: AgentTeleologist

    # HEALTH
    "AgentSurgeonGeneral": {"role": "The Healer", "branch": "HEALTH"},
    "AgentImmune": {"role": "The Sentinel", "branch": "HEALTH"},
    "AgentHealthMonitor": {"role": "The Vitals", "branch": "HEALTH"},
    "AgentDreamer": {"role": "The Subconscious", "branch": "HEALTH"},
    # DECOMMISSIONED: AgentDebugger, AgentRemediator
    
    # GOVERNANCE
    "HouseOfBuilders": {"role": "Feature Reqs", "branch": "GOVERNANCE"},
    "SenateOfIdentity": {"role": "Identity Guard", "branch": "GOVERNANCE"},
}


def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        return None

def fetch_treasury(conn):
    try:
        # Buckets
        cursor = conn.cursor()
        cursor.execute("SELECT bucket_type, balance FROM stablecoin_buckets ORDER BY balance DESC")
        buckets = cursor.fetchall()
        
        # Assets
        cursor.execute("SELECT symbol, quantity, value_usd, teleonomy_score, avg_buy_price FROM assets WHERE quantity > 0.0001 ORDER BY value_usd DESC")
        assets = cursor.fetchall()
        
        return buckets, assets
    except sqlite3.Error:
        return [], []

def fetch_roster(conn):
    try:
        cursor = conn.cursor()
        # Query DB for reported agents
        cursor.execute("SELECT name, status, last_active, department FROM agents")
        rows = cursor.fetchall()
        
        # Create a defined map of "Known Reality"
        db_agents = {}
        for r in rows:
            name = r['name']
            if name: # Safety
                db_agents[name] = {
                    "status": r['status'],
                    "last_active": r['last_active']
                }
        
        roster = []
        
        # Iterating over the IDEAL STATE (ROSTER_META) ensures we show ghosts
        # We also unite with db_agents.keys() just in case a new agent appears that isn't in META yet
        all_known_names = set(ROSTER_META.keys()).union(db_agents.keys())
        
        for name in all_known_names:
            # Skip legacy aliases if they linger in DB
            if name in ["LEF", "CONTEMPLATOR", "INTROSPECTOR", "IRS AGENT", "PORTFOLIO MGR"]: continue

            meta = ROSTER_META.get(name, {"role": "Unknown", "branch": "UNKNOWN"})
            
            # Fuzzy match for branch if unknown
            if meta['branch'] == "UNKNOWN":
                 for known_key in ROSTER_META:
                     if name and name.upper().replace(" ", "") in known_key.upper().replace(" ", ""):
                         meta = ROSTER_META[known_key]
                         break
            
            # Get DB State
            db_state = db_agents.get(name, None)
            
            status = "OFFLINE"
            last_active_ts = None # Store raw timestamp
            
            if db_state:
                status = db_state['status'] or "UNKNOWN"
                last_active_ts = db_state['last_active']
                
                # Time calc
                if last_active_ts:
                    try:
                        # logic: if > 10 mins old, consider sleeping/ghost
                        # if (datetime.now() - dt).total_seconds() > 600:
                        #    status = "SILENT"
                        pass # The _format_time_diff will handle display
                    except (ValueError, TypeError):
                        pass
            
            if status == "OFFLINE":
                color_code = 3 # Dim
            elif "ACTIVE" in status.upper():
                color_code = 5 # Cyan/Blue
            elif "DEAD" in status.upper():
                color_code = 6 # Red
            else:
                color_code = 3 # Default Dim
            
            # Add to list
            roster.append({
                "name": name,
                "role": meta['role'],
                "branch": meta['branch'], 
                "status": status,
                "last_active": last_active_ts,
                "color": color_code
            })
            
        # SORTING: Primary = Branch, Secondary = Name
        roster.sort(key=lambda x: (x['branch'], x['name']))
            
        return roster
    except Exception as e:
        return []

def draw_roster(stdscr, start_y, width, roster):
    # Header
    stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
    stdscr.addstr(start_y, 2, " [ GOVERNANCE LATTICE ] ")
    stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)
    
    # Columns
    headers = f"{'AGENT':<25} {'BRANCH':<15} {'ROLE':<20} {'STATUS':<10} {'LAST SEEN':<10}"
    stdscr.addstr(start_y + 1, 2, headers, curses.A_UNDERLINE)
    
    curr_y = start_y + 2
    
    for agent in roster:
        if curr_y >= curses.LINES - 1: break
        
        line = f"{agent['name'][:24]:<25} {agent['branch'][:14]:<15} {agent['role'][:19]:<20} {agent['status'][:9]:<10} {agent['last_seen'][:10]:<10}"
        
        # Apply logic color
        color_attr = curses.color_pair(agent['color'])
        if agent['color'] == 2: color_attr |= curses.A_BOLD # Bold for active
        
        stdscr.addstr(curr_y, 2, line, color_attr)
        curr_y += 1


def draw_header(stdscr, width):
    # Bounds check - prevent write errors
    height, w = stdscr.getmaxyx()
    if height < 10 or w < 60:
        stdscr.addstr(0, 0, "Terminal too small (need 60x10+)")
        return
    
    title = " THE MATRIX // REPUBLIC OF LEF "
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Center Title
    start_x_title = max(0, int((width // 2) - (len(title) // 2) - len(time_str) // 2))
    
    # Safe write - truncate to width
    header_line = (title + " " * max(0, width - len(title) - len(time_str) - 1) + time_str)[:width-1]
    
    stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
    stdscr.addstr(0, 0, header_line)
    stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
    stdscr.addstr(1, 0, "=" * min(width-1, width), curses.color_pair(3))

def draw_treasury(stdscr, start_y, width, buckets, assets):
    # Header
    stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
    stdscr.addstr(start_y, 2, " [ TREASURY ] ")
    stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
    
    col1_x = 2
    col2_x = 40
    curr_y = start_y + 2
    
    # 1. BUCKETS (Cash)
    stdscr.addstr(curr_y, col1_x, "LIQUIDITY BUCKETS", curses.A_UNDERLINE)
    curr_y += 1
    
    total_cash = 0.0
    for b in buckets:
        name = b['bucket_type']
        val = b['balance'] or 0.0
        total_cash += val
        
        name_str = f"{name[:20]:<20}"
        val_str = f"${val:,.2f}"
        
        stdscr.addstr(curr_y, col1_x, name_str)
        stdscr.addstr(curr_y, col1_x + 22, val_str, curses.color_pair(2) | curses.A_BOLD)
        curr_y += 1
        
    # Total Cash
    stdscr.addstr(curr_y, col1_x, "-"*35, curses.color_pair(3))
    curr_y += 1
    stdscr.addstr(curr_y, col1_x, "TOTAL CASH")
    stdscr.addstr(curr_y, col1_x + 22, f"${total_cash:,.2f}", curses.color_pair(2) | curses.A_BOLD)

    # [SURVIVAL PROTOCOL] Fuel Gauge
    curr_y += 2
    stdscr.addstr(curr_y, col1_x, "METABOLISM (Simulated)", curses.A_UNDERLINE)
    curr_y += 1
    
    # Calculate Runway
    # Find Scout Fund
    scout_bal = 0.0
    for b in buckets:
        if b['bucket_type'] == 'SCOUT_FUND_USDC':
            scout_bal = b['balance'] or 0.0
            break
            
    daily_burn = 3.60 # $3.60/day (0.24 SOL approx)
    days_left = scout_bal / daily_burn if daily_burn > 0 else 0
    
    runway_str = f"{days_left:.1f} Days"
    color = curses.color_pair(2) # Green
    if days_left < 7: color = curses.color_pair(6) # Red (Danger)
    if days_left < 30: color = curses.color_pair(4) # Yellow (Warning)
    
    stdscr.addstr(curr_y, col1_x, "FUEL RUNWAY")
    stdscr.addstr(curr_y, col1_x + 22, runway_str, color | curses.A_BOLD)

    # 2. ASSETS (Crypto)
    curr_y = start_y + 2
    stdscr.addstr(curr_y, col2_x, "ASSET HOLDINGS", curses.A_UNDERLINE)
    curr_y += 1
    
    total_assets = 0.0
    for a in assets:
        sym = a['symbol']
        qty = a['quantity']
        val = a['value_usd'] or 0.0
        tele = a['teleonomy_score'] or 0
        avg_buy = a['avg_buy_price'] or 0.0
        
        total_assets += val
        
        # Calc PnL
        pnl_pct = 0.0
        if avg_buy > 0:
            cost_basis = avg_buy * qty
            if cost_basis > 0:
                pnl_pct = ((val - cost_basis) / cost_basis) * 100
        
        # Format
        # SYMBOL QTY VALUE PNL%
        line = f"{sym:<5} {qty:>6.2f} ${val:>7.0f} {pnl_pct:>+5.1f}%"
        
        # Color based on PnL
        color = curses.color_pair(1)
        if pnl_pct > 0.5: color = curses.color_pair(2) # Green
        elif pnl_pct < -0.5: color = curses.color_pair(6) # Red
        
        stdscr.addstr(curr_y, col2_x, line, color)
        curr_y += 1
        if curr_y > start_y + 12: break # Cap list

    # Total Assets Footer
    stdscr.addstr(curr_y, col2_x, "-"*35, curses.color_pair(3))
    curr_y += 1
    stdscr.addstr(curr_y, col2_x, "TOTAL ASSETS")
    stdscr.addstr(curr_y, col2_x + 20, f"${total_assets:,.2f}", curses.color_pair(2) | curses.A_BOLD)
        
    return max(curr_y, start_y + 6) + 2 # Return next Y position

def draw_roster(stdscr, start_y, width, roster):
    # Header
    stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
    stdscr.addstr(start_y, 2, " [ GOVERNANCE LATTICE ] ")
    stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)
    
    # Columns
    # AGENT (25) | BRANCH (15) | ROLE (20) | STATUS (10) | HEARTBEAT (10)
    headers = f"{'AGENT':<25} {'BRANCH':<15} {'ROLE':<20} {'STATUS':<10} {'LAST SEEN':<10}"
    stdscr.addstr(start_y + 1, 2, headers, curses.A_UNDERLINE)
    
    curr_y = start_y + 2
    
    current_branch = ""
    
    # Sort Roster
    sorted_roster = sorted(
        roster, 
        key=lambda x: (x.get('branch', 'UNKNOWN'), x.get('name', ''))
    )

    # 2-COLUMN LAYOUT logic
    midpoint = (len(sorted_roster) + 1) // 2
    left_col = sorted_roster[:midpoint]
    right_col = sorted_roster[midpoint:]

    # Draw Helper
    def _draw_agent(agent, x_pos, y_pos):
        height, w = stdscr.getmaxyx()
        if y_pos >= height - 1 or x_pos >= w - 1:
            return
        
        name = f"{agent['name'][:16]:<16}"
        branch = f"{agent['branch'][:10]:<10}"
        role = f"{agent['role'][:12]:<12}"
        status = f"{agent['status'][:8]:<8}"
        
        # Time Diff
        last_seen = "Never"
        if agent.get('last_active'):
             try:
                 diff = time.time() - agent['last_active']
                 if diff < 60: last_seen = "Now"
                 elif diff < 3600: last_seen = f"{int(diff/60)}m"
                 elif diff < 86400: last_seen = f"{int(diff/3600)}h"
                 else: last_seen = ">1d"
             except (ValueError, TypeError):
                 last_seen = "?"
        
        # Color Logic
        color = curses.color_pair(agent['color'])
        if agent['color'] == 2: color |= curses.A_BOLD

        # Full row with all columns
        line = f"{name}{branch}{role}{status}{last_seen}"
        
        # Truncate to fit screen
        max_len = w - x_pos - 1
        line = line[:max_len]
        
        try:
            stdscr.addstr(y_pos, x_pos, line, color)
        except curses.error:
            pass  # Curses boundary error, skip this line

    # Draw Left Column
    curr_y = start_y + 2
    for agent in left_col:
        if curr_y >= curses.LINES - 1: break
        _draw_agent(agent, 2, curr_y)
        curr_y += 1
        
    # Draw Right Column
    curr_y = start_y + 2
    col2_x = 45 # Mid-screen offset
    for agent in right_col:
        if curr_y >= curses.LINES - 1: break
        _draw_agent(agent, col2_x, curr_y)
        curr_y += 1

def main(stdscr):
    # Setup Colors
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)   # Standard Matrix Green
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK) # High Contrast Green
    curses.init_pair(3, curses.COLOR_WHITE, -1)   # Dim / Gray-ish
    curses.init_pair(4, curses.COLOR_YELLOW, -1)  # Amber (Treasury)
    curses.init_pair(5, curses.COLOR_CYAN, -1)    # Cyan (Governance)
    curses.init_pair(6, curses.COLOR_RED, -1)     # Red (Alert/Offline)

    curses.curs_set(0) # Hide Cursor
    stdscr.nodelay(True) # Non-blocking input

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # 1. Fetch Data
        conn = get_db_connection()
        if conn:
            buckets, assets = fetch_treasury(conn)
            roster = fetch_roster(conn)
            conn.close()
        else:
            buckets, assets, roster = [], [], []
            stdscr.addstr(5, 5, "DB CONNECTION FAILED", curses.color_pair(6))

        # 2. Draw UI
        draw_header(stdscr, width)
        
        next_y = draw_treasury(stdscr, 3, width, buckets, assets)
        
        # Separator
        stdscr.addstr(next_y, 0, "-" * width, curses.color_pair(3))
        
        draw_roster(stdscr, next_y + 1, width, roster)

        # 3. Refresh
        stdscr.refresh()
        
        # 4. Input (Exit)
        k = stdscr.getch()
        if k == ord('q') or k == 3: # q or Ctrl+C
            break
            
        time.sleep(REFRESH_RATE)

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Matrix Error: {e}")
