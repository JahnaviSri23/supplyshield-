from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"

KEYS = ["source_center", "destination_center"]


def main():
    data = pd.read_csv(PROCESSED / "legs_enriched.csv")
    nodes = pd.read_csv(PROCESSED / "core_nodes.csv")
    edges = pd.read_csv(PROCESSED / "core_edges.csv")

    # Check the interface required by the optimizer.
    required_nodes = {
        "hub", "name", "state", "lat", "lon",
        "legs_per_day_p95", "capacity_est"
    }
    required_edges = {
        "source", "destination", "trips",
        "median_actual_time", "median_ratio",
        "p90_ratio", "distance_km"
    }

    assert required_nodes.issubset(nodes.columns)
    assert required_edges.issubset(edges.columns)
    assert nodes["hub"].is_unique
    assert not edges.duplicated(["source", "destination"]).any()
    assert set(edges["source"]).issubset(set(nodes["hub"]))
    assert set(edges["destination"]).issubset(set(nodes["hub"]))
    assert nodes["capacity_est"].notna().all()
    assert nodes["capacity_est"].ge(0).all()
    assert edges["trips"].ge(3).all()

    assert np.array_equal(
        nodes["capacity_est"].to_numpy(),
        np.ceil(nodes["legs_per_day_p95"].to_numpy())
    )

    created = pd.to_datetime(
        data["trip_creation_time"], errors="raise"
    )
    departure = pd.to_datetime(
        data["od_start_time"], errors="raise"
    )
    rain = pd.to_numeric(data["source_rain_mm"], errors="coerce")
    ratio = pd.to_numeric(data["delay_ratio"], errors="coerce")

    eligible = (
        created.ge("2018-09-12")
        & created.lt("2018-09-26")
        & departure.ge("2018-09-12")
        & departure.lt("2018-09-26")
        & rain.notna()
        & np.isfinite(rain)
        & rain.ge(0)
        & ratio.notna()
        & np.isfinite(ratio)
        & ratio.ge(0)
    )

    analysis = data.loc[eligible].copy()
    analysis["rain_mm"] = rain.loc[eligible]
    analysis["ratio"] = ratio.loc[eligible]
    analysis["departure_date"] = departure.loc[eligible].dt.normalize()

    summaries = []
    comparisons = []

    for threshold in [1.0, 5.0, 10.0]:
        selected = analysis.loc[
            analysis["rain_mm"].eq(0)
            | analysis["rain_mm"].ge(threshold)
        ].copy()

        selected["condition"] = np.where(
            selected["rain_mm"].eq(0), "dry", "rainy"
        )

        grouped = (
            selected.groupby(KEYS + ["condition"])
            .agg(
                legs=("ratio", "size"),
                days=("departure_date", "nunique"),
                median_ratio=("ratio", "median"),
            )
            .reset_index()
        )

        dry = grouped.loc[grouped["condition"].eq("dry")].rename(
            columns={
                "legs": "dry_legs",
                "days": "dry_days",
                "median_ratio": "dry_median",
            }
        )
        rainy = grouped.loc[grouped["condition"].eq("rainy")].rename(
            columns={
                "legs": "rainy_legs",
                "days": "rainy_days",
                "median_ratio": "rainy_median",
            }
        )

        paired = dry[
            KEYS + ["dry_legs", "dry_days", "dry_median"]
        ].merge(
            rainy[KEYS + ["rainy_legs", "rainy_days", "rainy_median"]],
            on=KEYS,
            validate="one_to_one",
        )

        paired = paired.loc[
            paired["dry_legs"].ge(3)
            & paired["rainy_legs"].ge(3)
        ].copy()

        paired["rainy_minus_dry"] = (
            paired["rainy_median"] - paired["dry_median"]
        )
        paired["rain_threshold_mm"] = threshold
        comparisons.append(paired)

        # Additional support check: observations across multiple days.
        multi_day = paired.loc[
            paired["dry_days"].ge(2)
            & paired["rainy_days"].ge(2)
        ]

        summaries.append({
            "rain_threshold_mm": threshold,
            "eligible_legs": len(analysis),
            "dry_legs": int(analysis["rain_mm"].eq(0).sum()),
            "rainy_legs": int(analysis["rain_mm"].ge(threshold).sum()),
            "comparable_lanes": len(paired),
            "represented_legs": int(
                (paired["dry_legs"] + paired["rainy_legs"]).sum()
            ),
            "median_difference": paired["rainy_minus_dry"].median(),
            "positive_lane_pct": (
                100 * paired["rainy_minus_dry"].gt(0).mean()
                if len(paired) else np.nan
            ),
            "multi_day_lanes": len(multi_day),
            "multi_day_median_difference":
                multi_day["rainy_minus_dry"].median(),
        })

    summary = pd.DataFrame(summaries)
    details = pd.concat(comparisons, ignore_index=True)

    summary.to_csv(
        PROCESSED / "rain_threshold_sensitivity.csv", index=False
    )
    details.to_csv(
        PROCESSED / "rain_lane_sensitivity.csv", index=False
    )

    DOCS.mkdir(exist_ok=True)
    report = """# Training-only rain comparison

Dry means exactly 0 mm of source departure-day rainfall.
Rainy thresholds are 1, 5 and 10 mm; intermediate amounts are excluded.
Each compared lane needs at least three legs per condition.
The additional multi-day check requires at least two dates per condition.

Lane effects are rainy median travel-time ratio minus dry median ratio.
The reported overall median gives each eligible lane equal weight.
Different thresholds can include different lanes, so their results are
not a dose-response estimate.

This is descriptive analysis, not a causal or statistical significance test.
Trips sharing dates, locations and weather grids are not independent.
City coordinates and daily endpoint rainfall are approximate exposures.
Same-day historical rainfall is not information available at departure.
The short training period limits generalisation.

## Results

"""
    report += "```text\n"
    report += summary.round(4).to_string(index=False)
    report += "\n```\n"

    (DOCS / "rain_analysis.md").write_text(report, encoding="utf-8")

    print("Core handoff checks: PASS")
    print("Core hubs:", len(nodes))
    print("Core lanes:", len(edges))
    print("\nRain sensitivity results:")
    print(summary.round(4).to_string(index=False))
    print("\nSaved two CSVs and docs/rain_analysis.md")


if __name__ == "__main__":
    main()