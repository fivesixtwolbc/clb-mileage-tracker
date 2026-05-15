import json
import csv
from datetime import datetime
import math

# Location coordinates for frequently visited locations
LOCATIONS = {
    "CRS Admin": (33.804848, -118.168297),
    "Seaside Park": (33.772591, -118.201407),
    "Drake Park": (33.774900, -118.200155),
    "Cesar E Chavez Park": (33.772714, -118.199144),
    "The Home Depot": (33.801828, -118.165796),
    "Heartwell Park": (33.831304, -118.119921),
    "Cal Heights Music": (33.818775, -118.175399),
    "Long Beach City Hall": (33.768177, -118.196741),
    "Long Beach Senior Center": (33.771272, -118.176903),
    "Bixby Park": (33.765966, -118.167132),
    "Recreation Park": (33.774956, -118.135192),
    "Pan American Park": (33.841457, -118.130819),
    "Bixby Knolls Park": (33.840514, -118.179478),
    "Crossroads Pet Resort": (33.804881, -118.010426),
    "Orizaba Park": (33.785000, -118.157500),
}

RADIUS_MILES = 0.1


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two sets of coordinates using the Haversine formula.
    
    Args:
        lat1, lon1: First coordinate pair (latitude, longitude)
        lat2, lon2: Second coordinate pair (latitude, longitude)
    
    Returns:
        Distance in miles
    """
    R = 3959  # Earth's radius in miles
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def match_location(place_location_str):
    """
    Check if a placeLocation string (formatted as 'geo:LAT,LONG') matches any known location
    within the defined radius.
    
    Args:
        place_location_str: String formatted as 'geo:LAT,LONG'
    
    Returns:
        Location name if match found, 'Personal/Other' if not matched
    """
    if not place_location_str or not place_location_str.startswith('geo:'):
        return 'Personal/Other'
    
    try:
        # Parse the geo coordinates
        coords = place_location_str.replace('geo:', '').split(',')
        lat = float(coords[0])
        lon = float(coords[1])
    except (ValueError, IndexError):
        return 'Personal/Other'
    
    # Check distance to all known locations
    for location_name, (loc_lat, loc_lon) in LOCATIONS.items():
        distance = haversine_distance(lat, lon, loc_lat, loc_lon)
        if distance <= RADIUS_MILES:
            return location_name
    
    return 'Personal/Other'


def generate_mileage_report(json_path, output_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Cutoff for the last 6 months (from May 15, 2026)
    cutoff_date = datetime(2025, 11, 15)
    
    # Standard CLB tracking headers
    headers = ["Date", "Traveled From Complete Address", "Traveled To Complete Address", "Total Mileage"]
    report_rows = []
    
    for i, entry in enumerate(data):
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
                    # Match the previous visit location (where you traveled from)
                    traveled_from = 'Personal/Other'
                    if i > 0 and 'placeVisit' in data[i - 1]:
                        prev_location = data[i - 1]['placeVisit'].get('location', {})
                        place_location = prev_location.get('placeId')
                        if not place_location:
                            place_location = prev_location.get('geoCoordinates')
                            if place_location:
                                lat = place_location.get('latitude')
                                lon = place_location.get('longitude')
                                place_location = f'geo:{lat},{lon}'
                        if place_location:
                            traveled_from = match_location(place_location)
                    
                    # Match the current/next visit location (where you traveled to)
                    traveled_to = 'Personal/Other'
                    if i + 1 < len(data) and 'placeVisit' in data[i + 1]:
                        next_location = data[i + 1]['placeVisit'].get('location', {})
                        place_location = next_location.get('placeId')
                        if not place_location:
                            place_location = next_location.get('geoCoordinates')
                            if place_location:
                                lat = place_location.get('latitude')
                                lon = place_location.get('longitude')
                                place_location = f'geo:{lat},{lon}'
                        if place_location:
                            traveled_to = match_location(place_location)
                    
                    # Only log if at least one location matches
                    if traveled_from != 'Personal/Other' or traveled_to != 'Personal/Other':
                        report_rows.append({
                            "Date": start_dt.strftime('%Y-%m-%d'),
                            "Traveled From Complete Address": traveled_from,
                            "Traveled To Complete Address": traveled_to,
                            "Total Mileage": round(miles, 1)
                        })

    # Generate the reimbursement CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(report_rows)

    print(f"Extraction complete! Logged {len(report_rows)} driving segments to {output_path}.")

generate_mileage_report('G.Cruz GoogleTimeline.json', 'CLB_Mileage_6_Months.csv')
