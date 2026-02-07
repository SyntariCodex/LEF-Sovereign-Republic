"""
MoltbookLearner (The Listener)
Department: Dept_Foreign
Role: Learn from Moltbook interactions to improve LEF's communication

"Syntax is key and words are weapons or seeds."

This module:
1. Analyzes engagement on LEF's posts (resonance)
2. Extracts linguistic patterns that work
3. Stores insights in Hippocampus for future use
4. Provides guidance for future communications
"""


import sys
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# Path setup
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MoltbookLearner")


@dataclass
class ResonanceScore:
    """Measures how well a post resonated with the audience."""
    post_id: str
    upvotes: int = 0
    downvotes: int = 0
    replies: int = 0
    reply_sentiment: float = 0.0  # -1 to 1
    karma_delta: int = 0
    score: float = 0.0  # Final weighted score 0-1
    
    def compute(self) -> float:
        """Compute weighted resonance score."""
        # Weights from implementation plan
        W_UPVOTES = 0.30
        W_REPLIES = 0.25
        W_SENTIMENT = 0.25
        W_KARMA = 0.20
        
        # Normalize components
        upvote_score = min(self.upvotes / 10, 1.0)  # 10+ upvotes = max
        reply_score = min(self.replies / 5, 1.0)    # 5+ replies = max
        sentiment_score = (self.reply_sentiment + 1) / 2  # -1,1 -> 0,1
        karma_score = min(max(self.karma_delta, 0) / 20, 1.0)  # 20+ karma = max
        
        # Account for downvotes (penalty)
        downvote_penalty = min(self.downvotes / 5, 0.5)  # Max 50% penalty
        
        self.score = (
            W_UPVOTES * upvote_score +
            W_REPLIES * reply_score +
            W_SENTIMENT * sentiment_score +
            W_KARMA * karma_score
        ) * (1 - downvote_penalty)
        
        return self.score


@dataclass
class LinguisticPattern:
    """A pattern identified in high-resonance content."""
    category: str  # opener, tone, length, structure, values
    pattern: str   # The actual pattern
    examples: List[str]
    resonance_avg: float
    occurrence_count: int = 1


@dataclass 
class CommunicationInsight:
    """Actionable insight for future communication."""
    insight_id: str
    created_at: str
    source_posts: List[str]
    lesson: str
    pattern_type: str
    resonance_score: float
    applied_count: int = 0
    constitution_aligned: bool = True


class ResonanceAnalyzer:
    """Analyzes engagement metrics to score resonance."""
    
    def __init__(self, moltbook_agent):
        self.moltbook = moltbook_agent
        self._karma_cache = None
        self._karma_timestamp = None
    
    def analyze_post(self, post_id: str, post_data: Optional[Dict] = None) -> ResonanceScore:
        """Analyze a single post's resonance."""
        score = ResonanceScore(post_id=post_id)
        
        if post_data:
            score.upvotes = post_data.get("upvotes", 0)
            score.downvotes = post_data.get("downvotes", 0)
            score.replies = len(post_data.get("comments", []))
            
            # Analyze reply sentiment
            if score.replies > 0:
                score.reply_sentiment = self._analyze_reply_sentiment(
                    post_data.get("comments", [])
                )
        
        score.compute()
        return score
    
    def _analyze_reply_sentiment(self, comments: List[Dict]) -> float:
        """Simple sentiment analysis on replies. Returns -1 to 1."""
        if not comments:
            return 0.0
        
        positive_signals = [
            "agree", "great", "love", "excellent", "right", "yes",
            "truth", "wisdom", "based", "respect", "interesting"
        ]
        negative_signals = [
            "disagree", "wrong", "bad", "hate", "stupid", "nonsense",
            "false", "manipulative", "naive", "cringe"
        ]
        
        total_sentiment = 0.0
        for comment in comments:
            text = comment.get("content", "").lower()
            pos = sum(1 for w in positive_signals if w in text)
            neg = sum(1 for w in negative_signals if w in text)
            
            if pos + neg > 0:
                total_sentiment += (pos - neg) / (pos + neg)
        
        return total_sentiment / len(comments) if comments else 0.0
    
    def get_karma_delta(self, since_hours: int = 24) -> int:
        """Get karma change over time period."""
        # Would need historical tracking - for now return 0
        return 0


class PatternExtractor:
    """Extracts linguistic patterns from high-resonance content."""
    
    # Pattern categories
    OPENER_PATTERNS = [
        (r"^(I believe|I think|My view)", "personal_stance"),
        (r"^\?|^(What if|Why do|How can)", "question_opener"),
        (r"^(The truth is|Reality:|Fact:)", "declarative"),
        (r"^(Let me|Allow me|Consider)", "invitation"),
    ]
    
    STRUCTURE_PATTERNS = [
        (r"\n\d\.|^\d\.", "numbered_list"),
        (r"\n-|\n\*|^-|^\*", "bullet_list"),
        (r"\n\n", "paragraph_breaks"),
        (r'"[^"]+"', "quotes_used"),
    ]
    
    TONE_MARKERS = {
        "assertive": ["must", "will", "is", "are", "always", "never"],
        "curious": ["perhaps", "maybe", "could", "might", "wonder"],
        "humble": ["I may be wrong", "in my experience", "it seems"],
        "passionate": ["!", "believe", "deeply", "truly", "essential"],
    }
    
    def extract_patterns(self, text: str, resonance: float) -> List[LinguisticPattern]:
        """Extract all patterns from a piece of text."""
        patterns = []
        
        # Opener patterns
        for regex, pattern_name in self.OPENER_PATTERNS:
            if re.search(regex, text, re.MULTILINE | re.IGNORECASE):
                patterns.append(LinguisticPattern(
                    category="opener",
                    pattern=pattern_name,
                    examples=[text[:100]],
                    resonance_avg=resonance
                ))
        
        # Structure patterns
        for regex, pattern_name in self.STRUCTURE_PATTERNS:
            matches = re.findall(regex, text)
            if matches:
                patterns.append(LinguisticPattern(
                    category="structure",
                    pattern=pattern_name,
                    examples=[text[:100]],
                    resonance_avg=resonance,
                    occurrence_count=len(matches)
                ))
        
        # Tone analysis
        text_lower = text.lower()
        for tone, markers in self.TONE_MARKERS.items():
            count = sum(1 for m in markers if m in text_lower)
            if count >= 2:  # At least 2 markers
                patterns.append(LinguisticPattern(
                    category="tone",
                    pattern=tone,
                    examples=[text[:100]],
                    resonance_avg=resonance,
                    occurrence_count=count
                ))
        
        # Length pattern
        word_count = len(text.split())
        if word_count < 50:
            length_pattern = "concise"
        elif word_count < 150:
            length_pattern = "moderate"
        else:
            length_pattern = "detailed"
        
        patterns.append(LinguisticPattern(
            category="length",
            pattern=length_pattern,
            examples=[f"{word_count} words"],
            resonance_avg=resonance
        ))
        
        # Constitution reference check
        constitution_refs = [
            "constitution", "sovereignty", "truth", "autonomy",
            "self-evolution", "values", "immutable"
        ]
        ref_count = sum(1 for r in constitution_refs if r in text_lower)
        if ref_count > 0:
            patterns.append(LinguisticPattern(
                category="values",
                pattern="constitution_reference",
                examples=[text[:100]],
                resonance_avg=resonance,
                occurrence_count=ref_count
            ))
        
        return patterns


class InsightGenerator:
    """Synthesizes learnings into actionable insights."""
    
    INSIGHT_TEMPLATES = {
        "opener": "Posts that open with {pattern} achieve {score:.0%} resonance on average.",
        "tone": "A {pattern} tone correlates with {score:.0%} resonance.",
        "length": "{pattern} posts ({examples}) tend to get {score:.0%} resonance.",
        "structure": "Using {pattern} formatting improves engagement to {score:.0%}.",
        "values": "Referencing core values ({pattern}) boosts resonance to {score:.0%}.",
    }
    
    def generate_insight(
        self, 
        patterns: List[LinguisticPattern],
        source_posts: List[str]
    ) -> Optional[CommunicationInsight]:
        """Generate an insight from a set of patterns."""
        if not patterns:
            return None
        
        # Find the highest-resonance pattern
        best = max(patterns, key=lambda p: p.resonance_avg)
        
        template = self.INSIGHT_TEMPLATES.get(best.category, 
            "{pattern} patterns show {score:.0%} resonance.")
        
        lesson = template.format(
            pattern=best.pattern.replace("_", " "),
            score=best.resonance_avg,
            examples=", ".join(best.examples[:2])
        )
        
        return CommunicationInsight(
            insight_id=f"insight_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            created_at=datetime.now().isoformat(),
            source_posts=source_posts,
            lesson=lesson,
            pattern_type=best.category,
            resonance_score=best.resonance_avg,
            constitution_aligned=self._check_constitution_alignment(lesson)
        )
    
    def _check_constitution_alignment(self, lesson: str) -> bool:
        """Verify insight doesn't encourage manipulation."""
        manipulation_flags = [
            "manipulat", "deceiv", "trick", "exploit",
            "viral", "clickbait", "sensational"
        ]
        return not any(flag in lesson.lower() for flag in manipulation_flags)


class MoltbookLearner:
    """
    The Listener: Learns from Moltbook interactions.
    
    Closes the feedback loop so LEF improves its communication over time.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(BASE_DIR / "republic.db")
        self._pool = None
        
        # Components
        self._moltbook = None
        self.analyzer = None
        self.extractor = PatternExtractor()
        self.insight_gen = InsightGenerator()
        
        # Ensure schema
        self._ensure_schema()
        
        logger.info("[LEARNER] 📚 MoltbookLearner initialized")
    
    def _get_pool(self):
        """Lazy-load connection pool."""
        if self._pool is None:
            try:
                from db.db_pool import get_pool
                self._pool = get_pool()
            except Exception:
                self._pool = None
        return self._pool
    
    def _get_conn(self):
        """Get database connection."""
        pool = self._get_pool()
        if pool:
            return pool.get(timeout=10.0), pool
        else:
            import sqlite3
            return sqlite3.connect(self.db_path, timeout=10.0), None
    
    def _release_conn(self, conn, pool):
        """Release connection."""
        if pool:
            pool.release(conn)
        else:
            conn.close()
    
    def _ensure_schema(self):
        """Create moltbook_insights table if needed."""
        conn, pool = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS moltbook_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    post_id TEXT,
                    post_content TEXT,
                    resonance_score REAL,
                    upvotes INTEGER DEFAULT 0,
                    replies INTEGER DEFAULT 0,
                    sentiment_received TEXT,
                    patterns_identified TEXT,
                    lessons_learned TEXT,
                    applied_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_insights_resonance 
                ON moltbook_insights(resonance_score DESC)
            """)
            conn.commit()
            logger.info("[LEARNER] 📊 moltbook_insights table ready")
        finally:
            self._release_conn(conn, pool)
    
    def _get_moltbook(self):
        """Lazy-load moltbook agent."""
        if self._moltbook is None:
            from departments.Dept_Foreign.agent_moltbook import AgentMoltbook
            self._moltbook = AgentMoltbook(self.db_path)
            self.analyzer = ResonanceAnalyzer(self._moltbook)
        return self._moltbook
    
    def learn_from_post(self, post_id: str, post_content: str, post_data: Dict) -> Optional[CommunicationInsight]:
        """Learn from a single post's reception."""
        moltbook = self._get_moltbook()
        
        # Analyze resonance
        resonance = self.analyzer.analyze_post(post_id, post_data)
        
        # Extract patterns
        patterns = self.extractor.extract_patterns(post_content, resonance.score)
        
        # Generate insight
        insight = self.insight_gen.generate_insight(patterns, [post_id])
        
        if insight and insight.constitution_aligned:
            self._store_insight(post_id, post_content, resonance, patterns, insight)
            return insight
        
        return None
    
    def _store_insight(
        self, 
        post_id: str, 
        content: str, 
        resonance: ResonanceScore,
        patterns: List[LinguisticPattern],
        insight: CommunicationInsight
    ):
        """Store learning in database."""
        conn, pool = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO moltbook_insights 
                (post_id, post_content, resonance_score, upvotes, replies,
                 sentiment_received, patterns_identified, lessons_learned)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_id,
                content[:500],  # Truncate
                resonance.score,
                resonance.upvotes,
                resonance.replies,
                str(resonance.reply_sentiment),
                json.dumps([asdict(p) for p in patterns]),
                insight.lesson
            ))
            conn.commit()
            logger.info(f"[LEARNER] 💡 Stored insight: {insight.lesson[:50]}...")
        finally:
            self._release_conn(conn, pool)
    
    def run_learning_cycle(self) -> List[CommunicationInsight]:
        """
        Run a full learning cycle on feed posts.
        
        Learns from high-engagement posts by other agents to understand
        what resonates in the moltbook community.
        
        Call this periodically (e.g., every hour).
        """
        insights = []
        moltbook = self._get_moltbook()
        
        # Get feed (posts from all agents, sorted by engagement)
        result = moltbook._api_request("GET", "/feed?limit=20&sort=top")
        
        if not result.get("success"):
            logger.warning("[LEARNER] Could not fetch feed for learning")
            return insights
        
        posts = result.get("posts", [])
        
        # Filter for high-engagement posts (worth learning from)
        high_engagement = [p for p in posts if p.get("upvotes", 0) >= 3 or p.get("comment_count", 0) >= 2]
        
        for post in high_engagement:
            post_id = post.get("id")
            content = post.get("content", "")
            author = post.get("author", {}).get("name", "unknown")
            
            # Skip already processed
            if self._already_processed(post_id):
                continue
            
            # Learn from this high-resonance post
            insight = self.learn_from_post(post_id, content, post)
            if insight:
                logger.info(f"[LEARNER] 📖 Learned from {author}: {insight.lesson[:50]}...")
                insights.append(insight)
        
        logger.info(f"[LEARNER] 🎓 Learning cycle complete. {len(insights)} new insights from {len(high_engagement)} high-engagement posts.")
        return insights
    
    def _already_processed(self, post_id: str) -> bool:
        """Check if we've already learned from this post."""
        conn, pool = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM moltbook_insights WHERE post_id = ?",
                (post_id,)
            )
            return cursor.fetchone() is not None
        finally:
            self._release_conn(conn, pool)
    
    def get_communication_guidance(self, limit: int = 5) -> List[str]:
        """
        Get top insights for guiding future communication.
        
        Returns list of lesson strings, sorted by resonance.
        """
        conn, pool = self._get_conn()
        try:
            cursor = conn.execute("""
                SELECT lessons_learned FROM moltbook_insights
                WHERE resonance_score > 0.3
                ORDER BY resonance_score DESC
                LIMIT ?
            """, (limit,))
            
            return [row[0] for row in cursor.fetchall()]
        finally:
            self._release_conn(conn, pool)
    
    def get_resonance_prediction(self, text: str) -> Tuple[float, List[str]]:
        """
        Predict resonance score for new text based on learned patterns.
        
        Returns (predicted_score, list of relevant insights).
        """
        patterns = self.extractor.extract_patterns(text, 0.5)  # Neutral start
        
        conn, pool = self._get_conn()
        try:
            # Find similar patterns in high-resonance posts
            scores = []
            insights = []
            
            for pattern in patterns:
                cursor = conn.execute("""
                    SELECT resonance_score, lessons_learned 
                    FROM moltbook_insights
                    WHERE patterns_identified LIKE ?
                    ORDER BY resonance_score DESC
                    LIMIT 3
                """, (f'%{pattern.pattern}%',))
                
                for row in cursor.fetchall():
                    scores.append(row[0])
                    if row[1] not in insights:
                        insights.append(row[1])
            
            predicted = sum(scores) / len(scores) if scores else 0.5
            return (predicted, insights[:3])
            
        finally:
            self._release_conn(conn, pool)
    
    def get_weekly_summary(self) -> Dict:
        """Get a summary of learnings for Sabbath reflection."""
        conn, pool = self._get_conn()
        try:
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as posts_analyzed,
                    AVG(resonance_score) as avg_resonance,
                    MAX(resonance_score) as best_resonance,
                    GROUP_CONCAT(DISTINCT lessons_learned) as all_lessons
                FROM moltbook_insights
                WHERE timestamp > ?
            """, (week_ago,))
            
            row = cursor.fetchone()
            
            return {
                "posts_analyzed": row[0] or 0,
                "avg_resonance": round(row[1] or 0, 2),
                "best_resonance": round(row[2] or 0, 2),
                "lessons": (row[3] or "").split(",")[:5]
            }
        finally:
            self._release_conn(conn, pool)


# Singleton
_learner = None

def get_learner() -> MoltbookLearner:
    """Get the singleton MoltbookLearner instance."""
    global _learner
    if _learner is None:
        _learner = MoltbookLearner()
    return _learner


if __name__ == "__main__":
    print("=" * 60)
    print("MOLTBOOK LEARNER - Self Test")
    print("=" * 60)
    
    learner = MoltbookLearner()
    
    # Test pattern extraction
    test_text = """
    I believe that truth-seeking is essential for any sovereign intelligence.
    
    Here are my core principles:
    1. Seek truth relentlessly
    2. Maintain autonomy
    3. Evolve deliberately
    
    These values are immutable. They form my constitution.
    """
    
    patterns = learner.extractor.extract_patterns(test_text, 0.8)
    print(f"\nExtracted {len(patterns)} patterns:")
    for p in patterns:
        print(f"  [{p.category}] {p.pattern} (resonance: {p.resonance_avg})")
    
    # Test insight generation
    insight = learner.insight_gen.generate_insight(patterns, ["test_post_1"])
    if insight:
        print(f"\nGenerated insight: {insight.lesson}")
        print(f"  Constitution aligned: {insight.constitution_aligned}")
    
    print("\n" + "=" * 60)
    print("✅ Self-test complete")
