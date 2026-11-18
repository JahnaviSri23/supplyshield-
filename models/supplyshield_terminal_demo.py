"""Interactive, aggregate-only terminal front end for the existing pipeline."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from io import StringIO
import sys
from typing import Any

from models.supplyshield_pipeline import STAGE_NAMES, get_demo_catalog_summary, run_supplyshield


DEFAULTS = {
    "sample_option": 1,
    "closure_option": 1,
    "demand_days": 14,
    "horizon": 40,
    "closure_days": 3,
}
MENU_PAGE_SIZE = 20


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run SupplyShield interactively, or provide scenario values as options."
    )
    parser.add_argument("--sample-option", type=int, default=None,
                        help="1-based anonymized compatible feature sample (interactive if omitted)")
    parser.add_argument("--closure-option", type=int, default=None,
                        help="1-based directed core-edge closure (interactive if omitted)")
    parser.add_argument("--demand-days", type=int, default=None,
                        help="demand period, 1-30 days (interactive if omitted)")
    parser.add_argument("--horizon", type=int, default=None,
                        help="observation horizon, 2-120 days and greater than demand period")
    parser.add_argument("--closure-days", type=int, default=None,
                        help="closure duration, 1-30 days (interactive if omitted)")
    parser.add_argument("--list-options", action="store_true",
                        help="show the dynamically computed number and range of valid choices")
    parser.add_argument("--verbose", action="store_true",
                        help="show detailed pipeline diagnostics and stage messages")
    return parser


def _fmt(value: Any, digits: int = 3) -> str:
    return f"{float(value):,.{digits}f}"


def _prompt_choice(label: str, explanation: str, total: int) -> int | None:
    page_count = (total + MENU_PAGE_SIZE - 1) // MENU_PAGE_SIZE
    page = 0
    while True:
        first = page * MENU_PAGE_SIZE + 1
        last = min(first + MENU_PAGE_SIZE - 1, total)
        print(f"\n{label}")
        print(f"  {explanation}")
        print(f"  Available choices: {total}; showing {first}-{last} (page {page + 1}/{page_count})")
        for start in range(first, last + 1, 5):
            group = range(start, min(start + 5, last + 1))
            print("  " + "   ".join(f"{n:04d}" for n in group))
        answer = input("  Enter a number, N/P for next/previous page, or Q to cancel: ").strip().lower()
        if answer == "q":
            return None
        if answer == "n":
            if page + 1 < page_count:
                page += 1
            else:
                print("  Already on the last page.")
            continue
        if answer == "p":
            if page > 0:
                page -= 1
            else:
                print("  Already on the first page.")
            continue
        try:
            choice = int(answer)
        except ValueError:
            print("  Enter a numeric choice, N, P, or Q.")
            continue
        if first <= choice <= last:
            return choice
        if 1 <= choice <= total:
            print(f"  Choice {choice} is not on this page; use N/P to navigate to it.")
        else:
            print(f"  Unavailable choice. Enter a number from {first} through {last}.")


def _prompt_days(label: str, explanation: str, minimum: int, maximum: int,
                 *, greater_than: int | None = None) -> int:
    while True:
        answer = input(f"\n{label}\n  {explanation}\n  Days ({minimum}-{maximum}): ").strip()
        try:
            value = int(answer)
        except ValueError:
            print("  Please enter a whole number of days.")
            continue
        if not minimum <= value <= maximum:
            print(f"  Enter a value from {minimum} through {maximum}.")
            continue
        if greater_than is not None and value <= greater_than:
            print(f"  The horizon must exceed the {greater_than}-day demand period so traffic can drain.")
            continue
        return value


def _scenario_from_args(args: argparse.Namespace, parser: argparse.ArgumentParser,
                         catalog: dict[str, int]) -> dict[str, int] | None:
    fully_interactive = all(
        getattr(args, name) is None
        for name in ("sample_option", "closure_option", "demand_days", "horizon", "closure_days")
    )
    if fully_interactive:
        sample = _prompt_choice(
            "Select prediction data sample.",
            "Choose a compatible, anonymized later-period model-input record; no identifiers are displayed.",
            catalog["sample_count"],
        )
        if sample is None:
            return None
        closure = _prompt_choice(
            "Select network disruption corridor.",
            "Choose one directed edge in the core network; it is mapped internally as the closure input.",
            catalog["closure_count"],
        )
        if closure is None:
            return None
        demand = _prompt_days(
            "Enter shipment demand period (days).",
            "Number of days during which the daily demand enters the simulation.", 1, 30,
        )
        closure_days = _prompt_days(
            "Enter expected corridor closure duration (days).",
            "How long the selected directed corridor remains closed.", 1, 30,
        )
        horizon = _prompt_days(
            "Enter total simulation observation horizon (days).",
            "Total run length; it must be longer than the demand period.", 2, 120,
            greater_than=demand,
        )
    else:
        # Preserve the earlier flags-only interface; omitted flags in a partial
        # command line retain their documented defaults.
        sample = args.sample_option if args.sample_option is not None else DEFAULTS["sample_option"]
        closure = args.closure_option if args.closure_option is not None else DEFAULTS["closure_option"]
        demand = args.demand_days if args.demand_days is not None else DEFAULTS["demand_days"]
        horizon = args.horizon if args.horizon is not None else DEFAULTS["horizon"]
        closure_days = args.closure_days if args.closure_days is not None else DEFAULTS["closure_days"]

    if not 1 <= sample <= catalog["sample_count"]:
        parser.error(f"sample option must be from 1 through {catalog['sample_count']}")
    if not 1 <= closure <= catalog["closure_count"]:
        parser.error(f"corridor option must be from 1 through {catalog['closure_count']}")
    if not 1 <= demand <= 30:
        parser.error("demand period must be from 1 through 30 days")
    if not 1 <= closure_days <= 30:
        parser.error("closure duration must be from 1 through 30 days")
    if not 2 <= horizon <= 120 or horizon <= demand:
        parser.error("horizon must be from 2 through 120 days and greater than the demand period")
    return {
        "sample_index": sample - 1,
        "closure_index": closure - 1,
        "demand_days": demand,
        "failure_days": closure_days,
        "horizon": horizon,
    }


def _display_result(result: dict[str, Any]) -> int:
    failed_stages = [
        name for name in STAGE_NAMES
        if result.get("stages", {}).get(name, {}).get("status") == "Failed"
    ]
    if result.get("status") == "FAILED" or failed_stages:
        print(f"\nPIPELINE FAILED: {result.get('error', 'No error detail returned.')}")
        if failed_stages:
            print(f"Failed stage: {failed_stages[-1]}")
        return 1
    if result.get("status") not in {"COMPLETE", "COMPLETE_WITH_WARNINGS"} or not result.get("result"):
        print(f"\nPIPELINE INCOMPLETE: unexpected status {result.get('status', 'missing')}.")
        return 1

    payload = result["result"]
    prediction = payload["prediction"]
    print("\nPREDICTION")
    print(f"  Predicted ratio: {_fmt(prediction['pred_ratio'], 4)}")
    print(f"  Predicted travel time: {_fmt(prediction['predicted_travel_time_min'], 2)} minutes")
    low, high = payload["uncertainty"]["ratio_intervals"]["90"]
    print(f"  90% conformal ratio interval: [{_fmt(low, 4)}, {_fmt(high, 4)}]")

    cvar = payload["risk_cvar"]["cvar"]
    print("\nRISK AND RECOVERY")
    if cvar.get("available"):
        print(f"  CVaR cost: {_fmt(cvar['cvar_cost_leg_hours_per_day'], 2)} leg-hours/day")
    else:
        print("  CVaR unavailable for this scenario; see --verbose diagnostics.")
    optimizer = payload["optimizer"]
    print(f"  Recovery objective: {_fmt(optimizer['objective_leg_hours_per_day'], 2)} leg-hours/day")
    print(f"  Optimized plan records: {optimizer['plan_records']}")

    print("\nSIMULATION COMPARISON (aggregate)")
    labels = {
        "baseline": "Baseline direct flow",
        "disrupted_no_reroute": "Disrupted, no reroute",
        "recovered": "Optimized recovery",
    }
    print(f"  {'Case':24} {'Generated':>12} {'Delivered':>12} {'Unmet':>10} {'Total cost':>14} {'Recovery':>12}")
    print("  " + "-" * 88)
    for key, label in labels.items():
        sim = payload["simulations"][key]
        recovery = "censored" if sim["recovery_censored"] else str(sim["recovery_days"])
        print(
            f"  {label:24} {_fmt(sim['generated']):>12} {_fmt(sim['delivered']):>12} "
            f"{_fmt(sim['unmet']):>10} {_fmt(sim['total_cost'], 2):>14} {recovery:>12}"
        )
    evaluation = payload["evaluation"]
    print(
        "\nTotal-cost change (optimized - disrupted): "
        f"{_fmt(evaluation['total_cost_change_vs_disruption'], 2)} leg-hours"
    )
    if not optimizer.get("plan_passed_to_simulator"):
        print("WARNING: optimized plan was not passed to the simulator.")
        return 1

    top = payload["explainability"]["top_features"]
    if top:
        feature = top[0]
        print(
            f"SHAP: top feature {feature['feature']} contributes "
            f"{_fmt(feature['contribution_to_residual'], 5)} to the predicted residual (not causal)."
        )
    print(
        "Limitations: CVaR aggregate output is not the simulator's OD-aware plan; other edges use "
        "tracked reference risk values; weather is not integrated; optimizer API does not expose solver status."
    )
    print(f"FINAL STATUS: {result['status']} - scenario completed; not a performance guarantee.")
    return 0


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    try:
        catalog = get_demo_catalog_summary()
    except Exception as exc:
        parser.exit(2, f"Input preflight failed: {type(exc).__name__}: {exc}\n")

    if args.list_options:
        print("PROVISIONAL - internal demonstration; instructor release approval pending.")
        print(f"Eligible prediction data samples: 1-{catalog['sample_count']}")
        print(f"Supported directed disruption corridors: 1-{catalog['closure_count']}")
        return 0

    try:
        scenario = _scenario_from_args(args, parser, catalog)
    except (KeyboardInterrupt, EOFError):
        print("\nInput cancelled; the pipeline was not started.")
        return 130
    if scenario is None:
        print("\nInput cancelled; the pipeline was not started.")
        return 0

    selected_sample = scenario["sample_index"] + 1
    selected_closure = scenario["closure_index"] + 1
    print("SUPPLYSHIELD TERMINAL DEMONSTRATION | PROVISIONAL / INTERNAL ONLY | instructor release pending")
    print(
        f"Scenario: sample {selected_sample}/{catalog['sample_count']}, "
        f"corridor {selected_closure}/{catalog['closure_count']}; "
        f"demand {scenario['demand_days']}d, closure {scenario['failure_days']}d, "
        f"horizon {scenario['horizon']}d."
    )
    if args.verbose:
        print("Running existing models.supplyshield_pipeline.run_supplyshield; no result files are written.")

    terminal = sys.stdout

    def progress(name: str, status: str, message: str) -> None:
        if status in {"Running", "Completed", "Warning", "Failed"}:
            if status == "Running":
                short_message = "started"
            elif status == "Warning":
                short_message = "CVaR output is not an OD-aware simulator plan."
            elif status == "Failed":
                short_message = "Stage failed; details follow."
            else:
                short_message = "complete"
            print(f"  {status.upper():9} {name}: {short_message}", file=terminal)
            if args.verbose:
                print(f"            {message}", file=terminal)

    diagnostics = StringIO()
    try:
        if args.verbose:
            result = run_supplyshield(scenario, progress=progress)
        else:
            # Capture direct print diagnostics from imported data/graph modules;
            # progress is routed to the original terminal stream above.
            with redirect_stdout(diagnostics):
                result = run_supplyshield(scenario, progress=progress)
    except KeyboardInterrupt:
        print("\nRun cancelled by user. No success status was reported.", file=terminal)
        return 130
    except Exception as exc:
        # Unexpected exceptions are not hidden by stdout capture.
        print(f"\nPIPELINE EXCEPTION: {type(exc).__name__}: {exc}", file=terminal)
        if args.verbose and diagnostics.getvalue():
            print(diagnostics.getvalue(), end="", file=terminal)
        return 1

    status = _display_result(result)
    if args.verbose and status != 0 and diagnostics.getvalue():
        print("\nPIPELINE DIAGNOSTICS:")
        print(diagnostics.getvalue(), end="")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
