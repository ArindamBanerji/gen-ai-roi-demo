from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.seed.config import SeedConfig
from app.seed.runner import generate_seed
from app.seed.validate import validate_seed
from app.graph_schema import seed_graph


DEFAULT_OUTPUT = Path("support/setup/zero_day_decisions_v5.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic SOC seed JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--n-training-alerts", type=int)
    parser.add_argument("--n-demo-alerts", type=int)
    parser.add_argument("--n-decisions", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--time-range-days", type=int)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--reseed", action="store_true")
    parser.add_argument("--reseed-clean", action="store_true")
    return parser.parse_args()


def _reseed(output: Path, clean: bool) -> None:
    mode = "clean reseed" if clean else "reseed"
    print(f"Running graph {mode} from {output}...")
    asyncio.run(seed_graph(str(output), clean=clean))


def main() -> int:
    args = parse_args()
    output = Path(args.output)

    if args.validate_only:
        data = json.loads(output.read_text(encoding="utf-8"))
        result = validate_seed(data)
        if result.errors:
            print(f"Seed validation failed: {len(result.errors)} errors")
            for error in result.errors[:20]:
                print(f"  - {error}")
            return 1
        print("Seed validation passed")
        if args.reseed or args.reseed_clean:
            _reseed(output, clean=args.reseed_clean)
        return 0

    overrides = {}
    for arg_name, config_name in [
        ("n_training_alerts", "n_training_alerts"),
        ("n_demo_alerts", "n_demo_alerts"),
        ("n_decisions", "n_decisions"),
        ("seed", "seed"),
        ("time_range_days", "time_range_days"),
    ]:
        value = getattr(args, arg_name)
        if value is not None:
            overrides[config_name] = value

    data = generate_seed(SeedConfig(**overrides))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote seed JSON: {output}")
    print(f"Alerts={len(data['alerts'])}, demo_alerts={len(data['demo_alerts'])}, decisions={len(data['decisions'])}")
    if args.reseed or args.reseed_clean:
        _reseed(output, clean=args.reseed_clean)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
