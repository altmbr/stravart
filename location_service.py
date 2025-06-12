def get_location_details(lat, lng) -> str:
    """
    Get the city, state/province, and country for a given latitude and longitude.
    
    Instead of using an API, we'll use a simple lookup based on coordinate ranges
    for common running locations.
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        str: A location name (e.g., "Toronto, Canada")
    """
    if not lat or not lng:
        return None
    
        
    try:
        # Force coordinate conversion to float just in case
        lat = float(lat)
        lng = float(lng)
        
        # Simple location lookup table based on coordinate ranges
        # Format: ((min_lat, max_lat), (min_lng, max_lng), "Location Name")
        location_ranges = [
            # Toronto area
            ((43.6, 43.8), (-79.5, -79.2), "Toronto, Canada"),
            
            # Montreal area - expanded range to catch more of the city and suburbs
            ((45.4, 45.7), (-73.7, -73.4), "Montreal, Canada"),
            
            # New York City - expanded to include all boroughs
            ((40.5, 40.92), (-74.25, -73.68), "New York City, USA"),
            
            # San Francisco proper + parts of Bay Area
            ((37.7, 37.9), (-122.5, -122.3), "San Francisco, USA"),
            
            # Los Angeles metro area
            ((33.7, 34.2), (-118.5, -118.1), "Los Angeles, USA"),
            
            # Boston area
            ((42.3, 42.4), (-71.1, -70.9), "Boston, USA"),
            
            # Chicago area
            ((41.8, 42.0), (-87.8, -87.5), "Chicago, USA"),
            
            # London area
            ((51.4, 51.6), (-0.2, 0.1), "London, UK"),
            
            # Paris area
            ((48.8, 48.9), (2.2, 2.4), "Paris, France"),
            
            # Berlin area
            ((52.4, 52.6), (13.3, 13.5), "Berlin, Germany"),
        ]
        
        # Check if coordinates fall within any known range
        for (lat_range, lng_range, location) in location_ranges:
            if lat_range[0] <= lat <= lat_range[1] and lng_range[0] <= lng <= lng_range[1]:
                return location
        
        # If no match, we can return a general "based on coordinates" message
        coords_rounded = f"{lat:.2f}, {lng:.2f}"
        return f"coordinates {coords_rounded}"
        
    except Exception as e:
        print(f"Error determining location: {e}")
        return None


def get_run_location(activity) -> tuple[float, float]:
    """
    Extract the average latitude and longitude from the run activity.
    Uses the start and end points to calculate the average location.
    
    Returns:
        tuple[float, float]: (avg_latitude, avg_longitude) or (None, None) if location data isn't available
    """
    try:
        # Check if we have both start and end coordinates
        start_latlng = getattr(activity, 'start_latlng', None)
        end_latlng = getattr(activity, 'end_latlng', None)
        
        
        # Calculate average location
        if start_latlng and end_latlng:
            # For LatLng objects, extract lat and lng attributes
            if hasattr(start_latlng, 'lat') and hasattr(start_latlng, 'lng'):
                start_lat = start_latlng.lat
                start_lng = start_latlng.lng
            # For list/tuple representation
            elif isinstance(start_latlng, (list, tuple)) and len(start_latlng) >= 2:
                start_lat = float(start_latlng[0])
                start_lng = float(start_latlng[1])
            # For objects with a "root" attribute containing lat/lng
            elif hasattr(start_latlng, 'root') and isinstance(start_latlng.root, (list, tuple)) and len(start_latlng.root) >= 2:
                start_lat = float(start_latlng.root[0])
                start_lng = float(start_latlng.root[1])
            else:
                return None, None
                
            # Same for end point
            if hasattr(end_latlng, 'lat') and hasattr(end_latlng, 'lng'):
                end_lat = end_latlng.lat
                end_lng = end_latlng.lng
            elif isinstance(end_latlng, (list, tuple)) and len(end_latlng) >= 2:
                end_lat = float(end_latlng[0])
                end_lng = float(end_latlng[1])
            elif hasattr(end_latlng, 'root') and isinstance(end_latlng.root, (list, tuple)) and len(end_latlng.root) >= 2:
                end_lat = float(end_latlng.root[0])
                end_lng = float(end_latlng.root[1])
            else:
                return None, None
            
            # Calculate averages
            avg_lat = (start_lat + end_lat) / 2
            avg_lng = (start_lng + end_lng) / 2
            
            return avg_lat, avg_lng
        
        # If we don't have both start and end, try to use start point only
        elif start_latlng:
            if hasattr(start_latlng, 'lat') and hasattr(start_latlng, 'lng'):
                return start_latlng.lat, start_latlng.lng
            elif isinstance(start_latlng, (list, tuple)) and len(start_latlng) >= 2:
                return float(start_latlng[0]), float(start_latlng[1])
            elif hasattr(start_latlng, 'root') and isinstance(start_latlng.root, (list, tuple)) and len(start_latlng.root) >= 2:
                return float(start_latlng.root[0]), float(start_latlng.root[1])
            
        return None, None
    except Exception as e:
        print(f"Error getting run location: {e}")
        return None, None