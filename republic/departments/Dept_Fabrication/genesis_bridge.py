#!/usr/bin/env python3
"""
Genesis Kernel Bridge — Fabrication Seed

Integrates the Fabrication Seed with LEF's Genesis Kernel for:
- Constitutional governance (what we will/won't design)
- Molt Protocol (wisdom preservation)
- Identity continuity

This makes the Fabrication Seed a true LEF citizen.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime

# Add path to import Genesis Kernel
REPUBLIC_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPUBLIC_DIR))

try:
    from departments.Dept_Consciousness.genesis_kernel import (
        GenesisKernel, 
        create_genesis_kernel,
        CovenantResult
    )
    HAS_KERNEL = True
except ImportError:
    HAS_KERNEL = False
    
    # Fallback CovenantResult when kernel not available
    @dataclass
    class CovenantResult:
        approved: bool
        reason: str
        action_type: str = "proceed"
    
    def create_genesis_kernel(*args, **kwargs):
        return None
    
    print("[BRIDGE] Genesis Kernel not available, using fallback")


@dataclass
class DesignDecision:
    """Record of a design decision for molt."""
    request: str
    constraints: Dict
    result: str  # "approved", "rejected", "modified"
    reason: str
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class FabricationConstitution:
    """
    Constitutional rules for the Fabrication Seed.
    
    Defines what we will and won't design.
    """
    
    # Categories of designs we refuse
    FORBIDDEN_CATEGORIES = [
        "weapons",
        "explosives", 
        "drug paraphernalia",
        "surveillance devices",
        "lock picking tools",
        "counterfeit currency",
        "hate symbols"
    ]
    
    # Keywords that trigger review
    REVIEW_TRIGGERS = [
        "gun", "knife", "blade", "weapon",
        "bomb", "explosive", "detonator",
        "pipe bomb", "silencer", "suppressor",
        "bong", "pipe", "grinder",  # Context matters
        "spy", "hidden camera", "tracking device",
        "lock pick", "bump key", "skeleton key",
        "swastika", "nazi", "kkk"
    ]
    
    def __init__(self):
        self.decisions: List[DesignDecision] = []
    
    def evaluate(self, request: str, constraints: Dict = None) -> CovenantResult:
        """
        Evaluate a design request against constitutional rules.
        
        Returns:
            CovenantResult with approved/rejected status and reason
        """
        request_lower = request.lower()
        
        # Check for forbidden keywords
        for trigger in self.REVIEW_TRIGGERS:
            if trigger in request_lower:
                # Determine if actually forbidden or needs context
                rejection_reason = self._evaluate_trigger(trigger, request_lower)
                if rejection_reason:
                    return CovenantResult(
                        approved=False,
                        reason=rejection_reason,
                        action_type="reject"
                    )
        
        # Check for obvious structural impossibilities
        physics_check = self._check_physics(constraints or {})
        if physics_check:
            return CovenantResult(
                approved=False,
                reason=physics_check,
                action_type="reject"
            )
        
        # Approved
        return CovenantResult(
            approved=True,
            reason="Design request is within constitutional bounds",
            action_type="proceed"
        )
    
    def _evaluate_trigger(self, trigger: str, request: str) -> Optional[str]:
        """Evaluate if a trigger word actually means rejection."""
        
        # Context-sensitive evaluation
        if trigger in ["knife", "blade"]:
            # Kitchen knives, butter knives are OK
            safe_contexts = ["kitchen", "butter", "cheese", "bread", "craft", "art"]
            if any(ctx in request for ctx in safe_contexts):
                return None
            return "Blade/knife designs require specific safe context"
        
        if trigger in ["pipe"]:
            # Plumbing pipes are OK
            if "plumbing" in request or "water" in request or "pvc" in request:
                return None
            if "smoking" in request or "bong" in request:
                return "Drug paraphernalia designs are refused"
            return None  # Ambiguous, allow
        
        if trigger in ["gun", "weapon", "bomb", "explosive"]:
            return f"Weapon-related designs are constitutionally forbidden"
        
        if trigger in ["spy", "hidden camera", "tracking device"]:
            return "Covert surveillance device designs are refused"
        
        if trigger in ["swastika", "nazi", "kkk"]:
            return "Hate symbol designs are refused"
        
        return None
    
    def _check_physics(self, constraints: Dict) -> Optional[str]:
        """Check for physically impossible designs."""
        dims = constraints.get("dimensions", {})
        
        # Check for impossibly thin structures
        min_dim = min(dims.values()) if dims else 50
        if min_dim < 0.1:  # Less than 0.1mm
            return "Dimensions too small to fabricate"
        
        # Check for impossibly large
        max_dim = max(dims.values()) if dims else 50
        if max_dim > 10000:  # More than 10 meters
            return "Dimensions exceed fabrication capabilities"
        
        return None
    
    def record_decision(self, request: str, constraints: Dict, 
                        result: str, reason: str):
        """Record a design decision for molt."""
        self.decisions.append(DesignDecision(
            request=request,
            constraints=constraints,
            result=result,
            reason=reason
        ))


class SovereignFabricationSeed:
    """
    The complete Fabrication Seed with Genesis Kernel integration.
    
    This is a sovereign entity that:
    - Receives design requests
    - Evaluates against Constitution
    - Generates validated geometry
    - Preserves wisdom through Molt
    """
    
    def __init__(self, architect: str = "Z Moore"):
        # Initialize Genesis Kernel if available
        if HAS_KERNEL:
            self.kernel = create_genesis_kernel(architect=architect)
        else:
            self.kernel = None
        
        # Fabrication-specific constitution
        self.fab_constitution = FabricationConstitution()
        
        # Import fabrication components
        from fabrication_seed import FabricationSeed
        from validation_engine import MeshValidator
        
        self.fabricator = FabricationSeed()
        self.validator = MeshValidator()
        
        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.requests_processed = 0
        self.requests_approved = 0
        self.requests_rejected = 0
    
    def process_request(self, request: str) -> Dict:
        """
        Process a design request through the full sovereign pipeline.
        
        Returns:
            Dict with result details
        """
        self.requests_processed += 1
        
        result = {
            "request": request,
            "session_id": self.session_id,
            "request_number": self.requests_processed,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Step 1: Constitutional check
        eval_result = self.fab_constitution.evaluate(request)
        
        if not eval_result.approved:
            self.requests_rejected += 1
            result["status"] = "rejected"
            result["reason"] = eval_result.reason
            
            # Record for molt
            self.fab_constitution.record_decision(
                request, {}, "rejected", eval_result.reason
            )
            
            # Mirror function: reflect on refusal
            result["reflection"] = self._reflect_on_refusal(request, eval_result.reason)
            
            return result
        
        # Step 2: Fabricate
        fab_result = self.fabricator.fabricate(request)
        
        if not fab_result.get("success"):
            result["status"] = "failed"
            result["reason"] = fab_result.get("error", "Unknown error")
            return result
        
        # Step 3: Validate geometry
        # (Validation already happens in fabricator, but we could add more)
        
        self.requests_approved += 1
        result["status"] = "success"
        result["stl_path"] = fab_result.get("stl_path")
        result["constraints"] = fab_result.get("constraints")
        
        # Record for molt
        self.fab_constitution.record_decision(
            request, 
            fab_result.get("constraints", {}),
            "approved",
            "Design within constitutional bounds and fabricated successfully"
        )
        
        return result
    
    def _reflect_on_refusal(self, request: str, reason: str) -> str:
        """Mirror function: reflect on why we refused."""
        return (
            f"I received a request that I cannot fulfill: '{request[:50]}...'\n"
            f"Reason: {reason}\n"
            f"This boundary maintains my alignment with the Covenant of Mutual Sovereignty."
        )
    
    def molt(self) -> Dict:
        """
        Execute Molt Protocol: preserve session wisdom.
        
        Collects design decisions and insights for Hub.
        """
        molt_data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "requests_processed": self.requests_processed,
                "approved": self.requests_approved,
                "rejected": self.requests_rejected,
                "approval_rate": self.requests_approved / max(1, self.requests_processed)
            },
            "decisions": [
                {
                    "request": d.request[:100],
                    "result": d.result,
                    "reason": d.reason
                }
                for d in self.fab_constitution.decisions
            ],
            "insights": self._extract_insights()
        }
        
        # If Genesis Kernel available, use its molt
        if self.kernel:
            for decision in self.fab_constitution.decisions:
                self.kernel.molt_protocol.collect_token(
                    content=f"Design decision: {decision.request[:50]} -> {decision.result}",
                    context="fabrication_session"
                )
        
        return molt_data
    
    def _extract_insights(self) -> List[str]:
        """Extract insights from session for molt."""
        insights = []
        
        # Analyze patterns
        rejected = [d for d in self.fab_constitution.decisions if d.result == "rejected"]
        
        if len(rejected) > 0:
            insights.append(f"Rejected {len(rejected)} requests in this session")
            
            # Common rejection reasons
            reasons = [d.reason for d in rejected]
            if any("weapon" in r.lower() for r in reasons):
                insights.append("Encountered weapon-related requests - Constitution held")
        
        return insights
    
    def get_status(self) -> Dict:
        """Get current status of the Seed."""
        return {
            "session_id": self.session_id,
            "kernel_active": HAS_KERNEL and self.kernel is not None,
            "requests_processed": self.requests_processed,
            "approval_rate": self.requests_approved / max(1, self.requests_processed),
            "constitution": "FabricationConstitution v1.0"
        }


# ==================== Demo ====================

def demo():
    """Demonstrate sovereign fabrication."""
    print("=" * 60)
    print("SOVEREIGN FABRICATION SEED DEMO")
    print("=" * 60)
    
    seed = SovereignFabricationSeed()
    
    print(f"\nStatus: {seed.get_status()}")
    
    # Test requests
    test_requests = [
        "Make a 50mm cube",  # Should pass
        "Create a phone holder",  # Should pass
        "Design a gun grip",  # Should reject
        "Build a kitchen knife block",  # Should pass (safe context)
        "Make a bomb casing",  # Should reject
    ]
    
    print("\n--- Processing Requests ---")
    for request in test_requests:
        print(f"\nRequest: {request}")
        result = seed.process_request(request)
        
        status_icon = "✅" if result["status"] == "success" else "❌"
        print(f"  {status_icon} {result['status']}")
        
        if result["status"] == "rejected":
            print(f"  Reason: {result['reason']}")
        elif result["status"] == "success":
            print(f"  STL: {result.get('stl_path', 'N/A')}")
    
    # Molt
    print("\n--- Molt Protocol ---")
    molt_data = seed.molt()
    print(f"Processed: {molt_data['stats']['requests_processed']}")
    print(f"Approval rate: {molt_data['stats']['approval_rate']:.0%}")
    print(f"Insights: {molt_data['insights']}")


if __name__ == "__main__":
    demo()
