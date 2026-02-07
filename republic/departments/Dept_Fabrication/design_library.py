#!/usr/bin/env python3
"""
Example Designs Library — Fabrication Seed

A library of pre-validated design templates that demonstrate
the Seed's capabilities and serve as starting points.

Each template includes:
- Natural language description
- Expected constraints
- Geometry function
- Validation requirements
"""

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional
from pathlib import Path
import json

try:
    import numpy as np
    from stl import mesh
    HAS_STL = True
except ImportError:
    HAS_STL = False


@dataclass
class DesignTemplate:
    """A reusable design template."""
    name: str
    category: str
    description: str
    default_dimensions: Dict[str, float]
    parameters: List[str]  # What can be customized
    difficulty: str  # "basic", "intermediate", "advanced"
    geometry_func: Optional[Callable] = None
    tags: List[str] = field(default_factory=list)


class DesignLibrary:
    """
    Library of design templates.
    
    Provides:
    - Pre-built templates for common objects
    - Searchable by category and tags
    - Example usage for documentation
    """
    
    def __init__(self):
        self.templates: Dict[str, DesignTemplate] = {}
        self._load_builtin_templates()
    
    def _load_builtin_templates(self):
        """Load built-in design templates."""
        
        # ==================== Basic Shapes ====================
        
        self.templates["basic_cube"] = DesignTemplate(
            name="Basic Cube",
            category="primitives",
            description="A simple cube with equal sides",
            default_dimensions={"size": 50},
            parameters=["size"],
            difficulty="basic",
            tags=["cube", "box", "simple", "beginner"]
        )
        
        self.templates["parametric_box"] = DesignTemplate(
            name="Parametric Box",
            category="primitives",
            description="A box with customizable width, depth, and height",
            default_dimensions={"width": 50, "depth": 30, "height": 20},
            parameters=["width", "depth", "height"],
            difficulty="basic",
            tags=["box", "rectangular", "container"]
        )
        
        self.templates["cylinder"] = DesignTemplate(
            name="Cylinder",
            category="primitives",
            description="A cylinder with customizable diameter and height",
            default_dimensions={"diameter": 30, "height": 50},
            parameters=["diameter", "height"],
            difficulty="basic",
            tags=["cylinder", "round", "tube"]
        )
        
        # ==================== Desk Accessories ====================
        
        self.templates["phone_stand"] = DesignTemplate(
            name="Phone Stand",
            category="desk_accessories",
            description="A simple phone stand with adjustable angle",
            default_dimensions={
                "base_width": 80,
                "base_depth": 60,
                "base_height": 10,
                "back_height": 100,
                "back_thickness": 8,
                "angle": 70
            },
            parameters=["base_width", "back_height", "angle"],
            difficulty="intermediate",
            tags=["phone", "stand", "holder", "desk", "mobile"]
        )
        
        self.templates["pen_holder"] = DesignTemplate(
            name="Pen Holder",
            category="desk_accessories",
            description="Cylindrical pen holder with multiple compartments",
            default_dimensions={
                "outer_diameter": 80,
                "height": 100,
                "wall_thickness": 3,
                "compartments": 1
            },
            parameters=["outer_diameter", "height", "compartments"],
            difficulty="intermediate",
            tags=["pen", "pencil", "holder", "desk", "office"]
        )
        
        self.templates["cable_clip"] = DesignTemplate(
            name="Cable Clip",
            category="desk_accessories",
            description="Clip to organize cables on desk edge",
            default_dimensions={
                "width": 20,
                "length": 30,
                "cable_diameter": 5,
                "desk_thickness": 20
            },
            parameters=["cable_diameter", "desk_thickness"],
            difficulty="intermediate",
            tags=["cable", "clip", "organizer", "desk"]
        )
        
        # ==================== Hardware ====================
        
        self.templates["mounting_bracket"] = DesignTemplate(
            name="L-Bracket",
            category="hardware",
            description="L-shaped mounting bracket with screw holes",
            default_dimensions={
                "width": 40,
                "leg1_length": 50,
                "leg2_length": 50,
                "thickness": 5,
                "hole_diameter": 4
            },
            parameters=["width", "leg1_length", "leg2_length", "hole_diameter"],
            difficulty="intermediate",
            tags=["bracket", "mount", "L-bracket", "hardware"]
        )
        
        self.templates["hook"] = DesignTemplate(
            name="Wall Hook",
            category="hardware",
            description="Simple wall hook for hanging items",
            default_dimensions={
                "hook_diameter": 25,
                "hook_thickness": 8,
                "plate_width": 30,
                "plate_height": 40,
                "plate_thickness": 4
            },
            parameters=["hook_diameter", "plate_width"],
            difficulty="intermediate",
            tags=["hook", "wall", "hanger", "hardware"]
        )
        
        self.templates["spacer"] = DesignTemplate(
            name="Spacer/Washer",
            category="hardware",
            description="Simple spacer or washer with center hole",
            default_dimensions={
                "outer_diameter": 20,
                "inner_diameter": 8,
                "thickness": 3
            },
            parameters=["outer_diameter", "inner_diameter", "thickness"],
            difficulty="basic",
            tags=["spacer", "washer", "hardware", "shim"]
        )
        
        # ==================== Containers ====================
        
        self.templates["storage_box"] = DesignTemplate(
            name="Storage Box",
            category="containers",
            description="Open-top box for storage with customizable compartments",
            default_dimensions={
                "width": 100,
                "depth": 80,
                "height": 50,
                "wall_thickness": 2,
                "compartments_x": 1,
                "compartments_y": 1
            },
            parameters=["width", "depth", "height", "compartments_x", "compartments_y"],
            difficulty="intermediate",
            tags=["box", "container", "storage", "organizer"]
        )
        
        self.templates["screw_tray"] = DesignTemplate(
            name="Screw Sorting Tray",
            category="containers",
            description="Tray with multiple compartments for sorting small parts",
            default_dimensions={
                "width": 150,
                "depth": 100,
                "height": 25,
                "rows": 2,
                "columns": 4,
                "wall_thickness": 2
            },
            parameters=["width", "depth", "rows", "columns"],
            difficulty="intermediate",
            tags=["tray", "organizer", "screws", "parts", "sorting"]
        )
        
        # ==================== Advanced ====================
        
        self.templates["gear"] = DesignTemplate(
            name="Spur Gear",
            category="mechanical",
            description="Simple spur gear with customizable teeth",
            default_dimensions={
                "pitch_diameter": 50,
                "teeth": 20,
                "thickness": 10,
                "shaft_diameter": 8
            },
            parameters=["pitch_diameter", "teeth", "shaft_diameter"],
            difficulty="advanced",
            tags=["gear", "mechanical", "spur", "teeth"]
        )
        
        self.templates["threaded_cap"] = DesignTemplate(
            name="Threaded Cap",
            category="mechanical",
            description="Cap with threads for containers or tubes",
            default_dimensions={
                "outer_diameter": 40,
                "inner_diameter": 35,
                "height": 15,
                "thread_pitch": 2,
                "thread_depth": 1
            },
            parameters=["outer_diameter", "inner_diameter", "thread_pitch"],
            difficulty="advanced",
            tags=["cap", "thread", "lid", "container"]
        )
    
    def get_template(self, name: str) -> Optional[DesignTemplate]:
        """Get a template by name."""
        return self.templates.get(name)
    
    def search(self, query: str = "", category: str = None, 
               difficulty: str = None) -> List[DesignTemplate]:
        """
        Search templates.
        
        Args:
            query: Search in name, description, tags
            category: Filter by category
            difficulty: Filter by difficulty
        """
        results = list(self.templates.values())
        
        if category:
            results = [t for t in results if t.category == category]
        
        if difficulty:
            results = [t for t in results if t.difficulty == difficulty]
        
        if query:
            query_lower = query.lower()
            results = [
                t for t in results
                if query_lower in t.name.lower() or
                   query_lower in t.description.lower() or
                   any(query_lower in tag for tag in t.tags)
            ]
        
        return results
    
    def list_categories(self) -> List[str]:
        """List all categories."""
        return list(set(t.category for t in self.templates.values()))
    
    def get_by_category(self, category: str) -> List[DesignTemplate]:
        """Get all templates in a category."""
        return [t for t in self.templates.values() if t.category == category]
    
    def export_catalog(self, path: Path) -> None:
        """Export catalog as JSON."""
        catalog = {
            name: {
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "default_dimensions": t.default_dimensions,
                "parameters": t.parameters,
                "difficulty": t.difficulty,
                "tags": t.tags
            }
            for name, t in self.templates.items()
        }
        
        with open(path, 'w') as f:
            json.dump(catalog, f, indent=2)


# ==================== Example Usage Strings ====================

USAGE_EXAMPLES = """
# Fabrication Seed — Example Usage

## Basic Requests (Free-form)

"Make me a 50mm cube"
"I need a phone holder for my desk"
"Create a box 80x60x30mm"
"Design a cylinder with diameter 40mm and height 100mm"

## Template-Based Requests

"Use the phone_stand template with back_height=120mm"
"Create a storage_box: 150x100x60mm with 2x3 compartments"
"Make a mounting_bracket with 60mm legs"

## Constrained Requests

"Design a pen holder that's no taller than 80mm"
"Create a cable clip for 8mm cables and 25mm desk"
"Make a spacer: outer 25mm, inner 10mm, 5mm thick"

## Advanced Requests

"Generate a spur gear with 24 teeth, 8mm shaft"
"Create a threaded cap for a 40mm container"

## Materials (Informational)

"Make a phone stand in PETG for outdoor use"
"Design a flexible cable organizer in TPU"
"Create a bracket that needs to be strong — use ABS"
"""


# ==================== Demo ====================

def demo():
    """Demonstrate the design library."""
    print("=" * 60)
    print("DESIGN LIBRARY DEMO")
    print("=" * 60)
    
    library = DesignLibrary()
    
    # List categories
    print("\nCategories:")
    for cat in library.list_categories():
        templates = library.get_by_category(cat)
        print(f"  {cat}: {len(templates)} templates")
    
    # Search examples
    print("\nSearch 'desk':")
    for t in library.search("desk"):
        print(f"  - {t.name}: {t.description}")
    
    print("\nSearch 'holder':")
    for t in library.search("holder"):
        print(f"  - {t.name}")
    
    # Get specific template
    print("\nPhone Stand template:")
    phone = library.get_template("phone_stand")
    if phone:
        print(f"  Name: {phone.name}")
        print(f"  Default dimensions: {phone.default_dimensions}")
        print(f"  Customizable: {phone.parameters}")
    
    # Export catalog
    catalog_path = Path("/tmp/fabrication_catalog.json")
    library.export_catalog(catalog_path)
    print(f"\nCatalog exported to: {catalog_path}")


if __name__ == "__main__":
    demo()
