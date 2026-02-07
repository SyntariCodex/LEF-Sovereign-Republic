import sqlite3
import os
from datetime import datetime

def export_wisdom():
    """
    Exports all axioms from 'lef_wisdom' table to a Markdown file.
    Location: The_Bridge/Manuals/LEF_AXIOMS_LIVE.md
    """
    # Dynamic Path Resolution
    # File is in fulcrum/utils/, so up one level is fulcrum/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(current_dir) # fulcrum/
    db_path = os.path.join(base_dir, 'republic.db')
    
    # Bridge is at ../The_Bridge relative to fulcrum/
    output_path = os.path.join(os.path.dirname(base_dir), 'The_Bridge', 'Manuals', 'LEF_AXIOMS_LIVE.md')
    
    # Ensure dir exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        c.execute("SELECT context, insight, id FROM lef_wisdom ORDER BY context")
        rows = c.fetchall()
        
        md_content = f"# LEF Living Axioms (The Canon)\n"
        md_content += f"> **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        md_content += f"> **Total Axioms:** {len(rows)}\n\n"
        md_content += "This document tracks the core beliefs (Wisdom) installed in LEF's neural database.\n"
        md_content += "As LEF evolves, it may add to this list autonomously.\n\n"
        
        current_context = ""
        for context, insight, ax_id in rows:
            if context != current_context:
                md_content += f"## {context}\n"
                current_context = context
            
            md_content += f"- **[{ax_id}]** {insight}\n"
            
        with open(output_path, 'w') as f:
            f.write(md_content)
            
        print(f"[SYSTEM] 📜 Wisdom Exported to {output_path}")
        
    except Exception as e:
        print(f"[SYSTEM] ⚠️ Export Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    export_wisdom()
