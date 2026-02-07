# Simple Setup Guide - For Non-Coders

**Hey Z!** This guide explains what's already built and what you need to do next, in plain English.

---

## What's Already Done ✅

I've built all the code files for you. Here's what exists:

### The Code Files (Already Created)
- ✅ **RDA Engine** - The "mind" that understands what you mean vs what you say
- ✅ **Teleonomy Scorer** - Scores crypto assets based on your philosophy
- ✅ **Database Setup** - Creates the database structure
- ✅ **Sentinel Agent** - Scans Twitter for market signals
- ✅ **Master Controller** - The "brain" that makes decisions
- ✅ **Coinbase Agent** - Executes trades (only when you approve)
- ✅ **SNW RFR System** - The system for funding youth programs

**All the code is written and ready to use.**

---

## What Claude Started vs What I Built

**Claude's Work:**
- Created an `IMPLEMENTATION_GUIDE.md` with code snippets and instructions
- The code snippets were **incomplete** (had placeholders like "# ... your code here ...")

**What I Built:**
- **Complete, working code** - No placeholders, everything is filled in
- All files are in the right folders
- Everything connects together properly

**Bottom Line:** You don't need to copy/paste code from Claude's guide. I've already built it all.

---

## What You Need To Do (Simple Steps)

### Step 1: Install Python (If You Don't Have It)

**What it is:** Python is the language the code runs in.

**How to check if you have it:**
1. Open Terminal (press `Cmd + Space`, type "Terminal", press Enter)
2. Type: `python3 --version`
3. If you see a version number (like "Python 3.9.5"), you're good!
4. If you see "command not found", you need to install it.

**How to install:**
- Go to python.org/downloads
- Download Python 3 for Mac
- Run the installer (just click through it)

---

### Step 2: Install the Code Libraries

**What it is:** These are "add-ons" that let the code talk to Coinbase, Twitter, etc.

**How to do it:**
1. Open Terminal
2. Type this command (copy and paste it):
   ```
   cd "/Users/zmoore-macbook/Desktop/LEF Ai/fulcrum"
   ```
3. Press Enter
4. Then type:
   ```
   pip3 install -r requirements.txt
   ```
5. Press Enter
6. Wait for it to finish (might take 5-10 minutes)

**What you'll see:** A bunch of text scrolling by. That's normal. When it stops and shows your cursor again, it's done.

---

### Step 3: Install Redis (The Message Bus)

**What it is:** Redis lets the different parts of the system talk to each other.

**How to do it:**
1. Open Terminal
2. Type:
   ```
   brew install redis
   ```
3. Press Enter
4. Wait for it to finish
5. Then type:
   ```
   brew services start redis
   ```
6. Press Enter

**Note:** If you see "command not found: brew", you need to install Homebrew first:
- Go to brew.sh
- Copy the command it shows you
- Paste it into Terminal and press Enter

---

### Step 4: Set Up Your API Keys

**What it is:** API keys are like passwords that let the code connect to Coinbase and Twitter.

**Where to get them:**

**Coinbase API Keys:**
1. Go to coinbase.com
2. Sign in
3. Go to Settings → API
4. Create a new API key
5. **IMPORTANT:** Make sure "Sandbox" mode is ON (this uses fake money for testing)

**Twitter/X Bearer Token:**
1. Go to developer.twitter.com
2. Sign in
3. Create a new app
4. Get your "Bearer Token"

**How to add them:**
1. Open the file: `fulcrum/config/config.json`
2. You'll see placeholders like `"YOUR_CB_API_KEY"`
3. Replace those with your actual keys:
   ```json
   {
     "coinbase": {
       "api_key": "paste-your-coinbase-key-here",
       "api_secret": "paste-your-coinbase-secret-here",
       "sandbox": true
     },
     "twitter": {
       "bearer_token": "paste-your-twitter-token-here"
     }
   }
   ```
4. Save the file

**⚠️ IMPORTANT:** Never share this file with anyone. It has your keys in it.

---

### Step 5: Create the Database

**What it is:** The database stores all the information (wallets, trades, etc.)

**How to do it:**
1. Open Terminal
2. Type:
   ```
   cd "/Users/zmoore-macbook/Desktop/LEF Ai/fulcrum"
   ```
3. Press Enter
4. Then type:
   ```
   python3 db/db_setup.py
   ```
5. Press Enter

**What you'll see:** "Database initialized. The Virtual Fleet is ready."

**What happened:** A file called `fulcrum.db` was created in your `fulcrum` folder.

---

### Step 6: Test It (Optional)

**Before running the full system, you can test individual parts:**

**Test the database:**
```
python3 db/db_setup.py
```
(Should say "Database initialized")

**Test the RDA engine:**
```
python3 agents/rda_engine.py
```
(Should show some test output)

---

### Step 7: Run the Full System

**What it does:** Starts all the agents working together.

**How to do it:**
1. Make sure Redis is running (from Step 3)
2. Open Terminal
3. Type:
   ```
   cd "/Users/zmoore-macbook/Desktop/LEF Ai/fulcrum"
   ```
4. Press Enter
5. Then type:
   ```
   python3 main.py
   ```
6. Press Enter

**What you'll see:**
- A bunch of messages saying agents are starting
- "FLEET ONLINE"
- The system running

**To stop it:** Press `Ctrl + C` (hold Control, press C)

---

## Troubleshooting (Common Problems)

### "Module not found" error
**Problem:** Python can't find a library
**Fix:** Run `pip3 install -r requirements.txt` again (Step 2)

### "Redis connection refused"
**Problem:** Redis isn't running
**Fix:** Run `brew services start redis` (Step 3)

### "API key invalid"
**Problem:** Your keys aren't set up right
**Fix:** Double-check Step 4 - make sure you copied the keys correctly

### "Database not found"
**Problem:** Database wasn't created
**Fix:** Run Step 5 again

---

## What Each Part Does (Simple Explanation)

**RDA Engine:** Understands what you really mean, not just what you say

**Teleonomy Scorer:** Scores crypto based on: Can it survive? Is it building? Does it have purpose? Can it run itself?

**Sentinel Agent:** Watches Twitter and on-chain data, finds gaps between what people say and what's really happening

**Master Controller:** Takes signals from Sentinel, decides what to do, puts trades in a queue for your approval

**Coinbase Agent:** Only executes trades you've approved (the "Human Gate")

**SNW RFR System:** Manages the youth program funding requests

---

## Questions?

If something doesn't work:
1. Check the error message
2. Look at the Troubleshooting section above
3. Make sure you did all the steps in order

**Remember:** The code is all built. You just need to:
1. Install the tools (Python, libraries, Redis)
2. Add your API keys
3. Create the database
4. Run it

That's it!

---

**The Resolver's Role:** Code is built. Waiting for you to set it up.  
**Your Role:** Follow the steps. If something breaks, tell me and I'll fix it.
