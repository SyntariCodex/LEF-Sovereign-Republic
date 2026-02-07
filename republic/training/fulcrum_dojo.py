import time
import redis
import sys
import os
import random
import sqlite3

# "The Dojo" - Master Training Simulation
# This script controls the Weather (Sentiment) to test Fulcrum's reflexes.
# ENHANCED: Unpredictable, Infinite Chaos.

def run_simulation():
    print("🥋 WELCOME TO THE DOJO (CHAOS MODE).")
    msg = "Initializing Infinite Chaos Engine..."
    if os.environ.get('AM_I_IN_DOCKER'):
        msg += " (Docker Mode)"
    print(msg)
    
    try:
        redis_host = os.environ.get('REDIS_HOST', 'localhost')
        r = redis.Redis(host=redis_host, port=6379, db=0)
        r.ping()
    except Exception as e:
        print(f"❌ Redis Connection Failed: {e}")
        print("Please ensure redis-server is running.")
        return

    scenarios = [
        # --- CLASSIC SCENARIOS ---
        ("BULL", "🐂 BULL RUN INVOKED (Sentiment > 80)", 80),
        ("CRASH", "📉 FLASH CRASH TRIGGERED (Sentiment < 15)", 30),
        ("BEAR", "🐻 BEAR WINTER SETTING IN (Sentiment ~20)", 90),
        ("MANIC", "🤪 MANIC PHASE (Rapid Volatility)", 45),
        ("NORMAL", "🌿 ORGANIC CYCLES (Baseline)", 60),
        
        # --- S-TIER SCENARIOS (Advanced Patterns) ---
        ("ACCUMULATION", "🧱 ACCUMULATION ZONE (Boring, Low Volatility)", 120),
        ("DISTRIBUTION", "🏰 DISTRIBUTION TOP (Chop at Highs)", 90),
        ("CHOP", "🥩 MEAT GRINDER (Choppy, No Trend)", 60),
        ("ALT_SEASON", "🦄 ALT SEASON (BTC Stable, Alts Fly)", 60),
        ("SCAM_WICK", "🕯️ SCAM WICK (Instant 10% Drop & Recovers)", 10)
    ]
    
    print(f"⏱️  Simulation Duration: INFINITE")
    print("Ensure 'python3 main.py' is running in another terminal.")
    print("-" * 50)
    
    try:
        while True:
            # 1. Pick a random scenario
            mode, message, base_duration = random.choice(scenarios)
            
            # 2. Add randomness to duration (+/- 50%)
            duration_variance = random.uniform(0.5, 1.5)
            duration = int(base_duration * duration_variance)
            
            print(f"\n{message}")
            print(f"🎲 Random Duration: {duration} seconds")
            
            # 3. Inject into Redis
            if mode == "NORMAL":
                # Occasionally delete the key to let organic mock take over completely
                if random.random() > 0.5:
                    r.delete('mock:sentiment:mode')
                    print(f"Injecting: ORGANIC (No Override)")
                else:
                    r.set('mock:sentiment:mode', 'NORMAL')
                    print(f"Injecting: 'mock:sentiment:mode' = NORMAL")
            else:
                r.set('mock:sentiment:mode', mode)
                print(f"Injecting: 'mock:sentiment:mode' = {mode}")
                
            # 4. VOLATILITY INJECTION (The Price Noise)
            # Simulate specialized price action for new modes
            if mode == "SCAM_WICK":
                 # Instant Crash followed by Recovery
                 r.set('mock:price_override', 'CRASH_-10%')
                 time.sleep(2)
                 r.set('mock:price_override', 'RECOVER_FAST')
            elif mode == "CHOP":
                 # Rapid up/down
                 r.set('mock:volatility_multiplier', '3.0')
            else:
                 r.delete('mock:volatility_multiplier')
                 r.delete('mock:price_override')

            # 5. PAYROLL INJECTION (Accelerated)
            # Simulating "Bi-Weekly" deposit every few cycles
            if random.random() < 0.20:
                # Docker Internal Logic
                if os.environ.get('AM_I_IN_DOCKER'):
                     try:
                        # Use the shared volume path
                        db_path = os.environ.get('DB_PATH', '/app/database/republic.db')
                        conn = sqlite3.connect(db_path)
                        c = conn.cursor()
                        c.execute("UPDATE stablecoin_buckets SET balance = balance + 200 WHERE bucket_type='INJECTION_DAI'")
                        conn.commit()
                        conn.close()
                        print(f"\n💰 PAYDAY! Injected $200 DAI directly into Shared DB ({db_path}).")
                     except Exception as e:
                        print(f"Error injecting payroll (Internal): {e}")
                
                else:
                    # Host Logic (docker exec)
                    try:
                        import subprocess
                        # Try Docker Exec Injection (Host Mode)
                        cmd = [
                            "docker", "exec", "lef-core", "python3", "-c",
                            "import sqlite3; db='/app/republic/republic.db'; conn=sqlite3.connect(db); c=conn.cursor(); c.execute(\"UPDATE stablecoin_buckets SET balance = balance + 200 WHERE bucket_type='INJECTION_DAI'\"); conn.commit();"
                        ]
                        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        print(f"\n💰 PAYDAY! Injected $200 DAI via Docker Exec. (Simulated Income)")
                    except Exception as e:
                        # Fallback to local
                         print(f"Error injecting payroll (Host): {e}")

            # 5. Countdown
            for i in range(duration, 0, -1):
                sys.stdout.write(f"\r⏳ Sustaining {mode} for {i}s...   ")
                sys.stdout.flush()
                time.sleep(1)
            print("\n✅ Cycle Complete. Rolling dice...")
            
    except KeyboardInterrupt:
        print("\n\n🛑 Simulation Stopped by User.")
        # Cleanup
        r.delete('mock:sentiment:mode')
        print("✅ Restored Organic Market Conditions.")

if __name__ == "__main__":
    run_simulation()
