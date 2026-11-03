# Baseline-relative rain analysis

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

```text
rain_group  legs  median_excess  disrupted_count  disrupted_pct
       dry  1442        -0.1165               95         6.5881
     light  3022        -0.0122              237         7.8425
     heavy   541        -0.0611               53         9.7967
```

Among completed training core journeys with source weather, the baseline-relative disrupted share was 6.59% on dry days and 9.80% on days with at least 10 mm of rain; this descriptive comparison does not establish that rain caused the difference.
