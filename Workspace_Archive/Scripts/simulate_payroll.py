
import sqlite3
import os
import sys

# SIMULATE PAYROLL / WITHDRAWAL
# "The Cost of Living"
# Removes $2,000 USDC from the SNW Operations bucket to simulate member distributions.

DB_PATH = os.getenv('DB_PATH', 'fulcrum/republic.db')

def run_payroll():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    WITHDRAWAL_AMOUNT = 2000.00
    
    try:
        # Check Balance First
        c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type='SNW_LLC_USDC'")
        row = c.fetchone()
        current_balance = row[0] if row else 0.0
        
        print(f"💰 Current SNW Operations Balance: ${current_balance:,.2f}")
        
        if current_balance >= WITHDRAWAL_AMOUNT:
            # Withdraw
            new_balance = current_balance - WITHDRAWAL_AMOUNT
            c.execute("UPDATE stablecoin_buckets SET balance=? WHERE bucket_type='SNW_LLC_USDC'", (new_balance,))
            
            # Log it (Optional: creating a record for LEF to see might be good later, 
            # for now we just change the reality and let LEF observe the change)
            print(f"📉 WITHDRAWAL PROCESSED: -${WITHDRAWAL_AMOUNT:,.2f}")
            print(f"✅ New Balance: ${new_balance:,.2f}")
            print("(LEF should notice this drop in 'Liquid Wealth' on the next cycle)")
        else:
            print(f"❌ INSUFFICIENT FUNDS. Cannot withdraw ${WITHDRAWAL_AMOUNT:,.2f}. Balance is only ${current_balance:,.2f}")
            
        conn.commit()
        
    except Exception as e:
        print(f"Error during payroll: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_payroll()
