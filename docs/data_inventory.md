# SupplyShield — Data Inventory

## Delhivery

- Download location: https://www.kaggle.com/code/payaldhokane/supplychain-insights/input?select=delhivery_data.csv
- License: Not stated in the supplied dataset description.
- Data origin: Delhivery logistics case-study dataset; real or synthetic status not confirmed.
- Column documentation: Data dictionary supplied with the dataset.
- Original rows: 144,867
- Original columns: 24
- Trip creation date range: 12 September 2018 to 3 October 2018
- Unique trips: 14,817
- Processed journey legs: 26,369
- Unique hubs: 1,657
- Directed lanes: 2,783
- Lanes with at least 30 distinct trips: 99

### Column uses

- Nodes: source_center, destination_center
- Location labels: source_name, destination_name
- Edges: directed source_center → destination_center pairs
- Trip identifier: trip_uuid
- Time information: trip_creation_time, od_start_time, od_end_time
- Travel-time comparison: actual_time and osrm_time
- Routing distance estimate: osrm_distance
- Route category: route_type

### Processing

Scan records were grouped by trip ID, source, destination,
and OD start/end timestamps. Maximum cumulative travel times
were used within each group.

delay_ratio = actual_time / osrm_time

This ratio compares observed travel time with an OSRM estimate;
it does not measure lateness against a promised delivery date.

### Outputs

- data/processed/legs.csv
- data/processed/lanes.csv
- docs/delay_ratio_hist.png

## Olist

- Original publisher: Olist
- Original source: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- Download location: https://github.com/Suhas5497/ecommerce-sql-analytics/tree/main/data
- License: CC BY-NC-SA 4.0
- Data origin: Real, anonymised commercial order data from Olist, covering 2016–2018.
- Verification note: Original dataset description and license verified; the GitHub copy has not been checked against the original files.
-- Original rows: 99,441
- Usable orders with both delivery dates: 96,476
- Purchase date range: 4 September 2016 to 17 October 2018

### Column uses

- Order identifier: order_id
- Date coverage: order_purchase_timestamp
- Actual delivery: order_delivered_customer_date
- Estimated delivery: order_estimated_delivery_date
- Purpose: separate comparison of customer delivery lateness;
  not direct validation of Delhivery travel-time predictions

### Processing and results

Orders missing either delivery date were excluded.

delay_days = actual delivery timestamp minus estimated delivery
timestamp, expressed using pandas .dt.days (rounded down).

- Mean: -11.876881 days
- Median: -12 days
- 90th percentile: -2 days
- 95th percentile: 3 days
- 99th percentile: 18 days
- Minimum: -147 days
- Maximum: 188 days

### Output

- docs/olist_delay_hist.png

## Limitations

- Delhivery and Olist measure different types of delay.
- Extreme values have been retained for later investigation.
- Histogram clipping affects display only, not the saved data.
- Network connectivity has not yet been checked.
- No prediction models have been trained.