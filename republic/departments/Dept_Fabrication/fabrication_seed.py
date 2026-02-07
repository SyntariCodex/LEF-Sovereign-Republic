#!/usr/bin/env python3
"""
Fabrication Seed — Minimal Prototype
Conversation → Geometry → STL

This prototype demonstrates the core loop:
1. Parse natural language into design constraints
2. Generate 3D geometry from constraints
3. Export as STL for fabrication

Uses: numpy-stl for geometry generation (no CAD software required)
"""

import json
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# For STL generation without CAD software
try:
    import numpy as np
    from stl import mesh
    HAS_STL = True
except ImportError:
    HAS_STL = False
    print("[WARN] numpy-stl not installed. Run: pip install numpy-stl numpy")


@dataclass
class DesignConstraints:
    """Parsed design constraints from natural language."""
    object_type: str  # "box", "cylinder", "phone_stand", etc.
    dimensions: Dict[str, float] = field(default_factory=dict)  # mm
    features: List[str] = field(default_factory=list)
    material: str = "PLA"
    description: str = ""


class IntentParser:
    """
    Parse natural language design requests into structured constraints.
    
    Prototype: Simple pattern matching.
    Production: LLM with structured output.
    """
    
    # Patterns for dimension extraction
    DIMENSION_PATTERNS = [
        r'(\d+(?:\.\d+)?)\s*(?:mm|millimeter)',
        r'(\d+(?:\.\d+)?)\s*(?:cm|centimeter)',
        r'(\d+(?:\.\d+)?)\s*(?:inch|in|")',
        r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)',
    ]
    
    # Object type keywords
    OBJECT_TYPES = {
        "cube": ["cube", "box", "block"],
        "cylinder": ["cylinder", "tube", "pipe", "rod"],
        "phone_stand": ["phone stand", "phone holder", "phone dock"],
        "hook": ["hook", "hanger"],
        "bracket": ["bracket", "mount", "holder"],
    }
    
    def parse(self, request: str) -> DesignConstraints:
        """Parse natural language into constraints."""
        request_lower = request.lower()
        
        # Detect object type
        object_type = "box"  # default
        for obj_type, keywords in self.OBJECT_TYPES.items():
            for keyword in keywords:
                if keyword in request_lower:
                    object_type = obj_type
                    break
        
        # Extract dimensions
        dimensions = self._extract_dimensions(request)
        
        # Extract features
        features = self._extract_features(request_lower)
        
        return DesignConstraints(
            object_type=object_type,
            dimensions=dimensions,
            features=features,
            description=request
        )
    
    def _extract_dimensions(self, text: str) -> Dict[str, float]:
        """Extract dimensions from text."""
        dimensions = {}
        
        # Look for explicit dimension patterns
        # Pattern: NxNxN (e.g., "50x30x20mm")
        xyz_match = re.search(r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)', text)
        if xyz_match:
            dimensions["width"] = float(xyz_match.group(1))
            dimensions["depth"] = float(xyz_match.group(2))
            dimensions["height"] = float(xyz_match.group(3))
            return dimensions
        
        # Pattern: "50mm cube"
        cube_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:mm|cm)?\s*cube', text.lower())
        if cube_match:
            size = float(cube_match.group(1))
            dimensions["width"] = size
            dimensions["depth"] = size
            dimensions["height"] = size
            return dimensions
        
        # Pattern: diameter and height for cylinder
        diam_match = re.search(r'(?:diameter|diam|d)\s*[:=]?\s*(\d+(?:\.\d+)?)', text.lower())
        height_match = re.search(r'(?:height|h|tall)\s*[:=]?\s*(\d+(?:\.\d+)?)', text.lower())
        
        if diam_match:
            dimensions["diameter"] = float(diam_match.group(1))
        if height_match:
            dimensions["height"] = float(height_match.group(1))
        
        # Default dimensions if none found
        if not dimensions:
            dimensions = {"width": 50, "depth": 50, "height": 50}
        
        return dimensions
    
    def _extract_features(self, text: str) -> List[str]:
        """Extract feature keywords."""
        features = []
        feature_keywords = ["hole", "slot", "chamfer", "fillet", "rounded", "hollow"]
        for keyword in feature_keywords:
            if keyword in text:
                features.append(keyword)
        return features


class GeometryEngine:
    """
    Generate 3D geometry from constraints.
    
    Prototype: Direct mesh generation with numpy-stl.
    Production: CAD API (Onshape/Fusion 360).
    """
    
    def generate(self, constraints: DesignConstraints) -> Optional[object]:
        """Generate mesh from constraints."""
        if not HAS_STL:
            print("[ERROR] numpy-stl required for geometry generation")
            return None
        
        if constraints.object_type == "cube" or constraints.object_type == "box":
            return self._create_box(constraints.dimensions)
        elif constraints.object_type == "cylinder":
            return self._create_cylinder(constraints.dimensions)
        elif constraints.object_type == "phone_stand":
            return self._create_phone_stand(constraints.dimensions)
        else:
            # Default to box
            return self._create_box(constraints.dimensions)
    
    def _create_box(self, dims: Dict[str, float]) -> mesh.Mesh:
        """Create a box mesh."""
        w = dims.get("width", 50)
        d = dims.get("depth", 50)
        h = dims.get("height", 50)
        
        # Define the 8 vertices of a box
        vertices = np.array([
            [0, 0, 0],      # 0
            [w, 0, 0],      # 1
            [w, d, 0],      # 2
            [0, d, 0],      # 3
            [0, 0, h],      # 4
            [w, 0, h],      # 5
            [w, d, h],      # 6
            [0, d, h],      # 7
        ])
        
        # Define the 12 triangles (2 per face)
        faces = np.array([
            [0, 3, 1], [1, 3, 2],  # bottom
            [0, 4, 7], [0, 7, 3],  # left
            [4, 5, 6], [4, 6, 7],  # top
            [5, 1, 2], [5, 2, 6],  # right
            [2, 3, 6], [3, 7, 6],  # back
            [0, 1, 5], [0, 5, 4],  # front
        ])
        
        # Create the mesh
        box = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
        for i, f in enumerate(faces):
            for j in range(3):
                box.vectors[i][j] = vertices[f[j], :]
        
        return box
    
    def _create_cylinder(self, dims: Dict[str, float], segments: int = 32) -> mesh.Mesh:
        """Create a cylinder mesh."""
        radius = dims.get("diameter", 30) / 2
        if "radius" in dims:
            radius = dims["radius"]
        height = dims.get("height", 50)
        
        # Create vertices
        vertices = []
        
        # Bottom center
        vertices.append([0, 0, 0])
        # Top center
        vertices.append([0, 0, height])
        
        # Bottom ring
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            vertices.append([x, y, 0])
        
        # Top ring
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            vertices.append([x, y, height])
        
        vertices = np.array(vertices)
        
        # Create faces
        faces = []
        
        # Bottom cap
        for i in range(segments):
            next_i = (i + 1) % segments
            faces.append([0, 2 + i, 2 + next_i])
        
        # Top cap
        for i in range(segments):
            next_i = (i + 1) % segments
            faces.append([1, 2 + segments + next_i, 2 + segments + i])
        
        # Side faces
        for i in range(segments):
            next_i = (i + 1) % segments
            bottom_curr = 2 + i
            bottom_next = 2 + next_i
            top_curr = 2 + segments + i
            top_next = 2 + segments + next_i
            faces.append([bottom_curr, bottom_next, top_curr])
            faces.append([bottom_next, top_next, top_curr])
        
        faces = np.array(faces)
        
        # Create mesh
        cylinder = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
        for i, f in enumerate(faces):
            for j in range(3):
                cylinder.vectors[i][j] = vertices[f[j], :]
        
        return cylinder
    
    def _create_phone_stand(self, dims: Dict[str, float]) -> mesh.Mesh:
        """Create a simple phone stand (L-shaped bracket)."""
        width = dims.get("width", 80)
        depth = dims.get("depth", 60)
        height = dims.get("height", 100)
        thickness = dims.get("thickness", 10)
        
        # Phone stand = base + back rest (two boxes combined)
        # For simplicity, create just the base for now
        base_dims = {"width": width, "depth": depth, "height": thickness}
        return self._create_box(base_dims)


class FabricationExporter:
    """Export geometry to fabrication-ready formats."""
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path.home() / "fabrication_output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_stl(self, geometry: mesh.Mesh, name: str) -> Path:
        """Export geometry as STL file."""
        filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.stl"
        filepath = self.output_dir / filename
        geometry.save(str(filepath))
        return filepath


class FabricationSeed:
    """
    The Fabrication Seed: Conversation → Geometry → Fabrication
    
    A minimal prototype demonstrating the core loop.
    """
    
    def __init__(self, output_dir: Path = None):
        self.parser = IntentParser()
        self.engine = GeometryEngine()
        self.exporter = FabricationExporter(output_dir)
        
        # Track what we've made
        self.history: List[Dict] = []
    
    def fabricate(self, request: str) -> Dict:
        """
        Main entry point: natural language → STL file
        
        Returns dict with result details.
        """
        result = {
            "request": request,
            "timestamp": datetime.now().isoformat(),
            "success": False
        }
        
        # Step 1: Parse intent
        try:
            constraints = self.parser.parse(request)
            result["constraints"] = {
                "object_type": constraints.object_type,
                "dimensions": constraints.dimensions,
                "features": constraints.features
            }
        except Exception as e:
            result["error"] = f"Intent parsing failed: {e}"
            return result
        
        # Step 2: Generate geometry
        try:
            geometry = self.engine.generate(constraints)
            if geometry is None:
                result["error"] = "Geometry generation failed"
                return result
            result["geometry_generated"] = True
        except Exception as e:
            result["error"] = f"Geometry generation failed: {e}"
            return result
        
        # Step 3: Export
        try:
            # Generate name from request
            name = re.sub(r'[^a-z0-9]+', '_', request.lower())[:30]
            filepath = self.exporter.export_stl(geometry, name)
            result["stl_path"] = str(filepath)
            result["success"] = True
        except Exception as e:
            result["error"] = f"Export failed: {e}"
            return result
        
        self.history.append(result)
        return result


# ============================================================
# CLI Interface
# ============================================================

def main():
    """Interactive CLI for the Fabrication Seed prototype."""
    print("=" * 60)
    print("FABRICATION SEED — Prototype v0.1")
    print("Conversation → Geometry → STL")
    print("=" * 60)
    print()
    
    if not HAS_STL:
        print("ERROR: numpy-stl required. Install with:")
        print("  pip install numpy-stl numpy")
        return
    
    seed = FabricationSeed()
    
    print("Enter design requests (or 'quit' to exit):")
    print()
    print("Examples:")
    print("  - Make a 50mm cube")
    print("  - I need a cylinder, diameter 30mm, height 100mm")
    print("  - Create a 80x60x10mm box")
    print()
    
    while True:
        try:
            request = input("Design> ").strip()
            if not request:
                continue
            if request.lower() in ["quit", "exit", "q"]:
                break
            
            print(f"\nProcessing: {request}")
            result = seed.fabricate(request)
            
            if result["success"]:
                print(f"✅ Success!")
                print(f"   Type: {result['constraints']['object_type']}")
                print(f"   Dimensions: {result['constraints']['dimensions']}")
                print(f"   STL: {result['stl_path']}")
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")
            
            print()
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
