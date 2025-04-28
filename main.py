import os
import random
import requests
import base64
import mimetypes
import json
from datetime import datetime, timezone, timedelta
from PIL import Image

import openai
from dotenv import load_dotenv
from stravalib import Client

"""
Generate and attach a summary image for the athlete's most recent Strava run.

Workflow:
1. Refresh Strava access token using the stored refresh token.
2. Fetch the athlete's most recent activity (limit=1).
3. Analyze a photo of the runner using GPT-4o Vision.
4. Build an image generation prompt that summarises the run.
5. Generate an image with OpenAI (imagegen) based on the prompt.
6. Download the generated image locally.
7. Provide instructions for adding the image to Strava activity.
"""

load_dotenv()  # Load environment variables from a .env file if present

# Required environment variables
STRAVA_CLIENT_ID = int(os.getenv("STRAVA_CLIENT_ID"))
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "AIzaSyC_By4kdX7WVdO0bultrhAl36hV5blIjkg")

# Optional settings
USER_IMAGES_DIR = os.getenv("USER_IMAGES_DIR", "/Users/bryanaltman/StravaPictures")
BRYAN_IMAGES_DIR = os.getenv("BRYAN_IMAGES_DIR", "bryanphotos")  # Directory with photos of Bryan
IMAGE_SIZE = os.getenv("OPENAI_IMAGE_SIZE", "1024x1024")
IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")  # Latest OpenAI image model
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "generated_images")

"""
Generate and attach a summary image for the athlete's most recent Strava run.

Workflow:
1. Refresh Strava access token using the stored refresh token.
2. Fetch the athlete's most recent activity (limit=1).
3. Analyze a photo of the runner using GPT-4o Vision.
4. Build an image generation prompt that summarises the run.
5. Generate an image with OpenAI (imagegen) based on the prompt.
6. Download the generated image locally.
7. Provide instructions for adding the image to Strava activity.
"""

# Basic validation to catch missing credentials early
for var_name in ("STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN", "OPENAI_API_KEY"):
    if not globals()[var_name]:
        raise EnvironmentError(f"Environment variable {var_name} is not set.")

# ------ STRAVA API FUNCTIONS ------

def get_strava_access_token() -> str:
    """Exchange the refresh token for a short‑lived access token."""
    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": STRAVA_REFRESH_TOKEN,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def get_last_run(client: Client):
    """Return the most recent activity (run) for the authenticated athlete."""
    # Get the most recent activity
    activities = list(client.get_activities(limit=1))
    if not activities:
        raise RuntimeError("No activities found for athlete.")
    
    activity = activities[0]
    
    # Ensure we have detailed information by requesting the full activity
    # This will include splits and detailed metrics
    detailed_activity = client.get_activity(activity.id)
    
    return detailed_activity

def get_recent_runs(client: Client, limit: int = 5):
    """Return the most recent activities (runs) for the authenticated athlete."""
    # Get recent activities
    activities = list(client.get_activities(limit=limit))
    if not activities:
        raise RuntimeError("No activities found for athlete.")
    
    return activities

def get_activity_details(client: Client, activity_id: int):
    """Fetch detailed information for a specific activity."""
    # Request the full activity with detailed information
    detailed_activity = client.get_activity(activity_id)
    return detailed_activity

# ------ IMAGE ANALYSIS FUNCTIONS ------

def describe_runner_photo(path: str) -> str:
    """Use GPT-4o-Vision to analyze runner photo for the imagegen prompt."""
    # Read and encode the image
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    
    # Determine the MIME type
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    
    # Set up OpenAI client
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ------ IMAGE GENERATION FUNCTIONS ------

def build_prompt(activity, runner_description: str | None = None) -> str:
    """Construct a text prompt for imagegen summarising the activity."""
    # Get activity name/title
    activity_name = getattr(activity, 'name', "Activity")
    
    # Get activity type and convert to string to safely use lower()
    activity_type_obj = getattr(activity, 'type', 'Run')
    if hasattr(activity_type_obj, 'root'):
        activity_type = str(activity_type_obj.root)
    else:
        activity_type = str(activity_type_obj)
    
    is_run_activity = activity_type.lower() == 'run'
    
    # Format duration in hours:minutes:seconds
    moving_time_obj = activity.moving_time
    # Format time in a more readable way (HH:MM:SS)
    if isinstance(moving_time_obj, timedelta):
        total_seconds = moving_time_obj.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        if hours > 0:
            duration_formatted = f"{hours}:{minutes:02d}:{seconds:02d} hours"
        else:
            duration_formatted = f"{minutes}:{seconds:02d} minutes"
    else:
        duration_formatted = str(moving_time_obj)
    
    # Get heart rate data if available
    avg_heartrate = getattr(activity, 'average_heartrate', None)
    
    # Get location information
    avg_lat, avg_lng = get_run_location(activity)
    location_name = ""
    if avg_lat and avg_lng:
        location_name = get_location_details(avg_lat, avg_lng)
    
    # Only process these for run-type activities
    if is_run_activity:
        # Extract activity stats and convert to US customary units
        distance_meters = activity.distance
        distance_km = round(distance_meters / 1000.0, 2)
        distance_miles = round(distance_meters / 1609.34, 2)
        
        # Calculate pace from moving_time, handling both timedelta and integer seconds
        total_seconds = 0
        if isinstance(moving_time_obj, timedelta):
            total_seconds = moving_time_obj.total_seconds()
        elif isinstance(moving_time_obj, int):
            total_seconds = moving_time_obj
        
        # Calculate pace in min/mile (U.S. customary units)
        if total_seconds > 0 and distance_miles > 0:
            pace_seconds_per_mile = total_seconds / distance_miles
            pace_minutes = int(pace_seconds_per_mile // 60)
            pace_seconds = int(pace_seconds_per_mile % 60)
            pace_str = f"{pace_minutes}:{pace_seconds:02d} min/mile"  # U.S. customary pace
        else:
            pace_str = "unknown pace"
        
        # Calculate elevation in feet (U.S. customary units)
        total_elevation_gain_meters = getattr(activity, 'total_elevation_gain', 0)
        total_elevation_gain_feet = round(total_elevation_gain_meters * 3.28084)  # Convert to feet
        
        # Analyze run type and splits
        run_type = analyze_run_type(activity)
        activity_description = run_type.lower()
    else:
        # For non-run activities, use the activity type as the description
        activity_description = activity_type.lower()
        distance_miles = None
        pace_str = None
        total_elevation_gain_feet = None
    
    # Initialize prompt with the activity type and title
    prompt = f"Create a stylized {activity_description} poster celebrating a recent {activity_description}. "
    prompt += f"Activity title: '{activity_name}'. "
    
    # For run activities, include distance, pace, and elevation
    if is_run_activity:
        prompt += f"The run was {distance_miles} miles with duration {duration_formatted} and avg pace {pace_str}. "
        prompt += f"The run included {total_elevation_gain_feet} feet of elevation gain. "
    else:
        # For non-run activities, just include duration
        prompt += f"The activity duration was {duration_formatted}. "
    
    # Add heart rate information if available
    if avg_heartrate:
        prompt += f"Average heart rate during the {activity_description} was {int(avg_heartrate)} BPM. "
    
    # Add location information
    if location_name:
        prompt += f"The {activity_description} took place in {location_name}. Show visual elements or scenery that represents this location. "
    
    # Add reference to runner description if provided
    if runner_description:
        prompt += f"The athlete should look like the person in the reference image, but in appropriate {activity_description} gear. Keep the same facial features and general appearance, but show them in motion with appropriate attire. "
    
    # Add usage disclaimer
    prompt += "This is for personal, non-commercial use only. "
    
    # Add style guidance for more modern, attractive posters
    prompt += "Overall style should evoke accomplishment and athleticism, with dynamic motion and inspirational feel. "
    
    # Add instructions for integrating stats
    stats_prompt = ""
    
    # For run activities, include distance and pace
    if is_run_activity and distance_miles and pace_str:
        stats_prompt += f"the distance ({distance_miles} miles) and pace ({pace_str})"
    
    # For all activities, add heart rate if available
    if avg_heartrate:
        if stats_prompt:
            stats_prompt += f" and heart rate ({int(avg_heartrate)} BPM)"
        else:
            stats_prompt += f"heart rate ({int(avg_heartrate)} BPM)"
    
    # Only add the stats visualization instruction if we have stats to visualize
    if stats_prompt:
        prompt += f"Add visual elements showing {stats_prompt} statistics artistically integrated into the design. "
        prompt += "Do not duplicate any numbers in the image - each statistic should appear only once. "
    
    # Final reminder that this is fictional
    prompt += "This is purely fictional artwork for personal use."
    
    return prompt

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
        except Exception as e:
            print(f"Error getting location: {e}")
    
    # Format the summary
    return f"{index}. {date_str}: {name} - {distance_miles} miles{heart_rate_info}{location}"

def select_activity(activities):
    """Display a menu of activities and let the user select one."""
    print("\nYour recent runs:")
    print("----------------")
    
    # Show each activity with details
    for i, activity in enumerate(activities, 1):
        print(format_activity_summary(activity, i))
    
    # Get user selection
    while True:
        try:
            choice = input("\nSelect a run to generate artwork for (1-5, or 'q' to quit): ")
            if choice.lower() == 'q':
                return None
                
            choice_num = int(choice)
            if 1 <= choice_num <= len(activities):
                return activities[choice_num - 1]
            else:
                print(f"Please enter a number between 1 and {len(activities)}")
        except ValueError:
            print("Please enter a valid number or 'q' to quit")

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
    
    # Print the coordinates we're using
    print(f"Looking up location for coordinates: ({lat}, {lng})")
        
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
                print(f"Location identified: {location}")
                return location
        
        # If no match, we can return a general "based on coordinates" message
        coords_rounded = f"{lat:.2f}, {lng:.2f}"
        print(f"No specific location identified for {coords_rounded}")
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
        
        # Debug log the location data
        print(f"Start location: {start_latlng}")
        print(f"End location: {end_latlng}")
        
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
                print(f"Unrecognized start location format: {type(start_latlng)}")
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
                print(f"Unrecognized end location format: {type(end_latlng)}")
                return None, None
            
            # Calculate averages
            avg_lat = (start_lat + end_lat) / 2
            avg_lng = (start_lng + end_lng) / 2
            
            print(f"Average location: ({avg_lat}, {avg_lng})")
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

def analyze_run_type(activity) -> str:
    """
    Analyze the activity's split data to determine the type of run.
    
    Different run types have characteristic split patterns:
    - Long Run: > 5 miles and at or slower than 7:30 pace
    - Intervals: Clear alternating pattern of fast/slow segments
    - Tempo Run: Between 3-10 miles at > 7:30 pace and relatively consistent
    """
    # Initialize as fallback
    run_type = "run"
    
    try:
        # First check run name for common interval workout indicators
        if hasattr(activity, 'name'):
            name_lower = activity.name.lower()
            interval_keywords = ['interval', 'repeat', 'x', '400', '800', '1000', '1200', '1600', 'mile repeat', 'hiit']
            
            # Check for high intensity interval workout keywords
            hiit_keywords = ['hiit', 'high intensity', 'sprint', 'tabata']
            for keyword in hiit_keywords:
                if keyword in name_lower:
                    return "High Intensity Interval Training"
            
            # Check if any interval keywords are in the run name
            for keyword in interval_keywords:
                if keyword in name_lower:
                    return "Interval Run"
        
        # Get splits if available
        splits = []
        if hasattr(activity, 'splits_metric') and activity.splits_metric:
            splits = activity.splits_metric
        
        # Not enough data for analysis
        if len(splits) < 3:
            return run_type
            
        # Extract pace data for each split
        paces = []
        for split in splits:
            if hasattr(split, 'average_speed') and split.average_speed > 0:
                # Convert speed to pace (seconds per km)
                pace_secs_per_km = 1000 / split.average_speed
                paces.append(pace_secs_per_km)
        
        if not paces:
            return run_type
            
        # Calculate stats for analysis
        avg_pace = sum(paces) / len(paces)
        pace_variation = max(paces) - min(paces)
        pace_std_dev = (sum((p - avg_pace) ** 2 for p in paces) / len(paces)) ** 0.5
        
        # Calculate pace changes between consecutive splits
        pace_changes = [abs(paces[i] - paces[i-1]) for i in range(1, len(paces))]
        avg_change = sum(pace_changes) / len(pace_changes) if pace_changes else 0
        
        # Detect pattern of alternating fast/slow for intervals
        alternating_pattern = True
        for i in range(2, len(paces)):
            # If three consecutive splits don't show alternating pattern
            if (paces[i] > paces[i-1] and paces[i-1] > paces[i-2]) or \
               (paces[i] < paces[i-1] and paces[i-1] < paces[i-2]):
                alternating_pattern = False
                break
        
        # Get total distance in miles
        distance_miles = activity.distance / 1609.34
        
        # Convert avg pace to min/mile for comparison (7:30 pace = 450 seconds per mile)
        avg_pace_secs_per_mile = avg_pace * 1.60934  # Convert secs/km to secs/mile
        
        # New decision logic based on the specified criteria
        if alternating_pattern and pace_variation > avg_pace * 0.2:
            # Clear alternating pattern of fast/slow segments
            run_type = "Interval Run"
        elif distance_miles > 5 and avg_pace_secs_per_mile >= 450:
            # > 5 miles and at or slower than 7:30 min/mile
            run_type = "Easy Run"
        elif 3 <= distance_miles <= 10 and avg_pace_secs_per_mile < 450 and pace_std_dev < avg_pace * 0.1:
            # Between 3-10 miles at faster than 7:30 pace and relatively consistent
            run_type = "Tempo Run"
        elif distance_miles > 10 and avg_pace_secs_per_mile >= 450:
            # > 10 miles and at or faster than 7:30 pace
            run_type = "Long Run"
        elif distance_miles <= 5 and avg_pace_secs_per_mile < 450:
            # Short and fast runs that aren't intervals
            run_type = "Tempo Run" 
        
        return run_type
    except Exception as e:
        print(f"Error analyzing run type: {e}")
        return run_type

def generate_image(prompt: str) -> str:
    """Generate an image via the OpenAI image generation API (gpt-image-1). Returns the hosted URL or raises with detailed diagnostics."""
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    print(f"OpenAI SDK version: {openai.__version__}")
    
    print(f"Sending image generation request. Model=gpt-image-1, Size={IMAGE_SIZE}")
    try:
        # Open the reference image
        with open("bryanphotos/Bryan.jpg", "rb") as image_file:
            response = client.images.edit(
                model="gpt-image-1",  # Using the same model as the working example
                image=image_file,
                prompt=prompt
            )
        
        # Log the full response for debugging
        print("\nFull API Response:")
        print(f"Response type: {type(response)}")
        print(f"Response attributes: {dir(response)}")
        print(f"Response data: {response.data}")
        
        if not response.data:
            print("No data in response")
            raise RuntimeError("Image generation returned no data")
            
        # Get the base64 data from the response
        image_base64 = response.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)
        
        # Save the image to a file
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        local_path = os.path.join(OUTPUT_DIR, f"strava_run_{timestamp}.png")
        
        # Create output directory if it doesn't exist
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
            
        with open(local_path, "wb") as f:
            f.write(image_bytes)
            
        return local_path
        
    except openai.BadRequestError as bre:
        print("\nBadRequestError details:")
        print(f"Error type: {type(bre)}")
        print(f"Error attributes: {dir(bre)}")
        print(f"Error body: {getattr(bre, 'body', '<no body>')}")
        raise
    except openai.OpenAIError as e:
        print(f"\nOpenAI API error: {e.__class__.__name__}: {e}")
        print(f"Error type: {type(e)}")
        print(f"Error attributes: {dir(e)}")
        raise
    except Exception as e:
        print(f"\nUnexpected error: {type(e)}: {e}")
        print(f"Error attributes: {dir(e)}")
        raise

def download_image(url: str) -> str:
    """Download the image to disk and return the local file path."""
    # Safety check for None URL
    if not url:
        raise ValueError("Cannot download from empty URL")
        
    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # Download the image
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    # Save to file
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    local_path = os.path.join(OUTPUT_DIR, f"strava_run_{timestamp}.png")
    
    with open(local_path, "wb") as f:
        f.write(response.content)
    
    return local_path

def get_runner_image() -> tuple[str | None, str | None]:
    """Get a runner image and its description."""
    image_path = None
    description = None
    
    # Try Bryan's photos directory first, then fallback to user images
    if os.path.exists(BRYAN_IMAGES_DIR) and os.listdir(BRYAN_IMAGES_DIR):
        image_path = random.choice([
            os.path.join(BRYAN_IMAGES_DIR, f) 
            for f in os.listdir(BRYAN_IMAGES_DIR) 
            if os.path.isfile(os.path.join(BRYAN_IMAGES_DIR, f))
        ])
        print(f"Selected runner image: {image_path}")
    elif os.path.exists(USER_IMAGES_DIR):
        image_path = random.choice([
            os.path.join(USER_IMAGES_DIR, f) 
            for f in os.listdir(USER_IMAGES_DIR) 
            if os.path.isfile(os.path.join(USER_IMAGES_DIR, f))
        ])
        print(f"Selected runner image from user directory: {image_path}")
    
    # Get description if we have an image
    if image_path:
        try:
            description = describe_runner_photo(image_path)
        except Exception as e:
            print(f"Error analyzing runner photo: {e}")
            print("Falling back to standard runner description")
    
    return image_path, description

# ------ MAIN WORKFLOW ------

def main():
    """Run the complete Strava Run Art workflow."""
    try:
        # 1. Connect to Strava API
        print("Fetching Strava access token...")
        access_token = get_strava_access_token()
        
        print("Initializing Strava client...")
        strava_client = Client(access_token=access_token)
        
        # 2. Get recent runs
        print("Fetching your recent runs...")
        recent_activities = get_recent_runs(strava_client, limit=5)
        
        # 3. Let user select which run to use
        selected_activity = select_activity(recent_activities)
        if not selected_activity:
            print("No activity selected. Exiting.")
            return 0
        
        # 4. Get detailed information for the selected activity
        print(f"Fetching detailed information for: {selected_activity.name} (ID: {selected_activity.id})")
        activity = get_activity_details(strava_client, selected_activity.id)
        
        # 5. Build prompt and generate image
        print("Building prompt for image generation...")
        prompt = build_prompt(activity)
        print(f"Generated prompt: {prompt}")
        
        print("Generating image with imagegen...")
        image_path = generate_image(prompt)
        print(f"Image saved locally at: {image_path}")
        
        # 6. Provide instructions for Strava (API doesn't allow direct photo uploads)
        print("\nNOTE: Your Strava token only has read permissions (not activity:write)")
        print("To manually add this image to your Strava activity:")
        print(f"1. Open the image at: {image_path}")
        print(f"2. Open your activity on Strava: https://www.strava.com/activities/{activity.id}")
        print("3. Click 'Add Photo' and upload the downloaded image")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    main()
