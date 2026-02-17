#!/usr/bin/env python3
"""
SOC Copilot Demo - Pre-Demo Validation Script

Usage:
    python scripts/validate-setup.py

This script checks that all services are running and the demo is ready.
Run this before any presentation to verify setup.
"""

import sys
import json
import urllib.request
import urllib.error
from typing import Tuple, Dict, Any

# Configuration
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"
TIMEOUT = 5  # seconds

# Required minimums for demo readiness
MIN_NODES = 40
MIN_EVOLUTION_COUNT = 3


def print_header():
    """Print script header."""
    print()
    print("=" * 50)
    print("  SOC Copilot Demo - Pre-Demo Validation")
    print("=" * 50)
    print()


def print_result(name: str, success: bool, details: str = ""):
    """Print a check result."""
    icon = "âœ…" if success else "âŒ"
    print(f"  {icon} {name}")
    if details:
        for line in details.split("\n"):
            print(f"      {line}")


def check_backend() -> Tuple[bool, Dict[str, Any]]:
    """Check if backend is running and healthy."""
    try:
        url = f"{BACKEND_URL}/api/health"
        req = urllib.request.Request(url, method="GET")
        
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode())
            
            # Check health status
            is_healthy = data.get("status") == "healthy"
            neo4j_connected = data.get("neo4j") == "connected"
            node_count = data.get("nodes", 0)
            evolution_count = data.get("triggered_evolution_count", 0)
            demo_ready = data.get("demo_ready", False)
            
            return True, {
                "healthy": is_healthy,
                "neo4j": neo4j_connected,
                "nodes": node_count,
                "evolution_count": evolution_count,
                "demo_ready": demo_ready
            }
            
    except urllib.error.URLError as e:
        return False, {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return False, {"error": str(e)}


def check_frontend() -> Tuple[bool, Dict[str, Any]]:
    """Check if frontend is running."""
    try:
        url = FRONTEND_URL
        req = urllib.request.Request(url, method="GET")
        
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            return response.status == 200, {}
            
    except urllib.error.URLError as e:
        return False, {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return False, {"error": str(e)}


def check_api_endpoint(name: str, method: str, path: str) -> Tuple[bool, str]:
    """Check a specific API endpoint."""
    try:
        url = f"{BACKEND_URL}{path}"
        req = urllib.request.Request(url, method=method)
        
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            return response.status == 200, f"Status: {response.status}"
            
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)


def main() -> int:
    """Run all validation checks."""
    print_header()
    
    all_passed = True
    
    # Check 1: Backend Health
    print("Checking backend...")
    backend_ok, backend_info = check_backend()
    
    if backend_ok:
        details = f"Neo4j: {'connected' if backend_info.get('neo4j') else 'disconnected'}\n"
        details += f"Nodes: {backend_info.get('nodes', 0)}\n"
        details += f"TRIGGERED_EVOLUTION: {backend_info.get('evolution_count', 0)}"
        print_result("Backend", True, details)
        
        # Check data sufficiency
        if backend_info.get("nodes", 0) < MIN_NODES:
            print_result("Demo Data", False, f"Only {backend_info.get('nodes', 0)} nodes (need {MIN_NODES}+)")
            all_passed = False
        elif backend_info.get("evolution_count", 0) < MIN_EVOLUTION_COUNT:
            print_result("Demo Data", False, f"Only {backend_info.get('evolution_count', 0)} evolutions (need {MIN_EVOLUTION_COUNT}+)")
            all_passed = False
        else:
            print_result("Demo Data", True)
    else:
        print_result("Backend", False, backend_info.get("error", "Unknown error"))
        all_passed = False
    
    print()
    
    # Check 2: Frontend
    print("Checking frontend...")
    frontend_ok, frontend_info = check_frontend()
    
    if frontend_ok:
        print_result("Frontend", True)
    else:
        print_result("Frontend", False, frontend_info.get("error", "Not reachable"))
        all_passed = False
    
    print()
    
    # Check 3: Key API Endpoints (only if backend is up)
    if backend_ok:
        print("Checking API endpoints...")
        
        endpoints = [
            ("GET", "/api/deployments", "Deployments"),
            ("GET", "/api/alerts/queue", "Alert Queue"),
        ]
        
        for method, path, name in endpoints:
            ok, detail = check_api_endpoint(name, method, path)
            print_result(name, ok, detail if not ok else "")
            if not ok:
                all_passed = False
        
        print()
    
    # Summary
    print("=" * 50)
    if all_passed:
        print("  âœ… Demo is READY!")
        print()
        print("  ðŸŽ¬ Open http://localhost:5173 to present")
        print()
        print("  Quick demo flow:")
        print("    1. Tab 2 â†’ Process Alert â†’ Show TRIGGERED_EVOLUTION")
        print("    2. Tab 3 â†’ Select Alert â†’ Show Graph â†’ Execute")
        print("    3. Tab 4 â†’ Show Week 1 â†’ Week 4 compounding")
        print("    4. Tab 1 â†’ 'What's our MTTR?' â†’ Show metrics")
    else:
        print("  âŒ Demo is NOT ready")
        print()
        print("  Troubleshooting:")
        
        if not backend_ok:
            print("    â€¢ Backend not running:")
            print("      cd backend && uvicorn app.main:app --reload")
        
        if not frontend_ok:
            print("    â€¢ Frontend not running:")
            print("      cd frontend && npm run dev")
        
        if backend_ok and backend_info.get("nodes", 0) < MIN_NODES:
            print("    â€¢ Seed demo data:")
            print("      curl -X POST http://localhost:8000/api/demo/seed")
    
    print("=" * 50)
    print()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
