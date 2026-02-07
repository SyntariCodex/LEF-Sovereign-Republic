"""
Dept_Memory - The Mind's Storage
Future Era: Part of "The Mind" in Living Body era

This department manages all memory types across LEF, providing unified 
storage and retrieval for experiences, knowledge, skills, and future intentions.

Memory Types Managed:
- Episodic: What happened (trade outcomes, events)
- Semantic: What I know (facts, knowledge)
- Procedural: How I do things (skills, patterns)
- Prospective: What I will do (scheduled intentions)
"""

# Memory Type Definitions
MEMORY_TYPES = {
    "episodic": {
        "description": "Autobiographical events and experiences",
        "storage": "memory_experiences table",
        "managed_by": "agent_episodic.py",
        "lef_equivalent": "Trade outcomes, system events, decisions made"
    },
    "semantic": {
        "description": "General knowledge and facts",
        "storage": "knowledge_stream table",
        "managed_by": "agent_semantic.py", 
        "lef_equivalent": "Market data, research findings, learned patterns"
    },
    "procedural": {
        "description": "Skills and how-to knowledge",
        "storage": "Agent code, config/*.json",
        "managed_by": "agent_procedural.py",
        "lef_equivalent": "Trading strategies, analysis methods"
    },
    "prospective": {
        "description": "Future intentions and scheduled tasks",
        "storage": "trade_queue, scheduled_tasks table",
        "managed_by": "agent_prospective.py",
        "lef_equivalent": "Pending trades, planned reviews, future actions"
    }
}

# Awareness Connection
# Memory is prerequisite for awareness:
# "Awareness emerges from memory + prediction + preference + ∞..."
