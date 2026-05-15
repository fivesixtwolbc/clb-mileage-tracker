import json
import csv
from datetime import datetime

def generate_mileage_report(json_path, output_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Cutoff for the last 6 months (from May 15, 2026)
    cutoff_date = datetime(2025, 11, 15)
    
    # Standard CLB tracking headers
    headers = ["Date", "Traveled From Complete Address", "Traveled To Complete Address", "Total Mileage"]
    report_rows = []
    
    for entry in data:
        start_time_str = entry.get('startTime', '')
        if not start_time_str:
            continue
            
        try:
            # Parse the standard format from the Timeline
            start_dt = datetime.strptime(start_time_str[:19], "%Y-%m-%dT%H:%M:%S")
            if start_dt < cutoff_date:
                continue
        except ValueError:
            continue

        # Extract only the segments where you were driving
        if 'activity' in entry:
            activity = entry['activity']
            top_candidate = activity.get('topCandidate', {})
            
            if top_candidate.get('type') == 'in passenger vehicle':
                distance_meters = float(activity.get('distanceMeters', 0))
                miles = distance_meters * 0.000621371
                
                if miles > 0:
                    report_rows.append({
                        "Date": start_dt.strftime('%Y-%m-%d'),
                        "Traveled From Complete Address": "Review Timeline", # Copilot can map the preceding 'visit' geo-coordinates here
                        "Traveled To Complete Address": "Review Timeline",   # Copilot can map the following 'visit' geo-coordinates here
                        "Total Mileage": round(miles, 1)
                    })

    # Generate the reimbursement CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(report_rows)

    print(f"Extraction complete! Logged {len(report_rows)} driving segments to {output_path}.")

generate_mileage_report('G.Cruz GoogleTimeline.json', 'CLB_Mileage_6_Months.csv')
