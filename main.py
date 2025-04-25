import os
import random
import requests
import base64
import mimetypes
import json
from datetime import datetime, timezone
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

# Optional settings
USER_IMAGES_DIR = os.getenv("USER_IMAGES_DIR", "/Users/bryanaltman/StravaPictures")
BRYAN_IMAGES_DIR = os.getenv("BRYAN_IMAGES_DIR", "bryanphotos")  # Directory with photos of Bryan
IMAGE_SIZE = os.getenv("OPENAI_IMAGE_SIZE", "1024x1024")
IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")  # Latest OpenAI image model
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "generated_images")

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
    # Extract activity stats and convert to US customary units
    distance_meters = activity.distance
    distance_km = round(distance_meters / 1000.0, 2)
    distance_miles = round(distance_meters / 1609.34, 2)  # Convert to miles
    
    moving_time = str(activity.moving_time)
    
    # Calculate pace from moving_time, handling both timedelta and integer seconds
    moving_time_obj = activity.moving_time
    total_seconds = 0
    
    # Handle different types of moving_time objects
    if isinstance(moving_time_obj, (int, float)):
        # If it's directly seconds (as seen in debug)
        total_seconds = moving_time_obj
    else:
        # Try to extract from timedelta-like object (traditional approach)
        try:
            total_seconds = (
                getattr(moving_time_obj, 'hours', 0) * 3600 + 
                getattr(moving_time_obj, 'minutes', 0) * 60 + 
                getattr(moving_time_obj, 'seconds', 0)
            )
        except (AttributeError, TypeError):
            pass
    
    # Calculate pace in both metric and imperial units
    avg_pace_metric = "N/A"
    avg_pace_imperial = "N/A"
    
    if distance_meters > 0:
        if total_seconds > 0:
            # Calculate pace (metric)
            pace_min_per_km = total_seconds / (distance_meters / 1000.0) / 60.0
            mins_km = int(pace_min_per_km)
            secs_km = int((pace_min_per_km - mins_km) * 60)
            avg_pace_metric = f"{mins_km}:{secs_km:02d} min/km"
            
            # Calculate pace (imperial)
            pace_min_per_mile = total_seconds / (distance_meters / 1609.34) / 60.0
            mins_mile = int(pace_min_per_mile)
            secs_mile = int((pace_min_per_mile - mins_mile) * 60)
            avg_pace_imperial = f"{mins_mile}:{secs_mile:02d} min/mile"
        elif hasattr(activity, 'average_speed') and activity.average_speed > 0:
            # Calculate from average_speed (m/s)
            pace_secs_per_km = 1000 / activity.average_speed
            pace_mins_km = int(pace_secs_per_km // 60)
            pace_secs_km = int(pace_secs_per_km % 60)
            avg_pace_metric = f"{pace_mins_km}:{pace_secs_km:02d} min/km"
            
            pace_secs_per_mile = 1609.34 / activity.average_speed
            pace_mins_mile = int(pace_secs_per_mile // 60)
            pace_secs_mile = int(pace_secs_per_mile % 60)
            avg_pace_imperial = f"{pace_mins_mile}:{pace_secs_mile:02d} min/mile"
    
    # Convert elevation gain from meters to feet
    elev_gain_meters = getattr(activity, "total_elevation_gain", 0)
    elev_gain_feet = round(elev_gain_meters * 3.28084)  # Convert to feet
    
    # Get average location (lat, lon)
    avg_lat, avg_lng = get_run_location(activity)
    
    # Analyze run type based on splits data
    run_type = analyze_run_type(activity)
    
    # Build the base prompt with activity details (in US customary units)
    prompt = (
        f"Create a stylized running poster celebrating a recent {run_type}. "
        f"The run was {distance_miles} miles with moving time {moving_time} and avg pace {avg_pace_imperial}. "
    )
    
    # Add elevation information if significant
    if elev_gain_feet > 100:
        prompt += f"The run included {elev_gain_feet} feet of elevation gain. "
    
    # Add location information if available
    if avg_lat and avg_lng:
        prompt += f"The run took place at coordinates ({avg_lat:.6f}, {avg_lng:.6f}). "
    
    prompt += (
        "The runner should look like the person in the reference image, but in running gear. "
        "Keep the same facial features and general appearance, but show them in motion with running attire. "
        "This is for personal, non-commercial use only. "
    )
    
    # Add style guidelines
    prompt += (
        "Overall style should evoke accomplishment and athleticism, "
        "with dynamic motion and inspirational feel. "
        f"Add visual elements showing the distance ({distance_miles} miles) and pace ({avg_pace_imperial}) "
        "statistics artistically integrated into the design. "
        "This is purely fictional artwork for personal use."
    )
    
    return prompt

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
                start_lat = start_latlng[0]
                start_lng = start_latlng[1]
            else:
                return None, None
                
            # Same for end point
            if hasattr(end_latlng, 'lat') and hasattr(end_latlng, 'lng'):
                end_lat = end_latlng.lat
                end_lng = end_latlng.lng
            elif isinstance(end_latlng, (list, tuple)) and len(end_latlng) >= 2:
                end_lat = end_latlng[0]
                end_lng = end_latlng[1]
            else:
                return None, None
            
            # Calculate averages
            avg_lat = (start_lat + end_lat) / 2
            avg_lng = (start_lng + end_lng) / 2
            
            print(f"Average location: ({avg_lat}, {avg_lng})")
            return avg_lat, avg_lng
            
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
            run_type = "interval workout"
        elif distance_miles >= 1 and avg_pace_secs_per_mile >= 450:
            # > 5 miles and at or slower than 7:30 pace
            run_type = "easy run"
        elif 3 <= distance_miles <= 10 and avg_pace_secs_per_mile < 450 and pace_std_dev < avg_pace * 0.1:
            # Between 3-10 miles at faster than 7:30 pace and relatively consistent
            run_type = "tempo run"
        elif distance_miles > 10 and avg_pace_secs_per_mile >= 450:
            # > 10 miles and at or faster than 7:30 pace
            run_type = "long run"
        
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
        
        # 2. Get the latest run
        print("Getting latest run...")
        activity = get_last_run(strava_client)
        print(f"Fetched activity: {activity.name} (ID: {activity.id})")
        
        # Print activity details for debugging
        print(f"Activity attributes: {dir(activity)}")
        
        # 3. Build prompt and generate image
        print("Building prompt for image generation...")
        prompt = build_prompt(activity)
        print(f"Generated prompt: {prompt}")
        
        print("Generating image with imagegen...")
        image_path = generate_image(prompt)
        print(f"Image saved locally at: {image_path}")
        
        # No need to download the image as it's already saved locally
        
        # 5. Provide instructions for Strava (API doesn't allow direct photo uploads)
        print("\nNOTE: Your Strava token only has read permissions (not activity:write)")
        print("To manually add this image to your Strava activity:")
        print(f"1. Open the image at: {image_path}")
        print("2. Open your activity on Strava")
        print("3. Click 'Add Photo' and upload the downloaded image")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    main()
