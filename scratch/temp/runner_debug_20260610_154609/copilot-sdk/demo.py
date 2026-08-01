#!/usr/bin/env python3
"""
Compounding Intelligence Platform Launcher.

Usage:
    python demo.py                  # Start all 5 copilots, open browsers
    python demo.py --soc --diag-mode --diag-graph-name GRAPH
                                    # Start SOC backend for proof/perf diagnostics
    python demo.py --playwright     # Start SOC + S2P only (Playwright prereqs)
    python demo.py --soc            # SOC only (requires AGE)
    python demo.py --s2p            # S2P only
    python demo.py --sdk            # Trading + Purchasing + DataOps only
    python demo.py --dataops        # DataOps only
    python demo.py --stop           # Stop all copilot processes
    python demo.py --status         # Show what's running
    python demo.py --preseed        # Pre-seed after start
    python demo.py --graph          # AGE graph mode for DataOps
    python demo.py --no-browser     # Don't open browser tabs
    python demo.py --kill-all       # Kill all known copilot ports
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.request import urlopen

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# --- Configuration ---

SCRIPT_DIR = Path(__file__).resolve().parent
CI_PLATFORM = SCRIPT_DIR.parent / "ci-platform"
KEEPALIVE_PID_FILE = SCRIPT_DIR / ".wsl_keepalive.pid"

IS_WINDOWS = sys.platform == "win32"
CREATE_FLAGS = subprocess.CREATE_NEW_CONSOLE if IS_WINDOWS else 0

# AGE connection parameters (Rule #40: Windows-side AGE DSNs use localhost;
# HTTP/FastAPI URLs use 127.0.0.1.)
AGE_DSN_SOC = "host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres"
AGE_DSN_DATAOPS = "host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres"
SOC_REPO = Path(os.environ.get(
    "CLAUDE_SOC",
    str(SCRIPT_DIR.parent / "gen-ai-roi-demo-v4-v50"),
))
SOC_BACKEND = SOC_REPO / "backend"
SOC_CONTRACT_PATH = SOC_REPO / "scratch" / "temp" / "soc_diag_backend_contract.json"

COPILOTS = [
    {
        "name": "SOC",
        "be_port": 8001,
        "fe_port": 5173,
        "be_path": SOC_BACKEND,
        "fe_path": SOC_REPO / "frontend",
        "requires_age": True,
        "graph_dsn": AGE_DSN_SOC,
        "env": {
            "GRAPH_BACKEND": "age",
            "GRAPH_DSN": AGE_DSN_SOC,
        },
    },
    {
        "name": "Trading",
        "be_port": 8010,
        "fe_port": 5174,
        "be_path": SCRIPT_DIR / "apps" / "trading" / "backend",
        "fe_path": SCRIPT_DIR / "apps" / "trading" / "frontend",
    },
    {
        "name": "Purchasing",
        "be_port": 8020,
        "fe_port": 5175,
        "be_path": SCRIPT_DIR / "apps" / "purchasing" / "backend",
        "fe_path": SCRIPT_DIR / "apps" / "purchasing" / "frontend",
    },
    {
        "name": "DataOps",
        "be_port": 8030,
        "fe_port": 5176,
        "be_path": SCRIPT_DIR / "apps" / "dataops" / "backend",
        "fe_path": SCRIPT_DIR / "apps" / "dataops" / "frontend",
    },
    {
        "name": "S2P",
        "be_port": 8002,
        "fe_port": 5177,
        "be_path": Path(os.environ.get(
            "CLAUDE_S2P",
            str(SCRIPT_DIR.parent / "s2p-copilot"),
        )) / "backend",
        "fe_path": SCRIPT_DIR / "apps" / "s2p" / "frontend",
    },
]

# Named groups for convenience flags
SDK_NAMES = {"trading", "purchasing", "dataops"}
PLAYWRIGHT_NAMES = {"soc", "s2p"}


# --- Helpers ---

def check_port(port: int) -> bool:
    """Check if a port is responding."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except Exception:
        return False


def check_health(port: int, path: str = "/health") -> dict | None:
    """Check backend health endpoint."""
    try:
        r = urlopen(f"http://127.0.0.1:{port}{path}", timeout=5)
        return json.loads(r.read())
    except Exception:
        return None


def verify_age(dsn: str) -> bool:
    """Verify AGE/PostgreSQL is reachable."""
    try:
        import psycopg
        conn = psycopg.connect(dsn, autocommit=True, connect_timeout=5)
        conn.close()
        return True
    except Exception:
        return False


def redact_dsn(dsn: str) -> str:
    """Redact DSN passwords for diagnostic contract files."""
    parts = []
    for part in str(dsn).split():
        if part.lower().startswith("password="):
            parts.append("password=***")
        else:
            parts.append(part)
    return " ".join(parts)


def env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def verify_wsl2_running() -> bool:
    """Check if any WSL2 distribution is running."""
    try:
        result = subprocess.run(
            ["wsl", "--list", "--running"],
            capture_output=True, text=True, timeout=5,
        )
        # "no running distributions" means nothing is up
        output = result.stdout + result.stderr
        if "no running" in output.lower() or not result.stdout.strip():
            return False
        return True
    except Exception:
        return False


def start_wsl2_postgres() -> bool:
    """Start PostgreSQL inside WSL2 and keep WSL2 alive."""
    print("  Starting WSL2 + PostgreSQL...")
    try:
        # wsl -u root bypasses sudo entirely — no password prompt
        result = subprocess.run(
            ["wsl", "-d", "Ubuntu-24.04", "-u", "root", "--",
             "bash", "-c",
             "service postgresql start 2>/dev/null; sleep 3; "
             "su -c 'pg_isready -h 127.0.0.1 -p 5433 -q' postgres "
             "&& echo PG_READY || echo PG_FAIL"],
            capture_output=True, text=True, timeout=30,
        )
        if "PG_READY" not in result.stdout:
            output = (result.stdout + result.stderr).strip()
            print(f"  ✗ PostgreSQL did not start: {output[:200]}")
            return False

        print("  ✓ PostgreSQL started in WSL2")

        # Keep WSL2 alive with a background sleep process.
        # Without this, WSL2 may idle-shutdown and kill PostgreSQL
        # between backend starts (~30s gap is enough to trigger it).
        _start_wsl2_keepalive()
        return True

    except subprocess.TimeoutExpired:
        print("  ✗ WSL2 start timed out (30s)")
        return False
    except Exception as e:
        print(f"  ✗ WSL2 start failed: {e}")
        return False


_wsl_keepalive_proc = None


def _start_wsl2_keepalive():
    """Start a background WSL2 process to prevent idle shutdown."""
    global _wsl_keepalive_proc
    if _wsl_keepalive_proc and _wsl_keepalive_proc.poll() is None:
        return  # already running

    _wsl_keepalive_proc = subprocess.Popen(
        ["wsl", "-d", "Ubuntu-24.04", "-u", "root", "--",
         "bash", "-c", "while true; do sleep 300; done"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Save PID so --stop in a later process can find it
    try:
        KEEPALIVE_PID_FILE.write_text(str(_wsl_keepalive_proc.pid))
    except Exception:
        pass
    print(f"  ✓ WSL2 keepalive started (PID {_wsl_keepalive_proc.pid})")


def _stop_wsl2_keepalive():
    """Stop the WSL2 keepalive process, whether from this run or a prior one."""
    global _wsl_keepalive_proc

    # Try in-process handle first
    if _wsl_keepalive_proc and _wsl_keepalive_proc.poll() is None:
        _wsl_keepalive_proc.terminate()
        print("  Stopped WSL2 keepalive")
        _wsl_keepalive_proc = None

    # Also check saved PID file (from a prior demo.py run)
    if KEEPALIVE_PID_FILE.exists():
        try:
            pid = int(KEEPALIVE_PID_FILE.read_text().strip())
            if IS_WINDOWS:
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True, timeout=5,
                )
            else:
                os.kill(pid, 9)
            print(f"  Stopped prior WSL2 keepalive (PID {pid})")
        except Exception:
            pass
        KEEPALIVE_PID_FILE.unlink(missing_ok=True)


def ensure_age_available(dsn: str) -> bool:
    """Ensure AGE is reachable, starting WSL2/PostgreSQL if needed."""
    if verify_age(dsn):
        print("  ✓ AGE connection verified")
        _start_wsl2_keepalive()  # ensure keepalive even if PG was already up
        return True

    print("  AGE not reachable. Checking WSL2...")

    # Whether WSL2 is running or not, try starting PostgreSQL
    if not start_wsl2_postgres():
        print()
        print("  ╔════════════════════════════════════════════╗")
        print("  ║  AGE/PostgreSQL is not available.          ║")
        print("  ║                                            ║")
        print("  ║  Manual fix (Rule #38):                    ║")
        print("  ║  1. wsl -d Ubuntu-24.04 -u root            ║")
        print("  ║  2. service postgresql start                ║")
        print("  ║  3. Keep that terminal open                ║")
        print("  ║  4. Re-run demo.py                        ║")
        print("  ╚════════════════════════════════════════════╝")
        return False

    # PostgreSQL reported ready — verify from Windows side
    for attempt in range(5):
        time.sleep(2)
        if verify_age(dsn):
            print("  ✓ AGE connection verified")
            return True
        print(f"  Waiting for AGE... ({attempt + 1}/5)")

    print("  ✗ AGE not reachable after PostgreSQL start")
    return False


def ensure_soc_diag_graph(graph_name: str, dsn: str) -> dict[str, str]:
    """Ensure the SOC AGE graph exists and return AGE connection diagnostics."""
    if str(CI_PLATFORM) not in sys.path:
        sys.path.insert(0, str(CI_PLATFORM))
    from ci_platform.graph.age_client import AGEClient

    client = AGEClient(dsn=dsn, graph_name=graph_name)
    asyncio.run(client.ensure_graph())
    diagnostics = {
        "connection_mode": client.connection_mode,
        "pool_available": "true" if client.pool_available else "false",
    }
    asyncio.run(client.close())
    return diagnostics


def remove_soc_diag_contract(contract_path: Path) -> None:
    """Remove stale SOC diagnostic contract before launching a new backend."""
    if contract_path.exists():
        contract_path.unlink()
        print(f"  Removed stale SOC diagnostic contract: {contract_path}")


def write_soc_diag_contract(
    *,
    graph_name: str,
    backend_port: int,
    graph_dsn: str,
    contract_path: Path,
    ci_platform_import_path: str,
    age_use_pool_requested: str,
    connection_mode: str,
    pool_available: str,
) -> None:
    """Write the runtime contract consumed by SOC proof/perf runners."""
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract = {
        "launcher": "copilot-sdk/demo.py --diag-mode",
        "graph_name": graph_name,
        "backend_port": backend_port,
        "graph_dsn_redacted": redact_dsn(graph_dsn),
        "soc_learning_enabled": os.getenv("SOC_LEARNING_ENABLED", "true"),
        "use_entity_cache": os.getenv("USE_ENTITY_CACHE", "false"),
        "age_use_pool_requested": age_use_pool_requested,
        "age_use_pool": age_use_pool_requested,
        "connection_mode": connection_mode,
        "pool_available": pool_available,
        "pythonpath": os.getenv("PYTHONPATH", ""),
        "ci_platform_import_path": ci_platform_import_path,
        "health_url": f"http://127.0.0.1:{backend_port}/health",
        "launched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    print(f"  Wrote SOC diagnostic contract: {contract_path}")


def wait_for_health(name: str, port: int, timeout: int = 30) -> bool:
    """Poll /health until healthy or timeout."""
    for i in range(timeout):
        time.sleep(1)
        h = check_health(port)
        if h:
            status = h.get("status", "ok")
            domain = h.get("domain", "")
            print(f"  ✓ {name}: {status} {domain}")
            return True
    print(f"  ✗ {name}: not healthy after {timeout}s on :{port}")
    return False


def wait_for_frontend(name: str, port: int, timeout: int = 15) -> bool:
    """Poll frontend port until it responds or timeout."""
    for _ in range(timeout):
        time.sleep(1)
        if check_port(port):
            print(f"  ✓ {name} frontend ready on :{port}")
            return True
    print(f"  ✗ {name} frontend not ready on :{port} after {timeout}s")
    return False


def find_pids_on_port(port: int) -> list[int]:
    """Find process IDs listening on a port."""
    pids: set[int] = set()
    target_port = str(port)
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) < 5 or parts[0].upper() != "TCP":
                continue
            if parts[-2].upper() != "LISTENING":
                continue
            local_address = parts[1]
            if _port_from_local_address(local_address) != target_port:
                continue
            try:
                pids.add(int(parts[-1]))
            except ValueError:
                pass
    except Exception as e:
        print(f"  WARN: Could not inspect port :{port}: {e}")
    return sorted(pids)


def _port_from_local_address(local_address: str) -> str | None:
    """Extract the port from netstat's local address column."""
    if local_address.startswith("[") and "]:" in local_address:
        return local_address.rsplit("]:", 1)[-1]
    if ":" not in local_address:
        return None
    return local_address.rsplit(":", 1)[-1]


def kill_port(port: int, name: str = "") -> bool:
    """Kill processes on a specific port."""
    pids = find_pids_on_port(port)
    if not pids:
        return False
    attempted = False
    for pid in pids:
        try:
            attempted = True
            if IS_WINDOWS:
                result = subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode != 0:
                    message = (result.stderr or result.stdout or "").strip()
                    print(f"  WARN: Could not stop PID {pid} on :{port}: {message}")
                    continue
            else:
                os.kill(pid, 9)
            label = f" ({name})" if name else ""
            print(f"  Killed stale PID {pid} on :{port}{label}")
        except Exception as e:
            print(f"  WARN: Could not stop PID {pid} on :{port}: {e}")
    return attempted


def known_ports(selected: list[dict] | None = None) -> list[int]:
    """Return configured backend and frontend ports."""
    copilots = selected or COPILOTS
    ports: list[int] = []
    for c in copilots:
        ports.append(c["be_port"])
        if c.get("fe_port") is not None:
            ports.append(c["fe_port"])
    return ports


# --- Commands ---

def cmd_stop(selected: list[dict]):
    """Stop all selected copilot processes."""
    print("Stopping copilots...")
    for c in selected:
        kill_port(c["be_port"], f"{c['name']} backend")
        if c.get("fe_port") is not None:
            kill_port(c["fe_port"], f"{c['name']} frontend")

    _stop_wsl2_keepalive()

    time.sleep(2)
    print("Done.")


def cmd_kill_all():
    """Kill listeners on all configured copilot ports."""
    print("Killing all copilot port listeners...")
    killed_any = False
    for port in known_ports():
        killed_any = kill_port(port) or killed_any
    if not killed_any:
        print("  No copilot port listeners found.")
    print("Done.")


def cmd_status(selected: list[dict]):
    """Show status of selected copilots."""
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  Copilot Platform Status                             ║")
    print("╚══════════════════════════════════════════════════════╝")

    # AGE status
    age_ok = verify_age(AGE_DSN_SOC)
    wsl_ok = verify_wsl2_running()
    print(f"  AGE/PostgreSQL  {'UP ✓' if age_ok else 'DOWN ✗':8s}  "
          f"WSL2 {'running' if wsl_ok else 'stopped'}")
    print()

    for c in selected:
        be_up = check_port(c["be_port"])
        fe_port = c.get("fe_port")
        fe_up = check_port(fe_port) if fe_port is not None else False
        h = check_health(c["be_port"]) if be_up else None

        be_status = "UP ✓" if h else ("UP ?" if be_up else "DOWN")
        fe_status = "UP ✓" if fe_up else ("N/A" if fe_port is None else "DOWN")
        fe_label = f":{fe_port}" if fe_port is not None else "N/A"
        domain = h.get("domain", "") if h else ""
        age_flag = " [AGE]" if c.get("requires_age") else ""

        print(f"  {c['name']:12s}  backend :{c['be_port']} {be_status:8s}"
              f"  frontend {fe_label:>5s} {fe_status:8s}"
              f"  {domain}{age_flag}")
    print()


def cmd_start(selected: list[dict], args):
    """Start selected copilots."""
    if args.diag_mode:
        diag_age_use_pool_requested = args.age_use_pool or env_truthy("AGE_USE_POOL")
        selected = [c for c in selected if c["name"].lower() == "soc"]
        if not selected:
            print("Diagnostic mode is SOC-only; no SOC copilot selected.")
            return
        args.no_browser = True
        args.preseed = False
        args.graph = False
        soc = selected[0]
        soc["be_port"] = args.diag_backend_port
        soc["fe_port"] = None
        soc["graph_dsn"] = args.diag_graph_dsn
        soc["env"] = {
            "GRAPH_BACKEND": "age",
            "GRAPH_DSN": args.diag_graph_dsn,
            "AGE_GRAPH_NAME": args.diag_graph_name,
            "SOC_LEARNING_ENABLED": "true",
        }
        if diag_age_use_pool_requested:
            soc["env"]["AGE_USE_POOL"] = "true"
        diag_pythonpath = f"{CI_PLATFORM};{soc['be_path']}"
        os.environ["GRAPH_BACKEND"] = "age"
        os.environ["GRAPH_DSN"] = args.diag_graph_dsn
        os.environ["AGE_GRAPH_NAME"] = args.diag_graph_name
        os.environ["SOC_LEARNING_ENABLED"] = "true"
        os.environ["PYTHONPATH"] = diag_pythonpath
        if diag_age_use_pool_requested:
            os.environ["AGE_USE_POOL"] = "true"
        else:
            os.environ.pop("AGE_USE_POOL", None)
        contract_path = args.diag_contract.resolve()
        remove_soc_diag_contract(contract_path)

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print(f"║  Starting {len(selected)} copilot(s)...                        ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    # --- AGE pre-check for copilots that need it ---
    age_needed = [c for c in selected if c.get("requires_age")]
    if age_needed or args.graph:
        dsn = age_needed[0]["graph_dsn"] if age_needed else AGE_DSN_DATAOPS
        print("Checking AGE/PostgreSQL...")
        if not ensure_age_available(dsn):
            print()
            print("Cannot start AGE-dependent copilots. Exiting.")
            # Start non-AGE copilots anyway
            non_age = [c for c in selected if not c.get("requires_age")]
            if non_age:
                print(f"Starting {len(non_age)} non-AGE copilot(s) instead...")
                selected = non_age
            else:
                return
        print()

    diag_connection_mode = None
    diag_pool_available = None
    diag_import_path = None
    if args.diag_mode:
        try:
            print(f"Ensuring SOC diagnostic graph: {args.diag_graph_name}")
            diag_age_diagnostics = ensure_soc_diag_graph(args.diag_graph_name, args.diag_graph_dsn)
            diag_connection_mode = diag_age_diagnostics["connection_mode"]
            diag_pool_available = diag_age_diagnostics["pool_available"]
            import ci_platform.graph.age_graph_store as age_graph_store
            diag_import_path = str(Path(age_graph_store.__file__).resolve())
            print(f"  ✓ SOC diagnostic graph ready ({diag_connection_mode}; pool_available={diag_pool_available})")
        except Exception as exc:
            print(f"  ✗ SOC diagnostic graph setup failed: {exc}")
            return

    # --- Graph mode (DataOps AGE) ---
    if args.graph:
        setup_graph_mode()

    # --- Start backends ---
    print("Starting backends...")
    for c in selected:
        port = c["be_port"]
        kill_port(port, f"{c['name']} backend")
        if check_port(port):
            print(f"  {c['name']} backend already on :{port}")
            continue

        be_path = c["be_path"]
        if not (be_path / "app" / "main.py").exists():
            print(f"  ✗ {c['name']}: main.py not found at {be_path}")
            continue

        # Build environment with copilot-specific vars
        env = os.environ.copy()
        if c.get("env"):
            env.update(c["env"])
        if args.diag_mode:
            env["PYTHONPATH"] = diag_pythonpath

        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", str(port)],
            cwd=str(be_path),
            env=env,
            creationflags=CREATE_FLAGS,
        )
        print(f"  {c['name']} backend starting on :{port} (PID {proc.pid})")

    # --- Wait for health ---
    print()
    print("Waiting for backends...")
    all_healthy = True
    for c in selected:
        timeout = 60 if c.get("requires_age") else 30
        if not wait_for_health(c["name"], c["be_port"], timeout=timeout):
            all_healthy = False

    if not all_healthy:
        print()
        print("Some backends failed. Check the console windows for errors.")
        # Continue anyway — some backends may be up
    elif args.diag_mode:
        write_soc_diag_contract(
            graph_name=args.diag_graph_name,
            backend_port=args.diag_backend_port,
            graph_dsn=args.diag_graph_dsn,
            contract_path=args.diag_contract.resolve(),
            ci_platform_import_path=diag_import_path or "",
            age_use_pool_requested="true" if diag_age_use_pool_requested else "false",
            connection_mode=diag_connection_mode or "unknown",
            pool_available=diag_pool_available or "unknown",
        )

    # --- Pre-seed ---
    if args.preseed:
        run_preseed(selected)

    if args.diag_mode:
        print()
        print("SOC diagnostic backend is ready for T2 proof/perf validation.")
        print(f"  graph: {args.diag_graph_name}")
        print(f"  health: http://127.0.0.1:{args.diag_backend_port}/health")
        print(f"  contract: {args.diag_contract.resolve()}")
        return

    # --- Start frontends ---
    print()
    print("Starting frontends...")
    for c in selected:
        fe_port = c.get("fe_port")
        if fe_port is None:
            print(f"  {c['name']} has no frontend; skipping")
            continue

        kill_port(fe_port, f"{c['name']} frontend")
        if check_port(fe_port):
            print(f"  {c['name']} frontend already on :{fe_port}")
            continue

        fe_path = c.get("fe_path")
        if not fe_path or not (fe_path / "package.json").exists():
            print(f"  ✗ {c['name']}: package.json not found at {fe_path}")
            continue

        subprocess.Popen(
            ["npx", "vite", "--port", str(fe_port), "--host", "127.0.0.1"],
            cwd=str(fe_path),
            creationflags=CREATE_FLAGS,
            shell=IS_WINDOWS,
        )
        print(f"  {c['name']} frontend starting on :{fe_port}")

    # --- Wait for frontends ---
    print()
    print("Waiting for frontends...")
    for c in selected:
        fe_port = c.get("fe_port")
        if fe_port is not None:
            wait_for_frontend(c["name"], fe_port, timeout=15)

    # --- Open browsers ---
    if not args.no_browser:
        urls = []
        for c in selected:
            fe_port = c.get("fe_port")
            if fe_port is not None:
                urls.append((c["name"], f"http://localhost:{fe_port}"))
        if urls:
            print()
            print("Opening browsers...")
            url_list = [url for _, url in urls]

            edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
            chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

            if edge.exists():
                subprocess.Popen([str(edge), "--inprivate"] + url_list)
                print("  Opened in Edge InPrivate:")
            elif chrome.exists():
                subprocess.Popen([str(chrome), "--incognito"] + url_list)
                print("  Opened in Chrome Incognito:")
            else:
                for _, url in urls:
                    webbrowser.open_new_tab(url)
                    time.sleep(1)
                print("  Opened in default browser:")

            for name, url in urls:
                print(f"    {name}: {url}")

    # --- Summary ---
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  Platform Ready                                      ║")
    print("╚══════════════════════════════════════════════════════╝")
    for c in selected:
        fe_port = c.get("fe_port")
        age_flag = " [AGE]" if c.get("requires_age") else ""
        if fe_port is None:
            print(f"  {c['name']:12s}  backend http://localhost:{c['be_port']}{age_flag}")
        else:
            print(f"  {c['name']:12s}  http://localhost:{fe_port}"
                  f"  (backend :{c['be_port']}){age_flag}")
    print()
    print("  Stop:       python demo.py --stop")
    print("  Status:     python demo.py --status")
    print("  Playwright: python demo.py --playwright --no-browser")
    print()


def setup_graph_mode():
    """Set GRAPH_DSN and optionally seed the DataOps graph."""
    print("Setting up graph mode...")
    os.environ["GRAPH_DSN"] = AGE_DSN_DATAOPS

    seed_script = CI_PLATFORM / "scripts" / "seed_dataops_graph.py"
    if seed_script.exists():
        print("  Seeding DataOps graph...")
        try:
            subprocess.run(
                [sys.executable, str(seed_script), "--force"],
                cwd=str(CI_PLATFORM),
                timeout=30,
                check=True,
            )
            print("  ✓ Graph seeded")
        except Exception as e:
            print(f"  WARN: Graph seed failed: {e}")
            del os.environ["GRAPH_DSN"]
    else:
        print(f"  WARN: Seed script not found: {seed_script}")

    print()


def run_preseed(selected: list[dict]):
    """Run pre-seeding script."""
    print()
    print("Pre-seeding copilots...")
    script = SCRIPT_DIR / "scripts" / "preseed_all_copilots.py"
    if not script.exists():
        print(f"  WARN: Pre-seed script not found: {script}")
        return

    cmd = [sys.executable, str(script)]

    preseed_names = {"trading", "purchasing", "dataops"}
    names = {c["name"].lower() for c in selected if c["name"].lower() in preseed_names}
    if not names:
        print("  No selected copilots support pre-seed; skipping")
        return
    if names != preseed_names:
        for name in names:
            cmd.append(f"--{name}-only")

    try:
        subprocess.run(cmd, cwd=str(SCRIPT_DIR), timeout=600)
    except Exception as e:
        print(f"  WARN: Pre-seed failed: {e}")
    print()


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Compounding Intelligence Platform Launcher",
    )
    parser.add_argument("--stop", action="store_true", help="Stop all copilots")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--kill-all", action="store_true",
                        help="Kill listeners on all known copilot ports")

    # Individual copilot flags
    parser.add_argument("--soc", action="store_true", help="SOC only")
    parser.add_argument("--trading", action="store_true", help="Trading only")
    parser.add_argument("--purchasing", action="store_true", help="Purchasing only")
    parser.add_argument("--dataops", action="store_true", help="DataOps only")
    parser.add_argument("--s2p", action="store_true", help="S2P only")

    # Group flags
    parser.add_argument("--sdk", action="store_true",
                        help="SDK copilots only (Trading + Purchasing + DataOps)")
    parser.add_argument("--playwright", action="store_true",
                        help="Playwright prereqs only (SOC + S2P)")

    # Options
    parser.add_argument("--graph", action="store_true", help="AGE graph mode for DataOps")
    parser.add_argument("--preseed", action="store_true", help="Pre-seed after start")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browsers")
    parser.add_argument("--diag-mode", action="store_true", help="SOC proof/perf backend-only diagnostic mode")
    parser.add_argument("--diag-graph-name", default="soc_graph_diag_f", help="SOC AGE graph for --diag-mode")
    parser.add_argument("--diag-backend-port", type=int, default=8001, help="SOC backend port for --diag-mode")
    parser.add_argument("--diag-graph-dsn", default=AGE_DSN_SOC, help="SOC AGE DSN for --diag-mode")
    parser.add_argument("--diag-contract", type=Path, default=SOC_CONTRACT_PATH, help="SOC diagnostic backend contract path")
    parser.add_argument("--age-use-pool", action="store_true", help="Set AGE_USE_POOL=true for SOC --diag-mode")

    args = parser.parse_args()

    # --- Select copilots ---
    if args.diag_mode:
        args.soc = True
    individual = args.soc or args.trading or args.purchasing or args.dataops or args.s2p
    group = args.sdk or args.playwright

    if individual or group:
        selected_names = set()
        if args.soc:
            selected_names.add("soc")
        if args.trading:
            selected_names.add("trading")
        if args.purchasing:
            selected_names.add("purchasing")
        if args.dataops:
            selected_names.add("dataops")
        if args.s2p:
            selected_names.add("s2p")
        if args.sdk:
            selected_names |= SDK_NAMES
        if args.playwright:
            selected_names |= PLAYWRIGHT_NAMES
        selected = [c for c in COPILOTS if c["name"].lower() in selected_names]
    else:
        selected = list(COPILOTS)

    # --- Dispatch ---
    if args.kill_all:
        cmd_kill_all()
    elif args.stop:
        cmd_stop(selected)
    elif args.status:
        cmd_status(selected)
    else:
        cmd_start(selected, args)


if __name__ == "__main__":
    main()


