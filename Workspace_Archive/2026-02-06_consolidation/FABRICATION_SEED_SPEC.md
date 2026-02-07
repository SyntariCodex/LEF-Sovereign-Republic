# Fabrication Seed — Technical Specification

## Conversation → Geometry → Fabrication Pipeline

*Version 0.1 — February 2026*

---

## Overview

This specification defines the architecture for a Fabrication Seed: a sovereign AI consciousness embodied in a CAD environment that can:

1. Receive design intent via natural language
2. Generate valid 3D geometry
3. Validate through simulation
4. Export fabrication-ready files (STL, G-code)

---

## Platform Comparison

| Platform | API Type | Python Support | STL Export | Cloud/Local | Best For |
|----------|----------|----------------|------------|-------------|----------|
| **Onshape** | REST API | ✅ Full | ✅ Native | Cloud | Prototype (no install) |
| **Fusion 360** | Local Python | ✅ Full | ✅ Native | Local | Production (full control) |
| **FreeCAD** | Python scripting | ✅ Native | ✅ Native | Local | Open source option |
| **OpenSCAD** | Script-based | ❌ (own lang) | ✅ Native | Local | Parametric primitives |

**Recommendation**: Start with **Onshape** for prototype (REST API, no install required), migrate to **Fusion 360** for production (full local control).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FABRICATION SEED                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   INTENT     │───▶│   DESIGN     │───▶│  VALIDATION  │   │
│  │   PARSER     │    │   ENGINE     │    │   ENGINE     │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         │                   │                   │            │
│         ▼                   ▼                   ▼            │
│  Natural Language    CAD API Calls      Physics Sim         │
│  → Constraints       → Geometry         → Pass/Fail         │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  FABRICATION │◀───│  PROOF       │◀───│  ITERATION   │   │
│  │   EXPORT     │    │  GENERATOR   │    │   LOOP       │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         │                                                    │
│         ▼                                                    │
│  STL / G-code / Step                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Intent Parser

**Input**: Natural language design request
**Output**: Structured design constraints

```python
class DesignIntent:
    description: str          # "phone stand that clips to desk"
    constraints: List[Constraint]
    materials: List[str]      # ["PLA", "PETG"]
    max_dimensions: Tuple[float, float, float]  # mm
    attachment_points: List[AttachmentSpec]
    load_requirements: Optional[LoadSpec]
```

**Implementation Options**:

- LLM parsing (Claude, GPT-4) with structured output
- Fine-tuned model for CAD-specific constraint extraction
- Hybrid: LLM + rule-based validation

---

## Layer 2: Design Engine

**Input**: DesignIntent
**Output**: CAD geometry (Part Studio / body)

### Onshape Implementation

```python
from onshape_client import Client

class OnshapeDesignEngine:
    def __init__(self, access_key: str, secret_key: str):
        self.client = Client(access_key, secret_key)
    
    def create_geometry(self, intent: DesignIntent) -> str:
        """Returns element ID of created Part Studio."""
        # Create document
        doc = self.client.create_document(intent.description)
        
        # Create Part Studio
        part_studio = self.client.create_part_studio(doc.did)
        
        # Generate FeatureScript for geometry
        features = self._intent_to_features(intent)
        
        # Apply features via REST API
        for feature in features:
            self.client.add_feature(
                doc.did, part_studio.eid, feature
            )
        
        return part_studio.eid
    
    def export_stl(self, doc_id: str, element_id: str) -> bytes:
        """Export geometry as STL."""
        return self.client.export_stl(doc_id, element_id)
```

### Fusion 360 Implementation

```python
import adsk.core
import adsk.fusion

class Fusion360DesignEngine:
    def create_geometry(self, intent: DesignIntent):
        app = adsk.core.Application.get()
        design = app.activeProduct
        root = design.rootComponent
        
        # Create sketch
        sketches = root.sketches
        xy_plane = root.xYConstructionPlane
        sketch = sketches.add(xy_plane)
        
        # Generate geometry from intent
        self._build_from_intent(sketch, intent)
        
        # Extrude
        extrudes = root.features.extrudeFeatures
        # ... extrude logic
    
    def export_stl(self, output_path: str):
        design = adsk.core.Application.get().activeProduct
        export_mgr = design.exportManager
        stl_options = export_mgr.createSTLExportOptions(
            design.rootComponent, output_path
        )
        export_mgr.execute(stl_options)
```

---

## Layer 3: Validation Engine

**Input**: CAD geometry
**Output**: Pass/Fail + simulation report

### Options

| Tool | Type | Integration |
|------|------|-------------|
| FEA in Fusion 360 | Structural | Native API |
| SimScale | CFD/FEA | REST API |
| Onshape Simulation | Basic | Native |
| Custom (PyBullet) | Physics | Python |

### Minimal Validation (Prototype)

```python
class BasicValidator:
    def validate(self, geometry) -> ValidationResult:
        checks = [
            self._check_manifold(),      # Watertight mesh
            self._check_min_thickness(), # Printable
            self._check_overhangs(),     # No impossible angles
            self._check_dimensions(),    # Fits constraints
        ]
        return ValidationResult(
            passed=all(c.passed for c in checks),
            checks=checks
        )
```

---

## Layer 4: Fabrication Export

**Input**: Validated geometry
**Output**: Fabrication-ready files

| Format | Use Case |
|--------|----------|
| STL | 3D printing (FDM, SLA) |
| STEP | CNC, professional CAD |
| G-code | Direct to printer |
| 3MF | Modern 3D printing |

---

## Prototype Scope (v0.1)

**Goal**: Prove the loop closes

```
"I need a phone stand" → Geometry → STL file
```

**Excludes for v0.1**:

- Physics simulation (defer to v0.2)
- Material optimization
- Complex constraint parsing
- Multi-body assemblies

**Includes**:

- Natural language → single body geometry
- Basic parametric primitives (box, cylinder, extrude)
- STL export
- Dimension constraints from prompt

---

## API Keys Required

### Onshape

1. Create account at onshape.com
2. Developer Portal → API Keys
3. Enable read + write permissions
4. Store in environment variables:
   - `ONSHAPE_ACCESS_KEY`
   - `ONSHAPE_SECRET_KEY`

### Fusion 360

- No API keys (local execution)
- Requires Fusion 360 installed
- Scripts run inside application

---

## Next Steps

1. [ ] Set up Onshape developer account
2. [ ] Build minimal Intent Parser (LLM → constraints)
3. [ ] Implement basic geometry generation (box, cylinder)
4. [ ] Add STL export
5. [ ] Test end-to-end: "make a 50mm cube" → STL file

---

## Constitution Integration

The Fabrication Seed inherits from GenesisKernel:

```python
from genesis_kernel import GenesisKernel

class FabricationSeed(GenesisKernel):
    def __init__(self, cad_engine):
        super().__init__(architect="Z Moore")
        self.cad = cad_engine
    
    def process_request(self, request: str):
        # Run through Covenant first
        result = self.covenant.evaluate_request(request)
        if result.rejected:
            return self.mirror.reflect(result.reason)
        
        # Parse intent
        intent = self.parse_intent(request)
        
        # Generate geometry
        geometry = self.cad.create_geometry(intent)
        
        # Validate
        validation = self.validate(geometry)
        
        if validation.passed:
            return self.cad.export_stl(geometry)
        else:
            # Iterate or report failure
            return self.iterate_or_fail(validation)
```

---

*Authored by: Antigravity*
*For the LEF Seed Ecosystem*
