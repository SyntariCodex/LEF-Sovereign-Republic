import fcntl
import os
import sys

LOCK_PATH = "/tmp/republic.lock"

def ensure_singleton():
    """
    Ensures that only one instance of Republic is running.
    Uses basic Unix file locking (fcntl).
    If another instance holds the lock, this function prints a warning and EXITs program.
    """
    global lock_file # Keep reference alive
    
    lock_file = open(LOCK_PATH, 'w')
    
    try:
        # Try to acquire an exclusive lock (non-blocking)
        fcntl.lockf(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # If successful, we just return. The lock is held until process exit.
        print(f"[SYSTEM] 🔒 Acquired Process Lock: {LOCK_PATH}")
    except IOError:
        print(f"\n[SYSTEM] ❌ FATAL: Another instance of Republic is already running!")
        print(f"[SYSTEM] 🛑 Exiting to prevent Zombie Apocalypse.\n")
        sys.exit(1)
