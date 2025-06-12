import os
import base64
import mimetypes
import random
from datetime import datetime, timezone, timedelta
import openai
import requests
from config import OPENAI_API_KEY, IMAGE_SIZE, IMAGE_MODEL, OUTPUT_DIR, BRYAN_IMAGES_DIR, USER_IMAGES_DIR
from location_service import get_run_location, get_location_details
from run_analyzer import analyze_run_type


def describe_runner_photo(path: str) -> str:
    """Use GPT-4o-Vision to analyze runner photo for the imagegen prompt."""
    # Read and encode the image
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    
    # Determine the MIME type
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    
    # Set up OpenAI client
    client = openai.OpenAI(api_key=OPENAI_API_KEY)


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


def generate_image(prompt: str) -> str:
    """Generate an image via the OpenAI image generation API (gpt-image-1). Returns the hosted URL or raises with detailed diagnostics."""
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    try:
        # Open the reference image
        with open("bryanphotos/Bryan.jpg", "rb") as image_file:
            response = client.images.edit(
                model="gpt-image-1",  # Using the same model as the working example
                image=image_file,
                prompt=prompt
            )
        
        if not response.data:
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
        print(f"OpenAI API error: {bre}")
        raise
    except openai.OpenAIError as e:
        print(f"OpenAI API error: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error during image generation: {e}")
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
    elif os.path.exists(USER_IMAGES_DIR):
        image_path = random.choice([
            os.path.join(USER_IMAGES_DIR, f) 
            for f in os.listdir(USER_IMAGES_DIR) 
            if os.path.isfile(os.path.join(USER_IMAGES_DIR, f))
        ])
    
    # Get description if we have an image
    if image_path:
        try:
            description = describe_runner_photo(image_path)
        except Exception:
            pass  # Silently fall back if photo analysis fails
    
    return image_path, description