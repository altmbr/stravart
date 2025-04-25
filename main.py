import os
import random
import requests
import base64
import mimetypes
import json
from datetime import datetime
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
    activities = list(client.get_activities(limit=1))
    if not activities:
        raise RuntimeError("No activities found for athlete.")
    return activities[0]

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
    
    # Call GPT-4o with the image - using a more general approach
    print(f"Analyzing runner photo with GPT-4o: {path}")
    resp = client.chat.completions.create(
        model="gpt-4o",  # Use GPT-4o for best vision capabilities
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "This is a photo related to a running activity. "
                            "Please describe the general athletic features visible "
                            "in terms of color scheme, athletic apparel, and overall style. "
                            "Focus on clothing, posture, and the general athletic context. "
                            "DO NOT describe facial features or provide identifying information. "
                            "Be concise (max 40 words)."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            }
        ],
    )
    
    description = resp.choices[0].message.content.strip()
    
    # Provide a fallback if GPT-4o still declines
    if "sorry" in description.lower() or "can't help" in description.lower() or "unable" in description.lower():
        description = "Athletic build, dressed in performance running gear, poised and confident stance, ready for action."
        print(f"Using fallback description: {description}")
    else:
        print(f"Generated description: {description}")
        
    return description

# ------ IMAGE GENERATION FUNCTIONS ------

def build_prompt(activity, runner_description: str | None = None) -> str:
    """Construct a text prompt for imagegen summarising the activity."""
    # Extract activity stats
    distance_km = round(activity.distance / 1000.0, 2)
    moving_time = str(activity.moving_time)
    
    # Calculate pace from Duration object in stravalib
    moving_time_obj = activity.moving_time
    total_seconds = (
        getattr(moving_time_obj, 'hours', 0) * 3600 + 
        getattr(moving_time_obj, 'minutes', 0) * 60 + 
        getattr(moving_time_obj, 'seconds', 0)
    )
    
    if distance_km > 0:
        pace_min_per_km = total_seconds / (activity.distance / 1000.0) / 60.0
        avg_pace = f"{pace_min_per_km:.1f} min/km"
    else:
        avg_pace = "N/A"
        
    elev_gain = getattr(activity, "total_elevation_gain", 0)

    # Build the base prompt with activity details
    prompt = (
        "Create a stylized running poster celebrating a recent run. "
        f"The run was {distance_km} km with moving time {moving_time} and avg pace {avg_pace}. "
        "The runner should look like the person in the reference image, but in running gear. "
        "Keep the same facial features and general appearance, but show them in motion with running attire. "
        "This is for personal, non-commercial use only. "
    )
    
    # Add style guidelines
    prompt += (
        "Overall style should evoke accomplishment and athleticism, "
        "with dynamic motion and inspirational feel. "
        "Add visual elements showing the distance and pace statistics artistically integrated into the design. "
        "This is purely fictional artwork for personal use."
    )
    
    return prompt

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
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
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
    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
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
        
        # 3. Build prompt and generate image
        print("Building prompt for image generation...")
        prompt = build_prompt(activity)
        print(f"Generated prompt: {prompt}")
        
        print("Generating image with imagegen...")
        image_path = generate_image(prompt)
        print(f"Image saved locally at: {image_path}")
        
        # 4. Download the image
        print("Downloading image...")
        local_path = download_image(image_path)
        print(f"Image saved locally at: {local_path}")
        
        # 5. Provide instructions for Strava (API doesn't allow direct photo uploads)
        print("\nNOTE: Your Strava token only has read permissions (not activity:write)")
        print("To manually add this image to your Strava activity:")
        print(f"1. Download the image from: {image_path}")
        print("2. Open your activity on Strava")
        print("3. Click 'Add Photo' and upload the downloaded image")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    main()
