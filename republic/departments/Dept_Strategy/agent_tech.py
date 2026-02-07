"""
AgentTech (The Innovator)
Department: Dept_Strategy
Role: AI Research & Tech Tracking (ArXiv/HuggingFace)
"""

import requests
import xml.etree.ElementTree as ET
import time
import logging
import redis

class AgentTech:
    def __init__(self, db_path=None):
        logging.info("[TECH] 🔭 Tech Scanner Online.")
        # Redis - Use shared singleton
        try:
            from system.redis_client import get_redis
            self.r = get_redis()
        except ImportError:
            try:
                self.r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.r.ping()
            except (redis.RedisError, ConnectionError):
                self.r = None

    def scan_arxiv(self) -> float:
        """
        Scrapes ArXiv API for recent AI papers.
        """
        logging.info("[TECH] 🔭 Scanning ArXiv for Research Breakthroughs...")
        keywords = ['LLM', 'Agentic', 'Transformer', 'Multi-Modal', 'AGI', 'Q*', 'Reasoning']
        url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG&start=0&max_results=10&sortBy=submittedDate&sortOrder=descending"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200: return 0.0
                
            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            breakthrough_score = 0
            
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text or ""
                summary = entry.find('atom:summary', ns).text or ""
                
                hits = [k for k in keywords if k.lower() in title.lower() or k.lower() in summary.lower()]
                if hits:
                    breakthrough_score += len(hits) * 10
                    logging.info(f"[TECH] 📄 Paper Found: {title[:60]}...")
                    
            score = min(breakthrough_score, 100)
            if self.r: self.r.set("macro:tech_acceleration", score)
            return score
        except Exception as e:
            logging.error(f"[TECH] Scan Failed: {e}")
            return 0.0

    # NOTE: scan_hackathons() removed - Hackathons/Competitions require human-in-loop

    def run_cycle(self):
        self.scan_arxiv()

def run_tech_loop(db_path=None):
    agent = AgentTech(db_path)
    while True:
        try:
            agent.run_cycle()
            time.sleep(3600) # Hourly scan
        except Exception as e:
            logging.error(f"[TECH] Loop Error: {e}")
            time.sleep(60)

