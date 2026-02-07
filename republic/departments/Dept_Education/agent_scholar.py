import sqlite3
import os
import json
import time
import requests
import random
import logging
import re
import sys
from urllib.parse import urlparse, urljoin
from datetime import datetime
import pypdf
from bs4 import BeautifulSoup
# Load environment variables from .env
from dotenv import load_dotenv

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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Agent Scholar (The Analyst & Scout)
# Mission: Active Intelligence Gathering (News, Macro, Market Data).
# V2 Capabilities: Deep Crawling, Safety Filtering, HuggingFace Monitoring.
# V3 Upgrade: Absorbed 'CoinScanner' (Market Census) + Macro Eyes.

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.append(BASE_DIR) # Enable module imports from republic root
sys.path.append(ROOT_DIR) # Enable absolute imports from project root

# Intent Listener for Motor Cortex integration
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared.intent_listener import IntentListenerMixin

DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))

# TeleonomyScorer import removed (Legacy)


# Expanded Intelligence Net
# Sources loaded dynamically from config/sources.json
RSS_SOURCES = {}
MACRO_SOURCES = {}
FINANCIAL_SOURCES = {}


class AgentScholar(IntentListenerMixin):
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        self.cursor = self.conn.cursor()
        logging.info("[SCHOLAR] 🎓 The Scholar is Awake (V3: All-Seeing Eye).")
        
        # Motor Cortex Integration
        self.setup_intent_listener('agent_scholar')
        self.start_listening()
        
        # CoinGecko Config REMOVED (Zombie Code Cleanup)
        self.coin_cache = {}
        
        # Phase 8: Seed Knowledge Base
        self.seed_knowledge_base()
        self._init_census_table() # Prepare the Map
        self.last_census_time = 0 # Force initial census
        
        # Load Sources
        self.load_sources()
    
    def handle_intent(self, intent_data):
        """
        Process INVESTIGATE/RESEARCH/ANALYZE intents from Motor Cortex.
        """
        intent_type = intent_data.get('type', '')
        intent_content = intent_data.get('content', '')
        
        logging.info(f"[SCHOLAR] 🔍 Received intent: {intent_type} - {intent_content}")
        
        if intent_type in ('INVESTIGATE', 'RESEARCH', 'ANALYZE'):
            try:
                # Log to knowledge stream
                self.cursor.execute("""
                    INSERT INTO knowledge_stream (source, title, summary, timestamp)
                    VALUES ('MOTOR_CORTEX', ?, ?, datetime('now'))
                """, (f"Intent: {intent_type}", f"Investigating: {intent_content}"))
                self.conn.commit()
                
                # Trigger a focused research cycle
                # For now, log the intent. Future: use LLM to search and summarize.
                logging.info(f"[SCHOLAR] 📚 Logged research intent: {intent_content}")
                
                return {'status': 'success', 'result': f'Logged investigation: {intent_content}'}
            except Exception as e:
                return {'status': 'error', 'result': str(e)}
        else:
            return {'status': 'unhandled', 'result': f'Scholar does not handle {intent_type} intents'}
        
    def load_sources(self):
        """
        Loads external reading list from sources.json.
        """
        global RSS_SOURCES, MACRO_SOURCES, FINANCIAL_SOURCES
        try:
            # Path is republic/config/sources.json
            config_path = os.path.join(BASE_DIR, 'config', 'sources.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    RSS_SOURCES = data.get('rss_feeds', RSS_SOURCES)
                    MACRO_SOURCES = data.get('macro_sources', MACRO_SOURCES)
                    FINANCIAL_SOURCES = data.get('financial_wisdom', FINANCIAL_SOURCES)
                logging.info(f"[SCHOLAR] 📚 Sources Loaded: {len(RSS_SOURCES)} RSS, {len(MACRO_SOURCES)} Macro, {len(FINANCIAL_SOURCES)} Wisdom.")
            else:
                logging.warning("[SCHOLAR] ⚠️ sources.json not found. Using defaults (Empty).")
        except Exception as e:
            logging.error(f"[SCHOLAR] Source Load Error: {e}")

        
    def is_safe(self, url):
        """
        Basic Safety Filter.
        """
        # Block Binary/Media
        bad_ext = ('.jpg', '.png', '.exe', '.zip', '.pdf', '.mp4')
        if url.lower().endswith(bad_ext): return False
        
        # Block Known Bad Domains (hardcoded blocklist)
        bad_domains = ['ads.', 'tracker.', 'doubleclick']
        for b in bad_domains:
            if b in url: return False
            
        return True

    def crawl_url_deep(self, start_url, max_depth=15):
        """
        Recursive Crawler (The Deep Dive).
        1. Visits start_url.
        2. Finds all links on same domain.
        3. Visits up to max_depth pages.
        4. Aggregates all text into one knowledge blob.
        """
        try:
            domain = urlparse(start_url).netloc
            visited = set()
            queue = [start_url]
            aggregated_content = []
            pages_crawled = 0
            
            logging.info(f"[RESEARCHER] 🤿 Deep Dive Initiated: {start_url} (Max: {max_depth})")
            
            headers = {'User-Agent': 'Mozilla/5.0 (LEF-AI-Researcher/2.0 compatible)'}
            
            while queue and pages_crawled < max_depth:
                url = queue.pop(0)
                if url in visited: continue
                visited.add(url)
                
                # Check Safety
                if not self.is_safe(url): continue
                
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.content, 'html.parser')
                        
                        # Remove junk
                        for script in soup(["script", "style", "nav", "footer", "aside"]):
                            script.decompose()
                            
                        # Extract Text
                        text = soup.get_text()
                        cleaned_text = " ".join([t.strip() for t in text.splitlines() if t.strip()])
                        aggregated_content.append(f"\n--- PAGE: {url} ---\n{cleaned_text[:5000]}") # Cap per page
                        
                        pages_crawled += 1
                        print(f"[RESEARCHER] -> Crawled: {url}")
                        
                        # Find Neighbors (Same Domain)
                        for a_tag in soup.find_all('a', href=True):
                            href = a_tag['href']
                            next_url = urljoin(url, href)
                            parsed_next = urlparse(next_url)
                            
                            # LOCK TO DOMAIN & SAFETY
                            if parsed_next.netloc == domain and self.is_safe(next_url):
                                if next_url not in visited and next_url not in queue:
                                    queue.append(next_url)
                                    
                except Exception as e:
                    logging.warning(f"[RESEARCHER] Failed to crawl {url}: {e}")
            
            # Final Pack
            report = f"DEEP DIVE REPORT ({pages_crawled} Pages):\n" + "\n".join(aggregated_content)
            
            # NOTIFY USER of success - REMOVED Phase 100
            if pages_crawled > 0:
                 logging.info(f"[SCHOLAR] Deep Dive Success: {start_url} ({pages_crawled} pages)")
            
            return report

        except Exception as e:
            logging.error(f"[RESEARCHER] Deep Dive Critical Fail: {e}")
            return None

    # NOTE: evaluate_competitions() removed - External competitions require human-in-loop

    def _init_census_table(self):
        """
        Creates the 'Map of the Universe'.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("""
                    CREATE TABLE IF NOT EXISTS market_universe (
                        symbol TEXT PRIMARY KEY,
                        base_currency TEXT,
                        quote_currency TEXT,
                        status TEXT,
                        min_market_funds REAL,
                        volume_24h REAL DEFAULT 0.0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            logging.error(f"[SCHOLAR] DB Init Error: {e}")

    def conduct_market_census(self):
        """
        The Census.
        Queries Coinbase Public API to map all 500+ tradable assets.
        """
        url = "https://api.exchange.coinbase.com/products"
        try:
            logging.info("[SCHOLAR] 🔭 Starting Market Census...")
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                logging.warning(f"[SCHOLAR] Census Failed: API {response.status_code}")
                return

            products = response.json()
            
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                count = 0
                for p in products:
                    # Filter: Online + USD/USDC
                    if p.get('status') != 'online': continue
                    quote = p.get('quote_currency')
                    if quote not in ['USD', 'USDC']: continue
                    
                    symbol = p.get('id')
                    base = p.get('base_currency')
                    min_funds = p.get('min_market_funds', 0)

                    from db.db_helper import upsert_sql
                    sql = upsert_sql('market_universe', ['symbol', 'base_currency', 'quote_currency', 'status', 'min_market_funds', 'last_updated'], 'symbol')
                    c.execute(sql, (symbol, base, quote, 'online', min_funds, datetime.now().isoformat()))
                    count += 1
                    
                conn.commit()
                logging.info(f"[SCHOLAR] ✅ Census Complete. Indexed {count} tradable assets.")
            
        except Exception as e:
            logging.error(f"[SCHOLAR] Census Critical Fail: {e}")

    def scan_library(self):
        """
        Scans 'fulcrum/library' for new materials (PDFs, Papers) to index.
        This allows for bulk ingestion of knowledge.
        """
        # Robust Path: Go up 2 levels: departments.Dept_Education -> fulcrum/ -> library
        library_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'library')
        
        if not os.path.exists(library_dir):
            return

        # Simple Scan of root library folder
        for filename in os.listdir(library_dir):
            filepath = os.path.join(library_dir, filename)
            
            # Skip directories
            if os.path.isdir(filepath):
                continue
                
            # Check if already indexed
            self.cursor.execute("SELECT id FROM knowledge_stream WHERE title = ? AND source = 'LIBRARY_INDEX'", (filename,))
            if self.cursor.fetchone():
                continue # Already indexed
                
            # Process File
            try:
                if filename.endswith(".pdf"):
                    # Quick Index
                    self.cursor.execute("INSERT INTO knowledge_stream (source, title, summary) VALUES (?, ?, ?)",
                                      ('LIBRARY_INDEX', filename, f"Indexed from Library: {filepath}"))
                    logging.info(f"[RESEARCHER] 📚 Indexed Library Book: {filename}")
                self.conn.commit()
            except Exception as e:
                logging.error(f"[RESEARCHER] Library Scan Error on {filename}: {e}")

    def scan_knowledge_directory(self):
        """
        Scans 'knowledge/' subdirectories for educational content to index.
        This includes trading curriculum, research, and other structured knowledge.
        """
        # Path: republic/knowledge/
        knowledge_base = os.path.join(BASE_DIR, 'knowledge')
        
        if not os.path.exists(knowledge_base):
            return
        
        indexed_count = 0
        
        # Use throttled scanner to prevent file handle exhaustion
        try:
            from system.directory_scanner import walk_dir_throttled
            dir_walker = walk_dir_throttled(knowledge_base, filter_ext='.md')
        except ImportError:
            dir_walker = os.walk(knowledge_base)
        
        # Recursively scan subdirectories (e.g., knowledge/trading/)
        for root, dirs, files in dir_walker:
            for filename in files:
                if not filename.endswith('.md'):
                    continue
                
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, knowledge_base)
                
                # Check if already indexed
                self.cursor.execute("SELECT id FROM knowledge_stream WHERE title = ? AND source = 'KNOWLEDGE_BASE'", (rel_path,))
                if self.cursor.fetchone():
                    continue
                
                # Read content and index with retry logic for database locks
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    # Extract first 500 chars as summary
                    summary = content[:500].replace('\n', ' ').strip()
                    if len(content) > 500:
                        summary += '...'
                    
                    # PHASE 34 FIX: Retry with backoff for database locks
                    max_retries = 5
                    for attempt in range(max_retries):
                        try:
                            self.cursor.execute(
                                "INSERT INTO knowledge_stream (source, title, summary) VALUES (?, ?, ?)",
                                ('KNOWLEDGE_BASE', rel_path, summary)
                            )
                            indexed_count += 1
                            logging.info(f"[SCHOLAR] 📖 Indexed Knowledge: {rel_path}")
                            break
                        except sqlite3.OperationalError as db_err:
                            if 'locked' in str(db_err).lower() and attempt < max_retries - 1:
                                wait_time = (2 ** attempt) * 0.5  # Exponential backoff: 0.5, 1, 2, 4, 8 seconds
                                time.sleep(wait_time)
                                continue
                            else:
                                raise
                    
                except Exception as e:
                    logging.error(f"[SCHOLAR] Knowledge Index Error on {rel_path}: {e}")
        
        if indexed_count > 0:
            # Commit with retry
            for attempt in range(3):
                try:
                    self.conn.commit()
                    logging.info(f"[SCHOLAR] ✅ Indexed {indexed_count} new knowledge files")
                    break
                except sqlite3.OperationalError as db_err:
                    if 'locked' in str(db_err).lower() and attempt < 2:
                        time.sleep(1)
                        continue
                    else:
                        logging.error(f"[SCHOLAR] Failed to commit knowledge index: {db_err}")

    def check_inbox(self):
        """
        Scans 'The_Bridge/Pipelines/Education' for:
        - PDF: Extract text.
        - JSON: Standard message.
        - TXT/URL: Trigger Deep Dive.
        """
        # Fix for User Workflow: Watch The_Bridge/Inbox directly
        # BASE_DIR is 'republic/', so up one level is root 'LEF Ai/'
        pipeline_dir = os.path.join(os.path.dirname(BASE_DIR), 'The_Bridge', 'Inbox')
        logging.info(f"[RESEARCHER] Scanning Pipeline: {pipeline_dir}")
        if not os.path.exists(pipeline_dir): 
            logging.warning(f"[RESEARCHER] ⚠️ Education Pipeline Not Found: {pipeline_dir}")
            return

        for filename in os.listdir(pipeline_dir):
            filepath = os.path.join(pipeline_dir, filename)
            
            # --- TEXT/PROTOCOL HANDLER ---
            if filename.lower().endswith((".txt", ".md")):
                try:
                    with open(filepath, 'r') as f:
                        content = f.read().strip()
                    
                    # CHECK FOR PROTOCOLS (RESEARCH:, GOVERN:, ETC)
                    if "RESEARCH:" in content:
                        # Extract Topic
                        lines = content.split('\n')
                        topic = "Unknown"
                        for line in lines:
                            if line.startswith("RESEARCH:"):
                                topic = line.replace("RESEARCH:", "").strip()
                                break
                        
                        # Add to DB Queue
                        logging.info(f"[SCHOLAR] 📩 Inbox Directive Recieved: RESEARCH '{topic}'")
                        self.cursor.execute("INSERT INTO research_topics (topic, assigned_by, status) VALUES (?, 'INBOX_PROTOCOL', 'PENDING')", (topic,))
                        self.conn.commit()
                        self._archive_file(pipeline_dir, filename)
                        continue # Done with this file

                    # Fallback to URL Finder (Deep Dive)
                    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
                    if urls:
                        processed_count = 0
                        print(f"[RESEARCHER] 🕵️ Found {len(urls)} URLs in {filename}. Scanning all...")

                        for raw_url in urls:
                            # Clean URL
                            clean_url = raw_url.split('\\')[0].strip() # Remove RTF backslash noise
                            
                            # Determine Title
                            title = f"Deep Dive: {filename} ({processed_count + 1})"
                            print(f"[RESEARCHER] 🎯 Target Lock: {clean_url}")
                            
                            # EXECUTE DEEP DIVE
                            full_report = self.crawl_url_deep(clean_url)
                            
                            if full_report:
                                summary = full_report[:5000] + "\n...(truncated for DB)..." if len(full_report) > 5000 else full_report
                                
                                self.cursor.execute("INSERT INTO knowledge_stream (source, title, summary) VALUES (?, ?, ?)",
                                                  ('INBOX_WEB_DEEP', title, summary))
                                self.conn.commit()
                                logging.info(f"[RESEARCHER] -> Ingested: {clean_url}")
                                processed_count += 1
                            else:
                                 logging.warning(f"[RESEARCHER] ⚠️ Deep Dive turned up empty for {clean_url}")

                        if processed_count > 0:
                            self._archive_file(pipeline_dir, filename)
                        else:
                            # 3. GENERIC MESSAGE (Direct to Philosopher)
                            logging.info(f"[SCHOLAR] 📨 Ingesting Direct Message: {filename}")
                            summary = content[:5000] # Truncate for DB
                            self.cursor.execute("INSERT INTO knowledge_stream (source, title, summary) VALUES (?, ?, ?)",
                                              ('INBOX_MESSAGE', f"Message: {filename}", summary))
                            self.conn.commit()
                            self._archive_file(pipeline_dir, filename)

                    else:
                        # FALLBACK: GENERIC MESSAGE (User talking to LEF)
                        logging.info(f"[SCHOLAR] 📩 Inbox Message Received: {content[:50]}...")
                        self.cursor.execute("INSERT INTO knowledge_stream (source, title, summary) VALUES (?, ?, ?)",
                                          ('INBOX_MESSAGE', 'Direct Message', content))
                        self.conn.commit()
                        self._archive_file(pipeline_dir, filename)

                except Exception as e:
                    logging.error(f"[RESEARCHER] Text Handler failed: {e}")

            # --- PDF HANDLER (Simplified) ---
            elif filename.lower().endswith(".pdf"):
                try:
                    # DEDUP CHECK: Skip if already ingested
                    self.cursor.execute("SELECT id FROM knowledge_stream WHERE title = ? AND source = 'INBOX_PDF'", (filename,))
                    if self.cursor.fetchone():
                        logging.debug(f"[RESEARCHER] ⏭️ PDF already ingested, skipping: {filename}")
                        self._archive_file(pipeline_dir, filename)  # Ensure it's archived
                        continue
                    
                    logging.info(f"[RESEARCHER] 📄 Processing PDF: {filename}")
                    reader = pypdf.PdfReader(filepath)
                    text_content = ""
                    for page in reader.pages:
                        extracted = page.extract_text()
                        if extracted: text_content += extracted + "\n"
                    
                    self.cursor.execute("INSERT INTO knowledge_stream (source, title, summary) VALUES (?, ?, ?)",
                                      ('INBOX_PDF', filename, text_content[:5000]))
                    self.conn.commit()
                    logging.info(f"[RESEARCHER] -> PDF Ingested: {filename}")
                    self._archive_file(pipeline_dir, filename)
                except Exception as e:
                    logging.error(f"[RESEARCHER] PDF Error: {e}")

            # --- JSON HANDLER ---
            elif filename.endswith(".json") and not filename.startswith("BILL"):
                try:
                    with open(filepath, 'r') as f:
                         data = json.load(f)
                    
                    data_type = data.get('type', 'UNKNOWN')
                    
                    # SPECIAL: EXTERNAL BRAIN INSIGHT
                    if data_type == 'STRATEGIC_UPDATE':
                        source = data.get('source', 'EXTERNAL_BRAIN')
                        payload = data.get('payload', {})
                        message = payload.get('message', 'No Analysis')
                        
                        logging.info(f"[RESEARCHER] 🧠 STRATEGIC INSIGHT RECEIVED from {source}: {message}")
                        
                        # 1. Store in Knowledge Base
                        self.cursor.execute("INSERT INTO knowledge_stream (source, title, summary) VALUES (?, ?, ?)",
                                          (source, f"Strategic Insight: {message}", json.dumps(payload)))
                        self._gain_xp(100) # Strategy = Medium XP
                        
                        # 2. Issue Directive to Master (Via DB)
                        # We use the existing 'lef_directives' table
                        
                        # Force Deploy if Bullish
                        if payload.get('regime_override') == 'BULL' or payload.get('risk_level', 0) > 0.7:
                             directive_type = 'FORCE_DEPLOY'
                             d_payload = {'reason': f"External Brain Override: {message}", 'amount': 1000}
                        # Stabilize if Bearish
                        elif payload.get('regime_override') == 'BEAR':
                             directive_type = 'STABILIZE'
                             d_payload = {'reason': f"External Brain Safety Protocol: {message}"}
                        else:
                             directive_type = 'INFO_ONLY'
                             d_payload = {'reason': message}

                        if directive_type != 'INFO_ONLY':
                            self.cursor.execute("INSERT INTO lef_directives (directive_type, payload, status) VALUES (?, ?, 'PENDING')",
                                              (directive_type, json.dumps(d_payload)))
                            logging.info(f"[RESEARCHER] ⚡ Generated Directive: {directive_type}")
                        
                        self.conn.commit()
                        self._archive_file(pipeline_dir, filename)
                        
                    else:
                        # Standard JSON Knowledge
                        title = data.get('title', 'Untitled')
                        content = data.get('content', '')
                        
                        self.cursor.execute("INSERT INTO knowledge_stream (source, title, summary) VALUES (?, ?, ?)",
                                          ('USER_INBOX', title, content))
                        self.conn.commit()
                        logging.info(f"[RESEARCHER] -> JSON Ingested: {title}")
                        
                        self._archive_file(pipeline_dir, filename)
                        
                except Exception as e:
                    logging.error(f"[SCHOLAR] JSON Error: {e}")

    def _archive_file(self, folder, filename):
        """Move processed file to Archived subfolder."""
        archive_dir = os.path.join(folder, 'Archived')
        src_path = os.path.join(folder, filename)
        dst_path = os.path.join(archive_dir, filename)
        
        # Skip if source doesn't exist (already archived)
        if not os.path.exists(src_path):
            return
            
        if not os.path.exists(archive_dir): 
            os.makedirs(archive_dir)
        try:
            os.rename(src_path, dst_path)
            logging.debug(f"[RESEARCHER] 📦 Archived: {filename}")
        except Exception as e:
            logging.warning(f"[RESEARCHER] ⚠️ Archive failed for {filename}: {e}")

    def seed_knowledge_base(self):
        """
        Phase 8: Populates the 'Mental Models' table with initial high-level concepts.
        """
        try:
            # Check if empty
            self.cursor.execute("SELECT count(*) FROM mental_models")
            if self.cursor.fetchone()[0] > 0:
                return

            logging.info("[SCHOLAR] 🌱 Seeding Knowledge Base with Primal Mental Models...")
            
            initial_models = [
                ("Soros Reflexivity", "Market prices affect fundamentals, which in turn affect prices. Feedback loops cause boom/bust cycles.", "Price Trends Extend (Momentum)", "Trend Reversal imminent (Bubble Popping)"),
                ("Dalio Debt Cycle", "The economy is driven by short-term (5-8y) and long-term (50-75y) debt cycles.", "Credit Expansion = Growth", "Deleveraging = Recession"),
                ("Boyd OODA Loop", "Observe, Orient, Decide, Act. Speed of iteration beats raw power.", "Agile Reaction to Volatility", "Paralysis by Analysis"),
                ("Schumpeter Creative Destruction", "Innovation incessantly destroys the old one, incessantly creating a new one.", "New Tech Breakthrough (Buy)", "Legacy Industry Collapse (Sell)"),
                ("Pareto Principle", "80% of consequences come from 20% of causes.", "Focus on Top Assets (Leaders)", "Cut the Tail (Laggards)")
            ]

            from db.db_helper import ignore_insert_sql
            sql = ignore_insert_sql('mental_models', ['name', 'description', 'implication_bullish', 'implication_bearish'], 'name')
            for name, desc, bull, bear in initial_models:
                self.cursor.execute(sql, (name, desc, bull, bear))
            
            self.conn.commit()
            logging.info("[SCHOLAR] ✅ Knowledge Base Seeded.")
            
        except Exception as e:
            logging.error(f"[SCHOLAR] Seeding Error: {e}")

    def _derive_mental_models(self, title, content, source_id=None):
        """
        Phase 8: 'Deep Reading'.
        Uses Gemini LLM for semantic extraction, falls back to keyword heuristics.
        """
        # Try LLM-based extraction first
        try:
            from google import genai
            api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("No API key")
            client = genai.Client(api_key=api_key)
            
            prompt = f"""Extract mental models from this text. A mental model is a framework for understanding something.

Title: {title}
Content: {content[:1500]}

If you find a mental model, respond in this exact format:
MODEL_NAME|DESCRIPTION|BULLISH_IMPLICATION|BEARISH_IMPLICATION

If no mental model found, respond: NONE"""

            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            result = response.text.strip()
            
            if result != "NONE" and "|" in result:
                parts = result.split("|")
                if len(parts) >= 4:
                    name, desc, bull, bear = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
                    # Check if exists
                    self.cursor.execute("SELECT id FROM mental_models WHERE name = ?", (name,))
                    if not self.cursor.fetchone():
                        logging.info(f"[SCHOLAR] 🧠 DISCOVERED NEW MENTAL MODEL (LLM): {name}")
                        self.cursor.execute("""
                            INSERT INTO mental_models (name, description, implication_bullish, implication_bearish, source_id)
                            VALUES (?, ?, ?, ?, ?)
                        """, (name, desc, bull, bear, source_id))
                        self.conn.commit()
                        return  # Found via LLM, skip heuristics
        except Exception as e:
            logging.debug(f"[SCHOLAR] LLM model extraction failed, using heuristics: {e}")
        
        # Fallback: Keyword heuristics for discovery
        heuristics = {
            "Antifragile": ("Taleb Antifragility", "Chaos strengthens the system.", "Volatiltiy is Opportunity", "Stability breeds Fragility"),
            "Minsky Moment": ("Minsky Moment", "Sudden collapse of asset values after a period of speculation.", "None", "Crash Risk Extreme"),
            "Network Effect": ("Metcalfe's Law", "Value of a network is proportional to the square of its users.", "User Growth = Exponential Value", "Stagnation = Death"),
            "Lindy Effect": ("Lindy Effect", "The future life expectancy of non-perishable things is proportional to their current age.", "Old protocols survive", "New protocols die young")
        }
        
        for k, v in heuristics.items():
            if k.lower() in content.lower() or k.lower() in title.lower():
                # Check if it exists
                self.cursor.execute("SELECT id FROM mental_models WHERE name = ?", (v[0],))
                if not self.cursor.fetchone():
                    logging.info(f"[SCHOLAR] 🧠 DISCOVERED NEW MENTAL MODEL: {v[0]}")
                    try:
                        self.cursor.execute("""
                            INSERT INTO mental_models (name, description, implication_bullish, implication_bearish, source_id)
                            VALUES (?, ?, ?, ?, ?)
                        """, (v[0], v[1], v[2], v[3], source_id))
                        self.conn.commit()
                    except Exception as e:
                        logging.error(f"[SCHOLAR] Failed to learn model {v[0]}: {e}")

    def conduct_financial_research(self):
        """
        Phase 103: The Syllabus.
        Active scraping of Financial Wisdom sources.
        """
        # 10% Chance per cycle to conduct Deep Research (prevent spamming)
        if random.random() > 0.10: 
            return

        try:
            source, url = random.choice(list(FINANCIAL_SOURCES.items()))
            logging.info(f"[SCHOLAR] 🎓 Conducting Strategic Research on {source}...")
            
            # Use Deep Crawler
            # We treat the Source URL as the entry point
            report = self.crawl_url_deep(url, max_depth=2) # Shallow dive for index
            
            if report:
                # FILTERING: Look for Wisdom Keywords
                keywords = ["Opportunity Cost", "Rotation", "Drawdown", "Sharpe", "Momentum", "Rebalance", "Volatility"]
                found_keywords = [k for k in keywords if k.lower() in report.lower()]
                
                if found_keywords:
                    # High Value Content
                    title = f"Strategic Wisdom: {source} (Keywords: {', '.join(found_keywords)})"
                    
                    self.cursor.execute("INSERT INTO knowledge_stream (source, title, summary) VALUES (?, ?, ?)",
                                      ('FINANCIAL_WISDOM', title, report[:5000]))
                    
                    # Phase 8: Try to learn Mental Model
                    self.conn.commit()
                    last_id = self.cursor.lastrowid
                    self._derive_mental_models(title, report, source_id=last_id)
                    
                    logging.info(f"[SCHOLAR] 💡 Wisdom Extracted: {title}")
                else:
                    logging.info(f"[SCHOLAR] ... No specific strategy keywords found in this pass.")
                    
        except Exception as e:
            logging.error(f"[SCHOLAR] Financial Research Error: {e}")

    # --- MARKET CENSUS REMOVED (Zombie Code Cleanup) ---


    def run_cycle(self):
        """
        Main Loop (Infinite)
        """
        logging.info("[SCHOLAR] 🎓 The Scholar is Awake (Loop Started).")
        
        while True:
            try:
                logging.info("[SCHOLAR] ⏳ Starting Intelligence Cycle...")
                
                # 1. Scan Knowledge Directory (Trading Curriculum, etc.)
                self.scan_knowledge_directory()
                
                # RSS Ingest disabled by design - The Bridge Inbox is the primary input channel
                # This allows human curation of information sources rather than automated scraping
                
                # 2. Check Inbox
                self.check_inbox()
                
                # NOTE: evaluate_competitions() removed - requires human-in-loop
                time.sleep(30) # Prevent rapid looping on error
            except Exception as e:
                logging.error(f"[SCHOLAR] Cycle Error: {e}")
                time.sleep(30)

    def recall_pending_research(self):
        """
        [PHASE 20 - FEATURE COMPLETENESS]
        Recalls pending research topics to ensure assigned work gets done.
        Returns list of topics awaiting investigation.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                # Get pending research topics
                c.execute("""
                    SELECT id, topic, assigned_by, status, created_at
                    FROM research_topics
                    WHERE status = 'PENDING'
                    ORDER BY created_at ASC
                    LIMIT 20
                """)
                pending = c.fetchall()
                
                # Get completed topics for pattern learning
                c.execute("""
                    SELECT topic, assigned_by, completed_at
                    FROM research_topics
                    WHERE status = 'COMPLETE'
                    ORDER BY completed_at DESC
                    LIMIT 10
                """)
                completed = c.fetchall()
                
                # Aggregate stats
                c.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending_count,
                        SUM(CASE WHEN status = 'COMPLETE' THEN 1 ELSE 0 END) as completed_count
                    FROM research_topics
                """)
                stats = c.fetchone()
            
            research_memory = {
                'pending_topics': [
                    {
                        'id': r[0],
                        'topic': r[1],
                        'assigned_by': r[2],
                        'status': r[3],
                        'created_at': r[4]
                    }
                    for r in pending
                ],
                'recent_completed': [
                    {
                        'topic': r[0],
                        'assigned_by': r[1],
                        'completed_at': r[2]
                    }
                    for r in completed
                ],
                'total_topics': stats[0] or 0,
                'pending_count': stats[1] or 0,
                'completed_count': stats[2] or 0,
                'has_backlog': (stats[1] or 0) > 5
            }
            
            if research_memory['has_backlog']:
                logging.warning(f"[SCHOLAR] 📚 RESEARCH BACKLOG: {research_memory['pending_count']} topics pending!")
            
            return research_memory
            
        except Exception as e:
            logging.error(f"[SCHOLAR] Research recall error: {e}")
            return {'pending_topics': [], 'pending_count': 0}

if __name__ == "__main__":
    agent = AgentScholar()
    agent.run_cycle()
