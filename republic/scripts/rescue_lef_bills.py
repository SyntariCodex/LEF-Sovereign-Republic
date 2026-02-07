import os
import json
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Desktop/LEF Ai
BRIDGE_DIR = os.path.join(BASE_DIR, 'The_Bridge')
REJECTED_DIR = os.path.join(BRIDGE_DIR, 'Proposals', 'Rejected')
PENDING_DIR = os.path.join(BRIDGE_DIR, 'Proposals', 'Pending')

def rescue_lef_bills():
    if not os.path.exists(REJECTED_DIR):
        print(f"Rejected dir not found: {REJECTED_DIR}")
        return

    # Ensure Pending exists
    os.makedirs(PENDING_DIR, exist_ok=True)
    
    files = [f for f in os.listdir(REJECTED_DIR) if f.startswith('BILL-LEF-') and f.endswith('.json')]
    print(f"Found {len(files)} rejected LEF bills.")
    
    count = 0
    for filename in files:
        old_path = os.path.join(REJECTED_DIR, filename)
        new_path = os.path.join(PENDING_DIR, filename)
        
        try:
            with open(old_path, 'r') as f:
                data = json.load(f)
            
            # FIX: Technical Spec Key
            if 'technical_spec' not in data:
                data['technical_spec'] = {} # Empty dict for now
                print(f"  - Added Empty Spec for {filename}")
                
            # Reset Status to Draft/Pending so it gets re-evaluated
            data['status'] = "DRAFT"
            if 'votes' in data:
                 if 'house' in data['votes']:
                      data['votes']['house']['status'] = 'PENDING'
                      data['votes']['house']['comments'] = []
            
            # Move to Pending
            with open(new_path, 'w') as f:
                json.dump(data, f, indent=4)
            
            os.remove(old_path)
            count += 1
            
        except Exception as e:
            print(f"Failed to rescue {filename}: {e}")

    print(f"✅ Rescued {count} LEF bills to {PENDING_DIR}")

if __name__ == "__main__":
    rescue_lef_bills()
