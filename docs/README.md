# SupplyShield data pipeline

Run commands from the project root with ss_env activated.

## Scripts

- src/make_legs.py: aggregates raw Delhivery scans into journey legs and directed lanes.
- src/graph.py: compares lane thresholds and calculates hub importance.
- src/distance_checks.py: summarises travel-time ratios by distance.
- src/olist_checks.py: calculates Olist late-delivery shares overall and by customer state.
- src/geocode_hubs.py: searches for approximate city coordinates and records unresolved matches.
- src/select_core.py: rebuilds the frozen training-only core using the saved location snapshot.
- src/weather_pipeline.py: reuses or downloads ERA5 daily weather and joins it to core legs.

## Rebuild the core and weather

Place the required source datasets in data/raw/, then run:

    python -m src.make_legs
    python -m src.select_core
    python -m src.weather_pipeline

The location snapshot preserves reviewed geocoding decisions.
Running the geocoder again is not required to reproduce the frozen core.

## Inputs and outputs

- config/hub_location_snapshot.csv: saved hub locations, match statuses and review evidence.
- data/processed/legs.csv: aggregated journey legs.
- data/processed/lanes.csv: directed lanes and full-data summary statistics.
- data/processed/core_nodes.csv: 100 selected hubs, location information and any later capacity estimates.
- data/processed/core_edges.csv: 292 frozen directed lanes with training-only counts.
- data/processed/core_train_legs.csv: 5,395 training journey legs on frozen lanes.
- data/processed/core_later_legs.csv: 2,422 later journey legs on frozen lanes.
- data/processed/core_training_comparison.csv: training-only comparison of 50/100/150-hub candidates.
- data/processed/core_location_review.csv: unresolved core hub locations.
- data/processed/core_location_coverage.csv: endpoint location coverage by period.
- data/processed/weather_hubs.csv: 95 hubs used for weather requests.
- data/processed/weather_daily.csv: 2,470 hub-day weather records.
- data/processed/legs_enriched.csv: 7,817 core legs with endpoint weather and availability flags.
- data/processed/weather_join_coverage.csv: weather coverage by period.
- data/processed/weather_download_errors.csv: failed requests; currently empty apart from headers.
- data/processed/weather_cache_era5/: local reusable weather cache, excluded from Git.

## Evaluation split

Split whole trips by trip_creation_time:

- Training: 12–25 September 2018.
- Calibration: 26–29 September 2018.
- Testing: 30 September onward.

The later file combines calibration and testing.
Person B must separate these periods before model evaluation.
Journey activity and weather can extend beyond trip creation dates.

## Current status

The frozen core and weather join are complete.
Capacity estimation and the rain-delay association test remain pending.
See assumptions.md for selection rules and limitations.