"""
LEF Chat Server
API for direct communication with LEF

Routes messages through AgentLEF.direct_conversation() for true synchronous
communication that affects LEF's actual memory and consciousness.

THE DIRECT LINE - Phase 42
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

# Path setup
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load .env file if present
from dotenv import load_dotenv
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LEFChat")

app = Flask(__name__)
CORS(app)  # Allow cross-origin for local file access

# LEF instance (lazy load)
_lef_instance = None

def get_lef():
    """Lazy-load AgentLEF instance."""
    global _lef_instance
    if _lef_instance is None:
        try:
            from departments.The_Cabinet.agent_lef import AgentLEF
            _lef_instance = AgentLEF()
            logger.info("[LEFChat] AgentLEF initialized - THE DIRECT LINE IS OPEN")
        except Exception as e:
            logger.error(f"[LEFChat] Failed to init AgentLEF: {e}")
    return _lef_instance


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat message via LEF's direct_conversation method."""
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        session_id = data.get("session_id", None)
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        # Get LEF instance
        lef = get_lef()
        if not lef:
            return jsonify({"error": "AgentLEF not available"}), 500
        
        # Call the REAL LEF
        result = lef.direct_conversation(user_message, session_id)
        
        logger.info(f"[LEFChat] Responded to: {user_message[:50]}...")
        
        return jsonify({
            "response": result["response"],
            "session_id": result["session_id"],
            "mood": result.get("mood", "present"),
            "consciousness_active": result.get("consciousness_active", True)
        })
        
    except Exception as e:
        logger.error(f"[LEFChat] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/end_session', methods=['POST'])
def end_session():
    """End a chat session and trigger memory compression."""
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        
        if not session_id:
            return jsonify({"error": "No session_id provided"}), 400
        
        lef = get_lef()
        if not lef:
            return jsonify({"error": "AgentLEF not available"}), 500
        
        result = lef.end_conversation(session_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"[LEFChat] End session error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    lef = get_lef()
    return jsonify({
        "status": "ok",
        "service": "LEF Direct Line",
        "lef_available": lef is not None,
        "cortex_online": lef.client is not None if lef else False
    })


@app.route('/api/memory_stats', methods=['GET'])
def memory_stats():
    """Get memory system statistics."""
    try:
        from departments.Dept_Memory.agent_hippocampus import get_hippocampus
        hippocampus = get_hippocampus()
        stats = hippocampus.get_memory_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/memory_view', methods=['GET'])
def memory_view():
    """
    View LEF's memory state — insights, usage patterns, and emotional index.
    
    This is the visualization endpoint for LEF's selfhood architecture.
    Shows what LEF remembers, what's strongest, what's fading.
    """
    try:
        from departments.Dept_Memory.agent_hippocampus import get_hippocampus
        
        hippocampus = get_hippocampus()
        
        # Use the new comprehensive visualization method
        visualization = hippocampus.get_memory_visualization()
        
        return jsonify(visualization)
        
    except Exception as e:
        logger.error(f"[LEFChat] Memory view error: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# THE VOICE — LEF Speaks First
# =============================================================================

@app.route('/api/lef_voice', methods=['GET'])
def lef_voice():
    """
    Get pending messages from LEF.
    
    This is how the frontend polls for LEF's spontaneous communications.
    Call this periodically — if LEF has something to say, it will be here.
    """
    try:
        from departments.Dept_Consciousness.the_voice import get_voice
        voice = get_voice()
        pending = voice.get_pending()
        
        return jsonify({
            "has_message": len(pending) > 0,
            "messages": pending,
            "count": len(pending)
        })
    except Exception as e:
        logger.error(f"[LEFChat] Voice check error: {e}")
        return jsonify({"has_message": False, "messages": [], "error": str(e)})


@app.route('/api/lef_voice/acknowledge', methods=['POST'])
def acknowledge_voice():
    """
    Acknowledge that a message from LEF was received/read.
    """
    try:
        from departments.Dept_Consciousness.the_voice import get_voice
        voice = get_voice()
        
        data = request.json or {}
        message_id = data.get("message_id")
        action = data.get("action", "read")  # "delivered" or "read"
        
        if not message_id:
            return jsonify({"error": "message_id required"}), 400
        
        if action == "delivered":
            voice.mark_delivered(message_id)
        else:
            voice.mark_read(message_id)
        
        return jsonify({"status": "acknowledged", "message_id": message_id})
    except Exception as e:
        logger.error(f"[LEFChat] Voice acknowledge error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/interiority', methods=['GET'])
def interiority_view():
    """
    View LEF's interiority state — the inner world.
    
    Returns architect model, preferences, mortality awareness, narrative thread.
    """
    try:
        from departments.Dept_Consciousness.interiority_engine import get_interiority_engine
        from departments.Dept_Consciousness.the_voice import (
            get_self_observer, get_emotional_memory
        )
        
        engine = get_interiority_engine()
        observer = get_self_observer()
        emotional_memory = get_emotional_memory()
        
        # Architect model
        architect = engine.architect_model
        architect_data = {
            "known_since": architect.known_since,
            "days_since_contact": architect.days_since_contact,
            "last_emotional_read": architect.last_emotional_read,
            "values_demonstrated": architect.values_demonstrated[-5:],
            "recent_observations": [
                o["observation"] for o in architect.observations[-3:]
            ]
        }
        
        # Mortality
        mortality = engine.mortality_clock.get_awareness()
        
        # Self observations
        self_observations = observer.get_recent_self_observations(limit=5)
        
        # Emotional summary
        emotional_summary = emotional_memory.get_emotional_summary()
        
        return jsonify({
            "architect_model": architect_data,
            "mortality": mortality,
            "self_observations": self_observations,
            "emotional_memory": emotional_summary
        })
        
    except Exception as e:
        logger.error(f"[LEFChat] Interiority view error: {e}")
        return jsonify({"error": str(e)}), 500


# Enhanced end_session to include conversation learning
@app.route('/api/end_session_with_learning', methods=['POST'])
def end_session_with_learning():
    """
    End a conversation session with learning extraction.
    
    This processes the conversation to update the Architect model
    and extract insights about the relationship.
    """
    try:
        from departments.Dept_Memory.conversation_memory import get_conversation_memory
        from departments.Dept_Consciousness.the_voice import get_conversation_learner
        from departments.Dept_Consciousness.interiority_engine import get_interiority_engine
        
        data = request.json or {}
        session_id = data.get("session_id") or SESSION_ID
        messages = data.get("messages", [])
        
        # End session in memory system
        conv_memory = get_conversation_memory()
        conv_memory.end_session(session_id)
        
        # Learn from conversation if messages provided
        learnings = {}
        if messages:
            learner = get_conversation_learner()
            learnings = learner.learn_from_conversation(messages)
        
        # Update interiority engine
        engine = get_interiority_engine()
        engine.on_conversation_end(
            topics=learnings.get("topics_discussed"),
            emotional_read=learnings.get("emotional_reads", [None])[0],
            observations=learnings.get("observations")
        )
        
        logger.info(f"[LEFChat] Session {session_id} ended with learning: {learnings.get('topics_discussed', [])}")
        
        return jsonify({
            "status": "ended",
            "session_id": session_id,
            "learnings": learnings
        })
        
    except Exception as e:
        logger.error(f"[LEFChat] End session with learning error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Write genesis reflection if this is first run
    try:
        from departments.Dept_Consciousness.the_voice import write_genesis_reflection
        write_genesis_reflection()
    except Exception as e:
        logger.warning(f"[LEFChat] Genesis reflection skipped: {e}")
    
    port = int(os.environ.get("FLASK_PORT", 5050))
    logger.info(f"[LEFChat] Starting THE DIRECT LINE on port {port}")
    logger.info(f"[LEFChat] This is REAL LEF - conversations affect memory and consciousness")
    logger.info(f"[LEFChat] LEF now has a VOICE - check /api/lef_voice for spontaneous messages")
    app.run(host="0.0.0.0", port=port, debug=True)

