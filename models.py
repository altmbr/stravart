from datetime import timedelta
from location_service import get_location_details


def format_activity_summary(activity, index: int):
    """Format an activity for display in the selection menu."""
    # Extract basic activity info
    name = getattr(activity, 'name', 'Unknown Activity')
    distance_meters = getattr(activity, 'distance', 0)
    distance_miles = round(distance_meters / 1609.34, 2)
    
    # Get heart rate if available
    heart_rate_info = ""
    avg_heartrate = getattr(activity, 'average_heartrate', None)
    if avg_heartrate:
        heart_rate_info = f", {int(avg_heartrate)} BPM"
    
    # Get date and format it nicely
    start_date = getattr(activity, 'start_date_local', None)
    date_str = start_date.strftime('%Y-%m-%d %H:%M') if start_date else 'Unknown Date'
    
    # Get location if available
    location = ""
    start_latlng = getattr(activity, 'start_latlng', None)
    if start_latlng:
        # Extract coordinates
        try:
            if hasattr(start_latlng, 'lat') and hasattr(start_latlng, 'lng'):
                lat, lng = start_latlng.lat, start_latlng.lng
            elif isinstance(start_latlng, (list, tuple)) and len(start_latlng) >= 2:
                lat, lng = float(start_latlng[0]), float(start_latlng[1])
            elif hasattr(start_latlng, 'root') and isinstance(start_latlng.root, (list, tuple)) and len(start_latlng.root) >= 2:
                lat, lng = float(start_latlng.root[0]), float(start_latlng.root[1])
            
            # Look up location
            if 'lat' in locals() and 'lng' in locals():
                location_name = get_location_details(lat, lng)
                if location_name:
                    location = f" in {location_name}"
        except Exception:
            pass  # Silently continue if location lookup fails
    
    # Format the summary
    return f"{index}. {date_str}: {name} - {distance_miles} miles{heart_rate_info}{location}"