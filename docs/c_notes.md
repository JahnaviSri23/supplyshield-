# Safe-Plan & Risk Analysis (Hub D Capacity Uncertainty)

## Decision Rule: Express Van Utilization
The optimizer routes flow through the express van only when the express van cost per parcel is strictly less than the penalty for an undelivered parcel (20).

## Safe-Plan Paragraph (CVaR Context)
A baseline planning model that assumes Hub D can consistently handle 60 parcels will route up to 60 units through it to minimize daily operating costs. However, on days when Hub D's capacity drops to 30 or 0, this aggressive baseline causes severe capacity overflows and massive penalty spikes.

Conditional Value at Risk (CVaR) is not the single absolute worst-case scenario; rather, it represents the expected average cost across the worst slice of outcomes (e.g., the worst 20% of days). A CVaR-optimized plan proactively diverts volume to slightly higher-cost secondary paths, effectively removing catastrophic cost spikes on bad days while accepting a small increase in standard operating costs.