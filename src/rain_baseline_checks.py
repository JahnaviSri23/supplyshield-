from pathlib import Path

import numpy as np
import pandas as pd

from src.targets import (
    apply_targets,
    fit_baselines,
    training_mask,
)


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"

RAIN_GROUPS = ["dry", "light", "heavy"]


def summarise(data, groups):
    return (
        data.groupby(groups, observed=True)
        .agg(
            legs=("excess", "size"),
            median_excess=("excess", "median"),
            disrupted_count=("disrupted", "sum"),
            disrupted_share=("disrupted", "mean"),
        )
        .reset_index()
        .assign(
            disrupted_pct=lambda x: 100 * x["disrupted_share"]
        )
        .drop(columns="disrupted_share")
    )


def main():
    # Reuse the shared definition rather than duplicate it.
    legs = pd.read_csv(PROCESSED / "legs.csv")
    enriched = pd.read_csv(PROCESSED / "legs_enriched.csv")

    baselines = fit_baselines(legs)
    data = apply_targets(enriched, baselines)

    rain = pd.to_numeric(
        data["source_rain_mm"], errors="coerce"
    )

    eligible = (
        training_mask(data)
        & rain.notna()
        & np.isfinite(rain)
        & rain.ge(0)
        & data["disrupted"].notna()
    )

    analysis = data.loc[eligible].copy()
    analysis["rain_mm"] = rain.loc[eligible]

    # Project analysis categories, not official weather classifications.
    analysis["rain_group"] = np.select(
        [
            analysis["rain_mm"].eq(0),
            analysis["rain_mm"].lt(10),
        ],
        ["dry", "light"],
        default="heavy",
    )

    analysis["rain_group"] = pd.Categorical(
        analysis["rain_group"],
        categories=RAIN_GROUPS,
        ordered=True,
    )

    summary = summarise(analysis, ["rain_group"])

    # Also report each baseline group separately.
    by_group = summarise(
        analysis,
        ["route_type", "distance_bucket", "rain_group"],
    )

    summary.to_csv(
        PROCESSED / "rain_baseline_summary.csv",
        index=False,
    )
    by_group.to_csv(
        PROCESSED / "rain_baseline_by_group.csv",
        index=False,
    )

    rates = summary.set_index("rain_group")["disrupted_pct"]

    if "dry" in rates.index and "heavy" in rates.index:
        dry = float(rates.loc["dry"])
        heavy = float(rates.loc["heavy"])

        sentence = (
            "Among completed training core journeys with source "
            f"weather, the baseline-relative disrupted share was "
            f"{dry:.2f}% on dry days and {heavy:.2f}% on days with "
            "at least 10 mm of rain; this descriptive comparison "
            "does not establish that rain caused the difference."
        )
    else:
        sentence = (
            "There were insufficient dry or heavy-rain observations "
            "to compare their disrupted shares."
        )

    report = """# Baseline-relative rain analysis

Baselines use route type × OSRM distance bucket.
The reference is all valid training legs completed before
2018-09-26, with trip creation and departure within the
training window starting 2018-09-12.

Each baseline group requires at least 30 observations.
Excess = travel ratio minus the training group median.
Disrupted = travel ratio strictly above the training group p90.
Unknown targets remain missing.

Rain groups use source departure-day rainfall:
- Dry: exactly 0 mm.
- Light: greater than 0 and less than 10 mm.
- Heavy: at least 10 mm.

These are project analysis categories, not official weather labels.

The comparison uses completed training core legs with known
targets and valid source rainfall. Missing rainfall is not zero.
These are in-sample descriptive results, not held-out evaluation.
Journeys share lanes, dates and weather grids, so observations
are not independent. Group composition can differ by rain level.
City locations are approximate. Historical daily rain is not
a forecast available at departure.

## Results

"""
    report += "```text\n"
    report += summary.round(4).to_string(index=False)
    report += "\n```\n\n"
    report += sentence + "\n"

    DOCS.mkdir(exist_ok=True)
    (DOCS / "rain_baseline_analysis.md").write_text(
        report, encoding="utf-8"
    )

    print("Eligible training legs:", len(analysis))
    print("\nBaseline-relative rain results:")
    print(summary.round(4).to_string(index=False))
    print("\nResult:")
    print(sentence)
    print("\nSaved:")
    print("data/processed/rain_baseline_summary.csv")
    print("data/processed/rain_baseline_by_group.csv")
    print("docs/rain_baseline_analysis.md")


if __name__ == "__main__":
    main()