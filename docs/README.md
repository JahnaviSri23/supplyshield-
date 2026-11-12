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

The frozen core and weather join are complete. A training-only dispatch-capacity
proxy and descriptive rain-delay comparisons are available; neither represents
measured physical capacity or establishes a causal weather effect.
See assumptions.md for selection rules and limitations.

- src/estimate_capacities.py: estimates training-only dispatch capacities and exports optimizer edge statistics.
- data/processed/hub_daily_departures.csv: daily outgoing core-leg counts, including zero days.

After rebuilding the core, run:

    python -m src.estimate_capacities

- src/rain_checks.py: checks core export fields and runs training-only descriptive rain comparisons.
- data/processed/rain_threshold_sensitivity.csv: results at 1, 5 and 10 mm thresholds.
- data/processed/rain_lane_sensitivity.csv: individual lane comparisons and observation-day counts.
- docs/rain_analysis.md: rain-comparison methods, results and limitations.

## Core exports: columns and training rules

Run `python -m src.estimate_capacities` after core selection.
Core selection can recreate the minimal edge file; this export
step restores the optimizer columns.

### core_edges.csv

| Column | Meaning |
|---|---|
| source, destination | Directed lane's hub identifiers |
| trips | Distinct training-trip count used for frozen lane membership; includes subsequent legs belonging to those trips |
| median_actual_time | Median actual travel time, in minutes, from eligible completed training legs |
| median_ratio | Median actual_time_min / osrm_time_min |
| p90_ratio | 90th percentile of that ratio, using linear interpolation |
| distance_km | Median OSRM route distance in kilometres; not straight-line distance |
| stats_legs | Number of valid completed training legs supporting these statistics |
| stats_cutoff_exclusive | Outcomes on or after this date are excluded |
| source_center, destination_center | Compatibility aliases for source and destination |
| leg_count, trip_count | Original frozen-core membership counts |

Travel statistics use trips created within 12–25 September 2018,
with departure and completion also within that window. Completion
must not precede departure. Actual time must be finite and nonnegative,
OSRM time finite and positive, and distance finite and nonnegative.
A lane without eligible observations retains missing statistics;
later-period outcomes are never substituted.

### core_nodes.csv

| Column | Meaning |
|---|---|
| hub, name, state | Hub identifier and supplied descriptive location |
| lat, lon | Approximate latitude and longitude in decimal degrees |
| location_quality | approximate_location_not_independently_validated, or unresolved |
| warehouse_location_verified | False: exact warehouse coordinates have not been verified |
| coordinate_method | Preserved provenance of the coordinate assignment |
| review_evidence | Existing review notes; not automatically proof of independent validation |
| located | Whether a finite, globally valid coordinate pair is available |
| legs_per_day_p95 | Linear p95 of daily outgoing core-leg counts across all 14 training dates, including zero days |
| capacity_est | Ceiling of legs_per_day_p95, in outgoing truck legs/day |
| observed_days | Number of calendar dates used: 14 |
| active_days | Dates with at least one observed departure |
| capacity_unit, capacity_method | Units and estimation rule |

Dispatch capacity uses departures on 12–25 September 2018.
It is an observed-throughput proxy for the selected core, not a
verified warehouse maximum. Approximate coordinates are not
warehouse navigation locations. Numeric coordinate validity does
not establish that a city or state assignment is correct.

## Map exports

Run: python -m src.export_map

- map_hubs.csv: 95 approximate hub markers with location-quality labels.
- map_lanes.csv: 264 lanes with coordinates for both endpoints.
- map_unresolved_hubs.csv: 5 hubs excluded from map markers.

These exports do not modify research coordinates or weather data.
Markers are not verified warehouse addresses.
Lane lines represent network connections, not road routes.
The research core retains all 100 hubs and 292 lanes.

## Historical lagged-weather handoff

Run: python -m src.make_lagged_weather

- leg_weather_lag1.csv: all 26,369 legs with master split assignments,
  previous-calendar-day source rainfall and missingness indicators.
- weather_lag1_coverage.csv: coverage by train/calibration/test split.

Proposed prediction timestamp: individual-leg od_start_time.
Naive journey timestamps are assumed to use Asia/Kolkata local time.
Model inputs: source_rain_prev_day_mm and source_rain_prev_day_missing.
Other exported columns support joining/auditing, not automatic model input.

Missing rainfall remains missing. Any imputation must be fitted on
training data only. Baseline and weather models must be compared on
identical evaluation journeys.

ERA5 publication timestamps are unavailable. This is a historical
lagged-weather experiment, not verified real-time prediction.