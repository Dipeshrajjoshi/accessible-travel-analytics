# Business Insights Report

## Data note

This report uses fictional sample data for a portfolio exercise. It is not based on Wheel the World's internal data and must not be interpreted as actual company performance.

## KPI summary

| Metric | Result |
|---|---:|
| Raw records | 180 |
| Cleaned records | 176 |
| Excluded records | 4 |
| Completed bookings | 112 |
| Cancelled bookings | 31 |
| Pending bookings | 33 |
| Completed-booking revenue | CAD $87,249.05 |
| Average completed booking value | CAD $779.01 |
| Cancellation rate | 17.61% |
| Average valid customer rating | 4.18 / 5 |

## Findings

1. **Destination:** London has the highest completed-booking revenue in this sample (CAD $16,232.42).
2. **Month:** 2025-05 has the highest completed-booking revenue in this sample (CAD $12,143.93).
3. **Data quality:** 8 data quality log entries were recorded during validation. Review `analysis/data_quality_log.csv` for the source row, issue, and action.

## Suggested business follow-up

- Review destination-level performance alongside booking volume, accessibility type, and customer feedback before making marketing or inventory decisions.
- Monitor cancellation rate by month and destination to identify whether patterns persist over time.
- Agree on metric definitions and data quality rules with stakeholders before using this workflow for real operational reporting.

## Limitations

The dataset is synthetic, small, and randomly generated. It is not representative of actual customers or travel demand. Revenue is simplified to the booking value of completed records; refunds, fees, taxes, currency conversion, and booking-date versus travel-date differences are not modeled. These findings are descriptive of this sample only, not causal evidence or real-world company results.
