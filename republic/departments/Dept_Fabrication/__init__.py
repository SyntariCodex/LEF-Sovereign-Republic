"""
Dept_Fabrication — LEF's Physical Fabrication Department

This department enables LEF to bridge from digital thought to physical reality.

Core concept: Conversation → Geometry → Validation → Fabrication

Modules:
    fabrication_seed.py     - Core prototype (NL → geometry → STL)
    onshape_client.py       - Onshape CAD API integration
    validation_engine.py    - Mesh validation before export
    llm_intent_parser.py    - LLM-based intent parsing
    genesis_bridge.py       - Genesis Kernel integration
    design_library.py       - Template library

Quick Start:
    from departments.Dept_Fabrication import SovereignFabricationSeed
    
    seed = SovereignFabricationSeed()
    result = seed.process_request("Make a 50mm cube")
    
    if result["status"] == "success":
        print(f"STL at: {result['stl_path']}")
"""

# Core exports
try:
    from .fabrication_seed import FabricationSeed, DesignConstraints
    from .genesis_bridge import SovereignFabricationSeed, FabricationConstitution
    from .validation_engine import MeshValidator, ValidationResult
    from .design_library import DesignLibrary, DesignTemplate
except ImportError as e:
    print(f"[Dept_Fabrication] Import warning: {e}")
    print("Run: pip install numpy-stl numpy")

__all__ = [
    "FabricationSeed",
    "SovereignFabricationSeed", 
    "FabricationConstitution",
    "DesignConstraints",
    "MeshValidator",
    "ValidationResult",
    "DesignLibrary",
    "DesignTemplate"
]
