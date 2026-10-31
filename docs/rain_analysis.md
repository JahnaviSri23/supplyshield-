# Training-only rain comparison

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

```text
 rain_threshold_mm  eligible_legs  dry_legs  rainy_legs  comparable_lanes  represented_legs  median_difference  positive_lane_pct  multi_day_lanes  multi_day_median_difference
               1.0           5118      1479        2156               113              2179            -0.0058            47.7876              110                      -0.0056
               5.0           5118      1479         906                81              1471            -0.0048            49.3827               79                       0.0221
              10.0           5118      1479         558                54              1134             0.0594            62.9630               44                       0.0468
```
### Rain comparison finding

Training-only within-lane comparisons showed near-zero median differences
at rainfall thresholds of 1 and 5 mm. At 10 mm, the median travel-time-ratio
difference was +0.0594 across 54 lanes, with 62.96% showing an increase.
Requiring at least two dates per condition retained 44 lanes and a positive
median difference of +0.0468.

These descriptive results suggest a possible association under heavier
rainfall, but do not establish causation or statistical significance.
The lane sample changes with the rainfall threshold. Weather-based
capacity reductions or delay penalties have not been calibrated from
these results.