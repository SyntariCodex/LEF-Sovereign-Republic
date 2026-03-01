#!/usr/bin/env python3
"""
LLM Intent Parser — Fabrication Seed

Converts natural language design requests into structured constraints
using Claude/GPT with structured output.

This replaces the regex-based parser with proper LLM understanding.
"""

import os
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any

# Import the base constraints
from fabrication_seed import DesignConstraints


# Schema for structured output
CONSTRAINT_SCHEMA = {
    "type": "object",
    "properties": {
        "object_type": {
            "type": "string",
            "enum": ["box", "cube", "cylinder", "phone_stand", "bracket", "hook", "custom"],
            "description": "The type of object to create"
        },
        "dimensions": {
            "type": "object",
            "properties": {
                "width": {"type": "number", "description": "Width in mm"},
                "depth": {"type": "number", "description": "Depth in mm"},
                "height": {"type": "number", "description": "Height in mm"},
                "diameter": {"type": "number", "description": "Diameter in mm (for cylinders)"},
                "radius": {"type": "number", "description": "Radius in mm"},
                "thickness": {"type": "number", "description": "Wall thickness in mm"}
            },
            "description": "Dimensional constraints in millimeters"
        },
        "features": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["hole", "slot", "chamfer", "fillet", "hollow", "pattern"]
                    },
                    "parameters": {
                        "type": "object"
                    }
                }
            },
            "description": "Additional features to add to the base shape"
        },
        "material": {
            "type": "string",
            "enum": ["PLA", "PETG", "ABS", "TPU", "resin", "metal", "wood"],
            "description": "Intended material for fabrication"
        },
        "purpose": {
            "type": "string",
            "description": "What the object is for (helps with design decisions)"
        },
        "constraints": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Additional constraints (e.g., 'must fit in pocket', 'needs to hold 5kg')"
        }
    },
    "required": ["object_type", "dimensions"]
}


class LLMIntentParser:
    """
    Parse design intent using LLM with structured output.
    
    Supports multiple LLM backends:
    - Claude (Anthropic)
    - GPT-4 (OpenAI)
    - Local (Ollama)
    """
    
    SYSTEM_PROMPT = """You are a CAD design intent parser. Your job is to extract 
structured design constraints from natural language requests.

When parsing a request:
1. Identify the object type (box, cylinder, bracket, etc.)
2. Extract all dimensional constraints (in millimeters)
3. Note any features (holes, fillets, chamfers)
4. Infer reasonable defaults for missing dimensions
5. Capture the purpose to inform design decisions

Always think about what the user actually needs, not just what they said.

Examples:
- "Make a phone holder" → phone_stand, ~80x60x10mm base + ~100mm back rest
- "I need a 2 inch cube" → cube, 50.8x50.8x50.8mm (converted from inches)
- "Box to hold small screws" → box, ~50x50x30mm, hollow with ~2mm walls

Return ONLY valid JSON matching the schema."""

    def __init__(self, backend: str = "claude", api_key: str = None):
        """
        Initialize parser with LLM backend.
        
        Args:
            backend: "claude", "openai", or "ollama"
            api_key: API key (or from environment)
        """
        self.backend = backend
        
        if backend == "claude":
            self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
            self._parse = self._parse_claude
        elif backend == "openai":
            self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
            self._parse = self._parse_openai
        elif backend == "ollama":
            self.api_key = None  # Local
            self._parse = self._parse_ollama
        else:
            # Fallback to simple parser
            self._parse = self._parse_simple
    
    def parse(self, request: str) -> DesignConstraints:
        """
        Parse natural language request into constraints.
        
        Args:
            request: Natural language design request
            
        Returns:
            DesignConstraints ready for geometry engine
        """
        try:
            result = self._parse(request)
            return self._result_to_constraints(result)
        except Exception as e:
            print(f"[PARSER] LLM parse failed, using fallback: {e}")
            return self._parse_simple(request)
    
    def _parse_claude(self, request: str) -> Dict:
        """Parse using Claude API."""
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package required: pip install anthropic")
        
        client = anthropic.Anthropic(api_key=self.api_key)
        
        from system.llm_router import call_with_timeout
        response = call_with_timeout(
            client.messages.create,
            timeout_seconds=120,
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=self.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"Parse this design request:\n\n{request}"}
            ]
        )

        # Extract JSON from response
        text = response.content[0].text if response else None
        if not text:
            return {}
        return self._extract_json(text)
    
    def _parse_openai(self, request: str) -> Dict:
        """Parse using OpenAI API with structured output."""
        try:
            import openai
        except ImportError:
            raise ImportError("openai package required: pip install openai")
        
        client = openai.OpenAI(api_key=self.api_key)
        
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Parse this design request:\n\n{request}"}
            ],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _parse_ollama(self, request: str) -> Dict:
        """Parse using local Ollama."""
        import requests
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama2",  # Or your preferred model
                "prompt": f"{self.SYSTEM_PROMPT}\n\nParse this request:\n{request}",
                "stream": False,
                "format": "json"
            }
        )
        
        result = response.json()
        return json.loads(result.get("response", "{}"))
    
    def _parse_simple(self, request: str) -> Dict:
        """Fallback simple parser (regex-based)."""
        from fabrication_seed import IntentParser
        parser = IntentParser()
        constraints = parser.parse(request)
        
        return {
            "object_type": constraints.object_type,
            "dimensions": constraints.dimensions,
            "features": [{"type": f} for f in constraints.features],
            "material": constraints.material
        }
    
    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from LLM response text."""
        # Try to find JSON in response
        import re
        
        # Look for JSON block
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group())
        
        raise ValueError("No JSON found in response")
    
    def _result_to_constraints(self, result: Dict) -> DesignConstraints:
        """Convert parsed result to DesignConstraints."""
        return DesignConstraints(
            object_type=result.get("object_type", "box"),
            dimensions=result.get("dimensions", {"width": 50, "depth": 50, "height": 50}),
            features=[f.get("type", "") for f in result.get("features", [])],
            material=result.get("material", "PLA"),
            description=result.get("purpose", "")
        )


class DesignReasoner:
    """
    Adds reasoning layer on top of constraints.
    
    Uses LLM to make design decisions:
    - Fill in missing dimensions with reasonable defaults
    - Suggest features based on purpose
    - Warn about potential issues
    """
    
    def __init__(self, backend: str = "claude", api_key: str = None):
        self.backend = backend
        self.api_key = api_key
    
    def enhance_constraints(self, constraints: DesignConstraints) -> DesignConstraints:
        """
        Enhance constraints with reasoning.
        
        Fills in missing values and adds suggestions.
        """
        # For now, just apply defaults
        dims = constraints.dimensions
        
        # Ensure we have all dimensions
        if "width" not in dims:
            dims["width"] = dims.get("diameter", 50)
        if "depth" not in dims:
            dims["depth"] = dims.get("diameter", dims["width"])
        if "height" not in dims:
            dims["height"] = 50  # Default height
        
        constraints.dimensions = dims
        return constraints


# ==================== Demo ====================

def demo():
    """Demonstrate LLM intent parsing."""
    print("=" * 60)
    print("LLM INTENT PARSER DEMO")
    print("=" * 60)
    
    # Use simple parser for demo (no API keys needed)
    parser = LLMIntentParser(backend="simple")
    
    test_requests = [
        "Make me a 50mm cube",
        "I need a phone holder for my desk",
        "Create a cylinder with diameter 30mm and height 100mm",
        "Design a small box to hold screws, about 60x40x30mm",
    ]
    
    for request in test_requests:
        print(f"\nRequest: {request}")
        constraints = parser.parse(request)
        print(f"  Type: {constraints.object_type}")
        print(f"  Dimensions: {constraints.dimensions}")
        print(f"  Features: {constraints.features}")


if __name__ == "__main__":
    demo()
