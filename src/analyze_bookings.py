#!/usr/bin/env python3
"""Clean synthetic accessible-travel bookings and generate KPI/report outputs.

Run from the repository root:
    python3 src/analyze_bookings.py
Uses Python standard library only.
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "raw_bookings.csv"
CLEAN = ROOT / "data" / "processed" / "cleaned_bookings.csv"
QUALITY = ROOT / "analysis" / "data_quality_log.csv"
METRICS = ROOT / "report" / "sample_metrics.json"
REPORT = ROOT / "report" / "business_insights.md"

FIELDS = [
    "booking_id", "booking_date", "destination", "customer_id",
    "booking_value", "booking_status", "accessibility_type",
    "customer_rating", "travel_month",
]
VALID_STATUSES = {"Completed", "Cancelled", "Pending"}


def clean_rows(raw_rows):
    cleaned, quality_log, seen = [], [], set()
    for source_row, row in enumerate(raw_rows, start=2):
        issues = []
        booking_id = (row.get("booking_id") or "").strip()
        if not booking_id:
            quality_log.append({
                "source_row": source_row, "booking_id": "",
                "issue": "Missing booking_id", "action": "Excluded row",
            })
            continue
        if booking_id in seen:
            quality_log.append({
                "source_row": source_row, "booking_id": booking_id,
                "issue": "Duplicate booking_id",
                "action": "Excluded duplicate; first occurrence retained",
            })
            continue
        seen.add(booking_id)

        try:
            booking_date = date.fromisoformat((row.get("booking_date") or "").strip())
        except ValueError:
            quality_log.append({
                "source_row": source_row, "booking_id": booking_id,
                "issue": "Invalid booking_date", "action": "Excluded row",
            })
            continue

        destination = (row.get("destination") or "").strip().title()
        if not destination:
            quality_log.append({
                "source_row": source_row, "booking_id": booking_id,
                "issue": "Missing destination", "action": "Excluded row",
            })
            continue

        try:
            booking_value = float(row.get("booking_value", ""))
            if booking_value < 0:
                raise ValueError("negative value")
        except (TypeError, ValueError):
            quality_log.append({
                "source_row": source_row, "booking_id": booking_id,
                "issue": "Invalid or negative booking_value",
                "action": "Excluded row",
            })
            continue

        status = (row.get("booking_status") or "").strip().title()
        if status == "Complete":
            status = "Completed"
            issues.append("Standardized booking_status from Complete to Completed")
        if status not in VALID_STATUSES:
            quality_log.append({
                "source_row": source_row, "booking_id": booking_id,
                "issue": f"Unrecognized booking_status: {status}",
                "action": "Excluded row",
            })
            continue

        customer_id = (row.get("customer_id") or "").strip()
        if not customer_id:
            issues.append("Missing customer_id; retained as blank")

        rating_text = (row.get("customer_rating") or "").strip()
        rating = ""
        if rating_text and rating_text.upper() != "N/A":
            try:
                parsed_rating = float(rating_text)
                if not 1 <= parsed_rating <= 5:
                    raise ValueError("rating outside 1-5")
                rating = f"{parsed_rating:g}"
            except ValueError:
                issues.append("Invalid customer_rating; set to blank")
        elif rating_text.upper() == "N/A":
            issues.append("Non-numeric customer_rating; set to blank")

        if issues:
            quality_log.append({
                "source_row": source_row, "booking_id": booking_id,
                "issue": "; ".join(issues),
                "action": "Standardized or retained with missing optional value",
            })

        cleaned.append({
            "booking_id": booking_id,
            "booking_date": booking_date.isoformat(),
            "destination": destination,
            "customer_id": customer_id,
            "booking_value": f"{booking_value:.2f}",
            "booking_status": status,
            "accessibility_type": (row.get("accessibility_type") or "").strip(),
            "customer_rating": rating,
            "travel_month": booking_date.strftime("%Y-%m"),
        })
    return cleaned, quality_log


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    if not RAW.exists():
        raise FileNotFoundError(
            f"Raw data not found: {RAW}. Run this script from the project files."
        )
    with RAW.open(newline="", encoding="utf-8") as handle:
        raw_rows = list(csv.DictReader(handle))

    cleaned, quality_log = clean_rows(raw_rows)
    write_csv(CLEAN, FIELDS, cleaned)
    write_csv(QUALITY, ["source_row", "booking_id", "issue", "action"], quality_log)

    completed = [r for r in cleaned if r["booking_status"] == "Completed"]
    cancelled = [r for r in cleaned if r["booking_status"] == "Cancelled"]
    pending = [r for r in cleaned if r["booking_status"] == "Pending"]
    ratings = [float(r["customer_rating"]) for r in cleaned if r["customer_rating"]]
    revenue = sum(float(r["booking_value"]) for r in completed)
    destination_revenue = defaultdict(float)
    monthly_revenue = defaultdict(float)
    status_counts = defaultdict(int)
    for row in cleaned:
        status_counts[row["booking_status"]] += 1
        if row["booking_status"] == "Completed":
            value = float(row["booking_value"])
            destination_revenue[row["destination"]] += value
            monthly_revenue[row["travel_month"]] += value

    top_destination = max(destination_revenue.items(), key=lambda item: item[1], default=("N/A", 0))
    top_month = max(monthly_revenue.items(), key=lambda item: item[1], default=("N/A", 0))
    metrics = {
        "dataset_type": "Synthetic sample data; not Wheel the World's internal data",
        "raw_rows": len(raw_rows),
        "cleaned_rows": len(cleaned),
        "excluded_rows": len(raw_rows) - len(cleaned),
        "quality_log_entries": len(quality_log),
        "completed_bookings": len(completed),
        "cancelled_bookings": len(cancelled),
        "pending_bookings": len(pending),
        "total_completed_revenue": round(revenue, 2),
        "average_completed_booking_value": round(revenue / len(completed), 2) if completed else 0,
        "cancellation_rate_all_cleaned_bookings": round(len(cancelled) / len(cleaned) * 100, 2) if cleaned else 0,
        "average_valid_customer_rating": round(statistics.mean(ratings), 2) if ratings else None,
        "valid_ratings_count": len(ratings),
        "top_destination_by_completed_revenue": {
            "destination": top_destination[0], "revenue": round(top_destination[1], 2)
        },
        "top_month_by_completed_revenue": {
            "month": top_month[0], "revenue": round(top_month[1], 2)
        },
        "status_counts": dict(status_counts),
    }
    METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    report = f"""# Business Insights Report

## Data note

This report uses fictional sample data for a portfolio exercise. It is not based on Wheel the World's internal data and must not be interpreted as actual company performance.

## KPI summary

| Metric | Result |
|---|---:|
| Raw records | {metrics['raw_rows']} |
| Cleaned records | {metrics['cleaned_rows']} |
| Excluded records | {metrics['excluded_rows']} |
| Completed bookings | {metrics['completed_bookings']} |
| Cancelled bookings | {metrics['cancelled_bookings']} |
| Pending bookings | {metrics['pending_bookings']} |
| Completed-booking revenue | CAD ${metrics['total_completed_revenue']:,.2f} |
| Average completed booking value | CAD ${metrics['average_completed_booking_value']:,.2f} |
| Cancellation rate | {metrics['cancellation_rate_all_cleaned_bookings']:.2f}% |
| Average valid customer rating | {metrics['average_valid_customer_rating'] if metrics['average_valid_customer_rating'] is not None else 'Not available'} / 5 |

## Findings

1. **Destination:** {top_destination[0]} has the highest completed-booking revenue in this sample (CAD ${top_destination[1]:,.2f}).
2. **Month:** {top_month[0]} has the highest completed-booking revenue in this sample (CAD ${top_month[1]:,.2f}).
3. **Data quality:** {len(quality_log)} data quality log entries were recorded during validation. Review `analysis/data_quality_log.csv` for the source row, issue, and action.

## Suggested business follow-up

- Review destination-level performance alongside booking volume, accessibility type, and customer feedback before making marketing or inventory decisions.
- Monitor cancellation rate by month and destination to identify whether patterns persist over time.
- Agree on metric definitions and data quality rules with stakeholders before using this workflow for real operational reporting.

## Limitations

The dataset is synthetic, small, and randomly generated. It is not representative of actual customers or travel demand. Revenue is simplified to the booking value of completed records; refunds, fees, taxes, currency conversion, and booking-date versus travel-date differences are not modeled. These findings are descriptive of this sample only, not causal evidence or real-world company results.
"""
    REPORT.write_text(report, encoding="utf-8")

    print("Analysis complete.")
    print(f"Raw records: {len(raw_rows)}")
    print(f"Cleaned records: {len(cleaned)}")
    print(f"Excluded records: {len(raw_rows) - len(cleaned)}")
    print(f"Completed-booking revenue: CAD ${revenue:,.2f}")
    print(f"Outputs refreshed: {CLEAN.relative_to(ROOT)}, {QUALITY.relative_to(ROOT)},")
    print(f"                  {METRICS.relative_to(ROOT)}, {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
