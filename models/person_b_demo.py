"""Run a synthetic-only demonstration of Person B's structural cascade model.

This is a small command-line illustration of the existing B04 abstraction.
It uses the same hand-specified H1-H8 fixture as the final B04 notebook and
does not read project datasets or write files.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sim.simulate import build_neighbors, simulate_cascade


def run_demo() -> None:
    """Print calm, full-cascade, and higher-tolerance synthetic cases."""
    edges = [
        ("H1", "H2"), ("H1", "H3"), ("H2", "H4"), ("H3", "H4"),
        ("H4", "H5"), ("H5", "H6"), ("H5", "H7"), ("H6", "H8"),
        ("H7", "H8"),
    ]
    capacity = {
        "H1": 100, "H2": 100, "H3": 100, "H4": 150,
        "H5": 120, "H6": 100, "H7": 100, "H8": 100,
    }
    baseline_load = {
        "H1": 60, "H2": 70, "H3": 70, "H4": 100,
        "H5": 80, "H6": 60, "H7": 60, "H8": 50,
    }
    neighbors = build_neighbors(edges)

    calm = simulate_cascade(capacity, baseline_load, neighbors, ["H4"])
    stressed_load = {**baseline_load, "H4": 120}
    cascade = simulate_cascade(capacity, stressed_load, neighbors, ["H4"])
    tolerant = simulate_cascade(
        capacity, stressed_load, neighbors, ["H4"], tolerance=1.1
    )

    assert calm["n_failed"] == 1
    assert calm["unserved_load"] == 0
    assert all(
        abs(calm["final_load"][hub] - expected) < 1e-6
        for hub, expected in {"H2": 100, "H3": 100, "H5": 120}.items()
    )
    assert cascade["n_failed"] == 8
    assert cascade["n_rounds"] == 4
    assert abs(cascade["unserved_load"] - 570) < 1e-6
    assert tolerant["n_failed"] == 1
    assert tolerant["unserved_load"] == 0
    for case in (calm, cascade, tolerant):
        assert case["converged"]
        assert case["conserved"]

    print("SYNTHETIC EXAMPLE ONLY -- not a real network forecast")
    print("Model: B04 undirected scalar-load structural cascade")
    for label, result in (
        ("Calm load, H4 fails", calm),
        ("Higher H4 load, H4 fails", cascade),
        ("Higher load, tolerance 1.1", tolerant),
    ):
        print(
            f"{label}: failed_hubs={result['n_failed']}, "
            f"rounds={result['n_rounds']}, "
            f"unserved_load={result['unserved_load']:.0f}, "
            f"conserved={result['conserved']}"
        )
    print("Checks: expected fixture outcomes and load conservation passed.")


if __name__ == "__main__":
    run_demo()
