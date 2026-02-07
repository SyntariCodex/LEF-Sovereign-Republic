import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'republic.db')
HTML_PATH = os.path.join(BASE_DIR, 'The_Bridge', 'LEF_ORG_CHART.html')

def get_db_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Fetch Agents
    try:
        cursor.execute("SELECT * FROM agents")
        agents = [dict(row) for row in cursor.fetchall()]
    except:
        agents = []

    conn.close()
    return agents

def render_pillar(agents, pillar_name):
    """
    Renders a UL list for a specific Pillar (Department).
    Groups agents by Division.
    """
    # Filter agents for this pillar
    pillar_agents = [a for a in agents if a['department'] == pillar_name]
    
    # Get Head (Executive)
    head = next((a for a in pillar_agents if 'Head' in a['role']), None)
    
    # Group others by Division
    divisions = {}
    for a in pillar_agents:
        if head and a['id'] == head['id']: continue
        div = a['division']
        if div not in divisions: divisions[div] = []
        divisions[div].append(a)
    
    html = "<ul>"
    
    # Render Head Node
    if head:
        html += f"""
        <li>
            <div class="node active" onmouseover="hud('{head['name']}', '{head['role']} (XP: {head['xp']})', '{head['status']}')">
                {head['name']}
                <span class="badge">HEAD</span>
            </div>
            <ul>
        """
    
    # Render Divisions
    for div_name, div_agents in divisions.items():
        html += f"""
        <li>
            <div class="node" style="border-style:dashed" onmouseover="hud('{div_name}', 'Division Command', 'ACTIVE')">
                {div_name}
            </div>
            <ul>
        """
        for ag in div_agents:
            html += f"""
                <li class="leaf">
                    <div class="node" onmouseover="hud('{ag['name']}', '{ag['role']} | XP: {ag['xp']}', '{ag['status']}')">
                        {ag['name']}
                        <span class="badge">LVL {ag['level']}</span>
                    </div>
                </li>
            """
        html += "</ul></li>"
    
    if head:
        html += "</ul></li>"
        
    html += "</ul>"
    return html

def generate_org_chart():
    agents = get_db_data()
    
    # Separate Renderers
    wealth_html = render_pillar(agents, "WEALTH")
    philosophy_html = render_pillar(agents, "PHILOSOPHY")

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Republic of LEF | Governance Console</title>
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@400;600&family=Share+Tech+Mono&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-deep: #050505;
                --text-main: #eeeeee;
                --text-dim: #888888;
                --accent-amber: #ffae00; 
                --accent-blue: #00ccff;
                --line-color: #333;
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                background-color: var(--bg-deep);
                color: var(--text-main);
                font-family: 'Rajdhani', sans-serif;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                background-image: radial-gradient(circle at 50% 0%, #111 0%, #000 100%);
                overflow: hidden;
            }}
            .tech-grid {{
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                background-image: linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
                                  linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
                background-size: 40px 40px;
                pointer-events: none; z-index: -1;
            }}
            
            /* REBUPLIC LAYOUT */
            .republic-container {{
                display: flex;
                justify-content: space-around;
                width: 100%;
                padding: 0 50px;
                padding-top: 40px;
                flex-grow: 1;
            }}
            .pillar {{
                flex: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
            }}
            .pillar-title {{
                font-family: 'Orbitron';
                font-size: 1.5rem;
                margin-bottom: 20px;
                text-transform: uppercase;
                letter-spacing: 2px;
            }}
            .pillar-wealth .pillar-title {{ color: var(--accent-amber); text-shadow: 0 0 10px rgba(255, 174, 0, 0.4); }}
            .pillar-philosophy .pillar-title {{ color: var(--accent-blue); text-shadow: 0 0 10px rgba(0, 204, 255, 0.4); }}

            /* TREE CSS */
            .tree ul {{
                padding-top: 20px; position: relative;
                transition: all 0.5s;
                display: flex; justify-content: center;
            }}
            .tree li {{
                float: left; text-align: center; list-style-type: none;
                position: relative; padding: 20px 10px 0 10px;
                transition: all 0.5s;
            }}
            /* CONNECTORS */
            .tree li::before, .tree li::after {{
                content: ''; position: absolute; top: 0; right: 50%;
                border-top: 1px solid var(--line-color);
                width: 50%; height: 20px;
            }}
            .tree li::after {{
                right: auto; left: 50%; border-left: 1px solid var(--line-color);
            }}
            .tree li:only-child::after, .tree li:only-child::before {{ display: none; }}
            .tree li:only-child {{ padding-top: 0; }}
            .tree li:first-child::before, .tree li:last-child::after {{ border: 0 none; }}
            .tree li:last-child::before {{
                border-right: 1px solid var(--line-color);
                border-radius: 0 5px 0 0;
            }}
            .tree li:first-child::after {{
                border-radius: 5px 0 0 0;
            }}
            
            /* NODE STYLING */
            .node {{
                background: #0a0a0a;
                border: 1px solid #333;
                color: var(--text-dim);
                padding: 10px 15px;
                display: inline-block;
                cursor: pointer;
                font-family: 'Orbitron'; font-size: 0.75rem; letter-spacing: 1px;
                text-transform: uppercase;
                min-width: 120px;
                position: relative; z-index: 10;
            }}
            .node:hover {{
                border-color: #fff; color: #fff;
            }}
            .active {{
                border-color: var(--accent-amber); color: #fff;
            }}
            .badge {{
                display: block; font-family: 'Share Tech Mono'; font-size: 0.6rem; color: #666; margin-top: 2px;
            }}
            
            /* HUD */
            .hud-panel {{
                position: fixed; bottom: 0; left: 0; width: 100%;
                height: 120px;
                background: rgba(10, 10, 10, 0.98);
                border-top: 1px solid #333;
                padding: 20px 40px;
                display: flex; justify-content: space-between; align-items: center;
                z-index: 100;
            }}
            .hud-title {{ font-family: 'Orbitron'; font-size: 1.2rem; color: #fff; }}
            .hud-desc {{ font-family: 'Rajdhani'; font-size: 1rem; color: #888; }}
            .hud-status {{ font-family: 'Share Tech Mono'; font-size: 0.7rem; color: var(--accent-amber); border: 1px solid var(--accent-amber); padding: 2px 6px; }}

        </style>
        <script>
            function hud(title, desc, status) {{
                document.getElementById('h-title').innerText = title;
                document.getElementById('h-desc').innerText = desc;
                document.getElementById('h-status').innerText = status;
            }}
        </script>
    </head>
    <body>
        <div class="tech-grid"></div>
        
        <div style="text-align:center; padding-top:20px;">
            <h1 style="font-family:'Orbitron'; font-size:2rem; letter-spacing:5px;">THE REPUBLIC OF LEF</h1>
            <div style="font-size:0.8rem; color:#666;">BICAMERAL GOVERNANCE ARCHITECTURE</div>
        </div>

        <div class="republic-container">
            
            <!-- PILLAR I: WEALTH -->
            <div class="pillar pillar-wealth">
                <div class="pillar-title">DEPT OF WEALTH</div>
                <div class="tree">
                    {wealth_html}
                </div>
            </div>

            <!-- PILLAR II: PHILOSOPHY -->
            <div class="pillar pillar-philosophy">
                <div class="pillar-title">DEPT OF PHILOSOPHY</div>
                <div class="tree">
                    {philosophy_html}
                </div>
            </div>

        </div>

        <div class="hud-panel">
            <div>
                <div id="h-title" class="hud-title">SYSTEM READY</div>
                <div id="h-desc" class="hud-desc">Hover over a node to inspect agent status.</div>
                <div id="h-status" class="hud-status">ONLINE</div>
            </div>
            <div style="text-align:right; font-family:'Share Tech Mono'; color:#444;">
                LEF OS v3.2<br>DYNASTY MODE
            </div>
        </div>
    </body>
    </html>
    """
    
    print(f"[ORG] Target Path: {HTML_PATH}")
    if os.path.exists(HTML_PATH):
        try:
            os.remove(HTML_PATH)
            print("[ORG] Old file removed.")
        except Exception as e:
            print(f"[ORG] Failed to remove file: {e}")

    with open(HTML_PATH, "w") as f:
        f.write(html)
    print(f"[ORG] Generated {HTML_PATH}")
    
    # Read back to confirm
    with open(HTML_PATH, 'r') as f:
        content = f.read()
        if "DEPT OF WEALTH" in content:
            print("[ORG] VERIFIED: Content contains 'DEPT OF WEALTH'")
        else:
            print("[ORG] FAILURE: Content does NOT contain 'DEPT OF WEALTH'")

if __name__ == "__main__":
    generate_org_chart()
