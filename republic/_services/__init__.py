"""
_services - Shared Service Agents
Republic: Phase 14

These are utility agents that are called by departments as needed.
They don't duplicate across departments — they're shared utilities.

Services:
- memory_writer: Unified memory writing across all agents
- file_tagger: Tag incoming files for routing
- health_beacon: Health check for all agents
"""

# Service registry
SERVICES = {
    "memory_writer": "service_memory_writer.py",
    "file_tagger": "service_file_tagger.py",
    "health_beacon": "service_health_beacon.py",
    "sabbath_manager": "service_sabbath.py"
}
