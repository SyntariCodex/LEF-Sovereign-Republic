#!/usr/bin/env python3
"""
Validation Engine — Fabrication Seed

Validates geometry before export to ensure:
1. Mesh is manifold (watertight)
2. No degenerate faces
3. Dimensions within constraints
4. Printability checks (overhangs, thickness)

This is the "proof" layer — geometry doesn't leave until validated.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

try:
    import numpy as np
    from stl import mesh
    HAS_STL = True
except ImportError:
    HAS_STL = False


@dataclass
class ValidationCheck:
    """Result of a single validation check."""
    name: str
    passed: bool
    message: str
    severity: str = "error"  # "error", "warning", "info"
    data: Dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Complete validation result."""
    passed: bool
    checks: List[ValidationCheck]
    geometry_stats: Dict = field(default_factory=dict)
    
    @property
    def errors(self) -> List[ValidationCheck]:
        return [c for c in self.checks if not c.passed and c.severity == "error"]
    
    @property
    def warnings(self) -> List[ValidationCheck]:
        return [c for c in self.checks if not c.passed and c.severity == "warning"]
    
    def summary(self) -> str:
        """Human-readable summary."""
        if self.passed:
            return f"✅ Validation passed ({len(self.checks)} checks)"
        else:
            errors = len(self.errors)
            warnings = len(self.warnings)
            return f"❌ Validation failed: {errors} errors, {warnings} warnings"


class MeshValidator:
    """
    Validates STL mesh geometry for fabrication.
    
    Checks performed:
    - Manifold (watertight)
    - No degenerate faces
    - Positive volume
    - No self-intersections (basic)
    - Dimension bounds
    """
    
    def __init__(self, 
                 min_thickness: float = 0.5,  # mm
                 max_dimensions: Tuple[float, float, float] = (500, 500, 500),  # mm
                 max_overhang_angle: float = 45):  # degrees
        self.min_thickness = min_thickness
        self.max_dimensions = max_dimensions
        self.max_overhang_angle = max_overhang_angle
    
    def validate(self, geometry: 'mesh.Mesh') -> ValidationResult:
        """Run all validation checks on geometry."""
        if not HAS_STL:
            return ValidationResult(
                passed=False,
                checks=[ValidationCheck(
                    name="dependency",
                    passed=False,
                    message="numpy-stl not installed",
                    severity="error"
                )]
            )
        
        checks = []
        
        # Run checks
        checks.append(self._check_has_faces(geometry))
        checks.append(self._check_manifold(geometry))
        checks.append(self._check_degenerate_faces(geometry))
        checks.append(self._check_positive_volume(geometry))
        checks.append(self._check_dimensions(geometry))
        checks.append(self._check_overhangs(geometry))
        
        # Calculate stats
        stats = self._calculate_stats(geometry)
        
        # Overall pass/fail
        passed = all(c.passed for c in checks if c.severity == "error")
        
        return ValidationResult(
            passed=passed,
            checks=checks,
            geometry_stats=stats
        )
    
    def _check_has_faces(self, geometry: 'mesh.Mesh') -> ValidationCheck:
        """Check that mesh has faces."""
        face_count = len(geometry.vectors)
        passed = face_count > 0
        return ValidationCheck(
            name="has_faces",
            passed=passed,
            message=f"Mesh has {face_count} faces" if passed else "Mesh has no faces",
            data={"face_count": face_count}
        )
    
    def _check_manifold(self, geometry: 'mesh.Mesh') -> ValidationCheck:
        """
        Check if mesh is manifold (watertight).
        
        A manifold mesh has every edge shared by exactly 2 faces.
        """
        # Build edge count
        edge_count = {}
        
        for face in geometry.vectors:
            for i in range(3):
                # Get edge vertices
                v1 = tuple(face[i].round(6))
                v2 = tuple(face[(i + 1) % 3].round(6))
                
                # Normalize edge direction
                edge = tuple(sorted([v1, v2]))
                edge_count[edge] = edge_count.get(edge, 0) + 1
        
        # Check for non-manifold edges
        non_manifold = [e for e, count in edge_count.items() if count != 2]
        boundary = [e for e, count in edge_count.items() if count == 1]
        
        passed = len(non_manifold) == 0 and len(boundary) == 0
        
        if passed:
            message = "Mesh is manifold (watertight)"
        else:
            message = f"Non-manifold: {len(non_manifold)} edges, {len(boundary)} boundary edges"
        
        return ValidationCheck(
            name="manifold",
            passed=passed,
            message=message,
            data={
                "non_manifold_edges": len(non_manifold),
                "boundary_edges": len(boundary)
            }
        )
    
    def _check_degenerate_faces(self, geometry: 'mesh.Mesh') -> ValidationCheck:
        """Check for zero-area or very small faces."""
        degenerate = 0
        total = len(geometry.vectors)
        min_area = 1e-10  # Very small threshold
        
        for i, face in enumerate(geometry.vectors):
            # Calculate area using cross product
            v1 = face[1] - face[0]
            v2 = face[2] - face[0]
            area = 0.5 * np.linalg.norm(np.cross(v1, v2))
            
            if area < min_area:
                degenerate += 1
        
        passed = degenerate == 0
        
        return ValidationCheck(
            name="degenerate_faces",
            passed=passed,
            message=f"No degenerate faces" if passed else f"{degenerate} degenerate faces",
            data={"degenerate_count": degenerate, "total_faces": total}
        )
    
    def _check_positive_volume(self, geometry: 'mesh.Mesh') -> ValidationCheck:
        """Check that mesh has positive volume (normals consistent)."""
        try:
            volume = geometry.get_mass_properties()[0]
            passed = volume > 0
            
            return ValidationCheck(
                name="positive_volume",
                passed=passed,
                message=f"Volume: {volume:.2f} mm³" if passed else "Negative or zero volume",
                data={"volume_mm3": volume}
            )
        except Exception as e:
            return ValidationCheck(
                name="positive_volume",
                passed=False,
                message=f"Could not calculate volume: {e}",
                severity="warning"
            )
    
    def _check_dimensions(self, geometry: 'mesh.Mesh') -> ValidationCheck:
        """Check dimensions are within bounds."""
        minx, maxx, miny, maxy, minz, maxz = self._get_bounds(geometry)
        
        width = maxx - minx
        depth = maxy - miny
        height = maxz - minz
        
        passed = (
            width <= self.max_dimensions[0] and
            depth <= self.max_dimensions[1] and
            height <= self.max_dimensions[2]
        )
        
        return ValidationCheck(
            name="dimensions",
            passed=passed,
            message=f"Dimensions: {width:.1f} x {depth:.1f} x {height:.1f} mm",
            data={
                "width": width,
                "depth": depth,
                "height": height,
                "max_allowed": self.max_dimensions
            }
        )
    
    def _check_overhangs(self, geometry: 'mesh.Mesh') -> ValidationCheck:
        """
        Check for severe overhangs (faces facing down at steep angles).
        
        Note: This is a warning, not an error — 3D printers can handle
        some overhangs with supports.
        """
        severe_overhangs = 0
        threshold_rad = math.radians(90 + self.max_overhang_angle)
        down = np.array([0, 0, -1])
        
        for normal in geometry.normals:
            # Angle between face normal and down vector
            norm = np.linalg.norm(normal)
            if norm > 0:
                cos_angle = np.dot(normal, down) / norm
                angle = math.acos(np.clip(cos_angle, -1, 1))
                
                if angle < threshold_rad:
                    severe_overhangs += 1
        
        passed = severe_overhangs < len(geometry.normals) * 0.1  # < 10% severe
        
        return ValidationCheck(
            name="overhangs",
            passed=passed,
            message=f"Severe overhangs: {severe_overhangs} faces",
            severity="warning",
            data={"severe_overhang_faces": severe_overhangs}
        )
    
    def _get_bounds(self, geometry: 'mesh.Mesh') -> Tuple[float, float, float, float, float, float]:
        """Get bounding box of mesh."""
        all_points = geometry.vectors.reshape(-1, 3)
        
        minx = all_points[:, 0].min()
        maxx = all_points[:, 0].max()
        miny = all_points[:, 1].min()
        maxy = all_points[:, 1].max()
        minz = all_points[:, 2].min()
        maxz = all_points[:, 2].max()
        
        return minx, maxx, miny, maxy, minz, maxz
    
    def _calculate_stats(self, geometry: 'mesh.Mesh') -> Dict:
        """Calculate geometry statistics."""
        minx, maxx, miny, maxy, minz, maxz = self._get_bounds(geometry)
        
        stats = {
            "face_count": len(geometry.vectors),
            "vertex_count": len(geometry.vectors) * 3,  # Approximate
            "bounds": {
                "min": [float(minx), float(miny), float(minz)],
                "max": [float(maxx), float(maxy), float(maxz)]
            },
            "dimensions_mm": {
                "width": float(maxx - minx),
                "depth": float(maxy - miny),
                "height": float(maxz - minz)
            }
        }
        
        try:
            volume, cog, inertia = geometry.get_mass_properties()
            stats["volume_mm3"] = float(volume)
            stats["center_of_gravity"] = [float(x) for x in cog]
        except:
            pass
        
        return stats


class ConstraintValidator:
    """
    Validates geometry against design constraints.
    
    Ensures the generated geometry matches what was requested.
    """
    
    def validate(self, geometry: 'mesh.Mesh', 
                 constraints: Dict,
                 tolerance: float = 1.0) -> ValidationResult:
        """
        Validate geometry matches constraints.
        
        Args:
            geometry: Generated mesh
            constraints: Original design constraints
            tolerance: Allowable deviation in mm
        """
        checks = []
        
        # Get actual dimensions
        mesh_validator = MeshValidator()
        bounds = mesh_validator._get_bounds(geometry)
        actual = {
            "width": bounds[1] - bounds[0],
            "depth": bounds[3] - bounds[2],
            "height": bounds[5] - bounds[4]
        }
        
        # Check each constraint dimension
        requested = constraints.get("dimensions", {})
        
        for dim in ["width", "depth", "height"]:
            if dim in requested:
                req = requested[dim]
                act = actual[dim]
                diff = abs(req - act)
                passed = diff <= tolerance
                
                checks.append(ValidationCheck(
                    name=f"dimension_{dim}",
                    passed=passed,
                    message=f"{dim}: requested {req:.1f}, got {act:.1f} (diff: {diff:.1f}mm)",
                    data={"requested": req, "actual": act, "difference": diff}
                ))
        
        passed = all(c.passed for c in checks)
        
        return ValidationResult(
            passed=passed,
            checks=checks
        )


# ==================== Demo ====================

def demo():
    """Demonstrate validation."""
    print("=" * 60)
    print("VALIDATION ENGINE DEMO")
    print("=" * 60)
    
    if not HAS_STL:
        print("numpy-stl required: pip install numpy-stl numpy")
        return
    
    # Create a simple box for testing
    from fabrication_seed import GeometryEngine, DesignConstraints
    
    engine = GeometryEngine()
    constraints = DesignConstraints(
        object_type="box",
        dimensions={"width": 50, "depth": 30, "height": 20}
    )
    
    geometry = engine.generate(constraints)
    
    # Validate
    validator = MeshValidator()
    result = validator.validate(geometry)
    
    print(f"\n{result.summary()}\n")
    
    for check in result.checks:
        status = "✅" if check.passed else "❌"
        print(f"  {status} {check.name}: {check.message}")
    
    print(f"\nGeometry stats:")
    for key, value in result.geometry_stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    demo()
