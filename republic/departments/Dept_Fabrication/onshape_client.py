#!/usr/bin/env python3
"""
Onshape API Client — Fabrication Seed Integration

This module provides the scaffold for connecting the Fabrication Seed
to Onshape's REST API for real CAD geometry creation.

Requirements:
  pip install requests

Setup:
  1. Create account at onshape.com
  2. Go to Developer Portal: https://dev-portal.onshape.com/
  3. Create API Keys (enable read + write)
  4. Set environment variables:
     - ONSHAPE_ACCESS_KEY
     - ONSHAPE_SECRET_KEY
"""

import os
import json
import hashlib
import hmac
import base64
import datetime
import random
import string
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from urllib.parse import urlencode, urlparse

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# Onshape API endpoints
ONSHAPE_BASE_URL = "https://cad.onshape.com/api/v6"


@dataclass
class OnshapeCredentials:
    """Onshape API credentials."""
    access_key: str
    secret_key: str
    
    @classmethod
    def from_env(cls) -> Optional['OnshapeCredentials']:
        """Load credentials from environment variables."""
        access = os.environ.get('ONSHAPE_ACCESS_KEY')
        secret = os.environ.get('ONSHAPE_SECRET_KEY')
        if access and secret:
            return cls(access_key=access, secret_key=secret)
        return None


@dataclass
class OnshapeDocument:
    """Reference to an Onshape document."""
    document_id: str
    workspace_id: str
    element_id: Optional[str] = None
    name: str = ""


class OnshapeClient:
    """
    Onshape REST API client for programmatic CAD.
    
    This is a scaffold — actual API calls need credentials to test.
    
    Usage:
        client = OnshapeClient()
        
        # Create a new document
        doc = client.create_document("My Design")
        
        # Create a Part Studio
        element = client.create_part_studio(doc, "Main Part")
        
        # Add geometry via FeatureScript
        client.add_feature(doc, element, sketch_feature)
        
        # Export STL
        stl_data = client.export_stl(doc, element)
    """
    
    def __init__(self, credentials: OnshapeCredentials = None):
        if not HAS_REQUESTS:
            raise ImportError("requests library required: pip install requests")
        
        self.credentials = credentials or OnshapeCredentials.from_env()
        self.base_url = ONSHAPE_BASE_URL
        self.session = requests.Session()
    
    def _generate_nonce(self) -> str:
        """Generate random nonce for request signing."""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=25))
    
    def _sign_request(self, method: str, path: str, query: str, 
                      content_type: str, date: str, nonce: str) -> str:
        """
        Generate HMAC signature for Onshape API authentication.
        
        The signature string format:
        method + '\n' + nonce + '\n' + date + '\n' + content_type + '\n' + 
        path + '\n' + query + '\n'
        """
        if not self.credentials:
            raise ValueError("No credentials configured")
        
        # Build signature string
        sig_string = (
            method.lower() + '\n' +
            nonce + '\n' +
            date + '\n' +
            content_type + '\n' +
            path + '\n' +
            query + '\n'
        )
        
        # HMAC-SHA256
        signature = hmac.new(
            self.credentials.secret_key.encode('utf-8'),
            sig_string.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    
    def _request(self, method: str, endpoint: str, 
                 params: Dict = None, data: Dict = None) -> Dict:
        """Make authenticated request to Onshape API."""
        if not self.credentials:
            return {"error": "No credentials configured", "mock": True}
        
        # Build URL
        url = f"{self.base_url}{endpoint}"
        query_string = urlencode(params) if params else ""
        
        # Generate auth headers
        date = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        nonce = self._generate_nonce()
        content_type = 'application/json'
        
        path = urlparse(url).path
        signature = self._sign_request(method, path, query_string, 
                                       content_type, date, nonce)
        
        headers = {
            'Content-Type': content_type,
            'Date': date,
            'On-Nonce': nonce,
            'Authorization': f'On {self.credentials.access_key}:HmacSHA256:{signature}'
        }
        
        # Make request
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    # ==================== Document Operations ====================
    
    def create_document(self, name: str, description: str = "") -> Optional[OnshapeDocument]:
        """
        Create a new Onshape document.
        
        Args:
            name: Document name
            description: Optional description
            
        Returns:
            OnshapeDocument with IDs for further operations
        """
        data = {
            "name": name,
            "description": description,
            "isPublic": False
        }
        
        result = self._request("POST", "/documents", data=data)
        
        if "error" in result:
            print(f"[ONSHAPE] Create document failed: {result['error']}")
            return None
        
        return OnshapeDocument(
            document_id=result.get('id', ''),
            workspace_id=result.get('defaultWorkspace', {}).get('id', ''),
            name=name
        )
    
    def create_part_studio(self, doc: OnshapeDocument, name: str = "Part Studio") -> Optional[str]:
        """
        Create a new Part Studio in a document.
        
        Returns:
            Element ID of the new Part Studio
        """
        endpoint = f"/partstudios/d/{doc.document_id}/w/{doc.workspace_id}"
        data = {"name": name}
        
        result = self._request("POST", endpoint, data=data)
        
        if "error" in result:
            print(f"[ONSHAPE] Create Part Studio failed: {result['error']}")
            return None
        
        return result.get('id')
    
    # ==================== Geometry Operations ====================
    
    def add_feature(self, doc: OnshapeDocument, element_id: str, 
                    feature: Dict) -> bool:
        """
        Add a feature to a Part Studio.
        
        Features are defined in FeatureScript format.
        
        Args:
            doc: Document reference
            element_id: Part Studio element ID
            feature: FeatureScript feature definition
            
        Returns:
            Success boolean
        """
        endpoint = f"/partstudios/d/{doc.document_id}/w/{doc.workspace_id}/e/{element_id}/features"
        
        result = self._request("POST", endpoint, data=feature)
        return "error" not in result
    
    def add_sketch(self, doc: OnshapeDocument, element_id: str,
                   plane: str = "TOP", entities: List[Dict] = None) -> bool:
        """
        Add a sketch to a Part Studio.
        
        Args:
            doc: Document reference
            element_id: Part Studio element ID
            plane: "TOP", "FRONT", "RIGHT", or a face reference
            entities: List of sketch entities (lines, circles, etc.)
        """
        feature = {
            "btType": "BTFeatureDefinitionCall-1406",
            "feature": {
                "btType": "BTMSketch-151",
                "featureType": "newSketch",
                "name": "Sketch",
                "parameters": [
                    {
                        "btType": "BTMParameterQueryList-148",
                        "parameterId": "sketchPlane",
                        "queries": [
                            {
                                "btType": "BTMFeatureQueryWithOccurrence-157",
                                "path": plane
                            }
                        ]
                    }
                ],
                "entities": entities or []
            }
        }
        
        return self.add_feature(doc, element_id, feature)
    
    def add_extrude(self, doc: OnshapeDocument, element_id: str,
                    sketch_id: str, depth: float) -> bool:
        """
        Add an extrude feature.
        
        Args:
            doc: Document reference
            element_id: Part Studio element ID
            sketch_id: ID of sketch to extrude
            depth: Extrusion depth in meters
        """
        feature = {
            "btType": "BTFeatureDefinitionCall-1406",
            "feature": {
                "btType": "BTMFeature-134",
                "featureType": "extrude",
                "name": "Extrude",
                "parameters": [
                    {
                        "btType": "BTMParameterQueryList-148",
                        "parameterId": "entities",
                        "queries": [
                            {
                                "btType": "BTMFeatureQueryWithOccurrence-157",
                                "path": f"query::sketchRegion(id + \"{sketch_id}\", false)"
                            }
                        ]
                    },
                    {
                        "btType": "BTMParameterQuantity-147",
                        "parameterId": "depth",
                        "expression": f"{depth} meter"
                    }
                ]
            }
        }
        
        return self.add_feature(doc, element_id, feature)
    
    # ==================== Export Operations ====================
    
    def export_stl(self, doc: OnshapeDocument, element_id: str,
                   part_id: str = None, units: str = "millimeter") -> Optional[bytes]:
        """
        Export Part Studio as STL.
        
        Args:
            doc: Document reference
            element_id: Part Studio element ID
            part_id: Specific part to export (or all)
            units: "millimeter", "centimeter", "meter", "inch"
            
        Returns:
            STL file bytes
        """
        endpoint = f"/partstudios/d/{doc.document_id}/w/{doc.workspace_id}/e/{element_id}/stl"
        
        params = {
            "units": units,
            "angleTolerance": 0.1,
            "chordTolerance": 0.01
        }
        
        if part_id:
            params["partId"] = part_id
        
        # For STL export, we need raw bytes response
        if not self.credentials:
            print("[ONSHAPE] Mock mode: would export STL here")
            return None
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"[ONSHAPE] Export failed: {e}")
            return None
    
    def export_step(self, doc: OnshapeDocument, element_id: str) -> Optional[bytes]:
        """Export Part Studio as STEP file."""
        endpoint = f"/partstudios/d/{doc.document_id}/w/{doc.workspace_id}/e/{element_id}/step"
        
        if not self.credentials:
            print("[ONSHAPE] Mock mode: would export STEP here")
            return None
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"[ONSHAPE] Export failed: {e}")
            return None


# ==================== High-Level Design Functions ====================

def create_box(client: OnshapeClient, name: str, 
               width: float, depth: float, height: float) -> Optional[OnshapeDocument]:
    """
    Create a simple box in Onshape.
    
    High-level function that handles the full workflow:
    1. Create document
    2. Create Part Studio
    3. Add sketch
    4. Add extrude
    
    Args:
        client: Onshape client
        name: Document name
        width, depth, height: Dimensions in mm
        
    Returns:
        Document reference for export
    """
    # Create document
    doc = client.create_document(name)
    if not doc:
        return None
    
    # Create Part Studio
    element_id = client.create_part_studio(doc, "Box")
    if not element_id:
        return None
    
    # Create sketch with rectangle
    # Note: Onshape uses meters internally
    w_m = width / 1000
    d_m = depth / 1000
    h_m = height / 1000
    
    rectangle_entities = [
        {
            "btType": "BTMSketchCurveSegment-155",
            "startPoint": {"btType": "BTVector2d-1538", "x": 0, "y": 0},
            "endPoint": {"btType": "BTVector2d-1538", "x": w_m, "y": 0}
        },
        {
            "btType": "BTMSketchCurveSegment-155",
            "startPoint": {"btType": "BTVector2d-1538", "x": w_m, "y": 0},
            "endPoint": {"btType": "BTVector2d-1538", "x": w_m, "y": d_m}
        },
        {
            "btType": "BTMSketchCurveSegment-155",
            "startPoint": {"btType": "BTVector2d-1538", "x": w_m, "y": d_m},
            "endPoint": {"btType": "BTVector2d-1538", "x": 0, "y": d_m}
        },
        {
            "btType": "BTMSketchCurveSegment-155",
            "startPoint": {"btType": "BTVector2d-1538", "x": 0, "y": d_m},
            "endPoint": {"btType": "BTVector2d-1538", "x": 0, "y": 0}
        }
    ]
    
    client.add_sketch(doc, element_id, "TOP", rectangle_entities)
    client.add_extrude(doc, element_id, "Sketch", h_m)
    
    doc.element_id = element_id
    return doc


# ==================== Test/Demo ====================

def demo():
    """Demonstrate Onshape client (mock mode if no credentials)."""
    print("=" * 60)
    print("ONSHAPE CLIENT DEMO")
    print("=" * 60)
    
    client = OnshapeClient()
    
    if not client.credentials:
        print("\n[INFO] No credentials found. Running in mock mode.")
        print("To use real Onshape API:")
        print("  export ONSHAPE_ACCESS_KEY='your_access_key'")
        print("  export ONSHAPE_SECRET_KEY='your_secret_key'")
        print()
    
    # Demo: Create a box
    print("Creating 50x30x20mm box...")
    doc = create_box(client, "Demo Box", 50, 30, 20)
    
    if doc:
        print(f"  Document ID: {doc.document_id}")
        print(f"  Workspace ID: {doc.workspace_id}")
        print(f"  Element ID: {doc.element_id}")
        
        # Export
        stl = client.export_stl(doc, doc.element_id)
        if stl:
            print(f"  STL exported: {len(stl)} bytes")
    else:
        print("  [MOCK] Would create document and geometry here")
    
    print()
    print("Done.")


if __name__ == "__main__":
    demo()
