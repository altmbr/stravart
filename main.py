from stravalib import Client
from strava_client import get_strava_access_token, get_recent_runs, get_activity_details
from image_generator import build_prompt, generate_image
from cli import select_activity
from config import STRAVA_REFRESH_TOKEN, STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET

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


def main():
    """Run the complete Strava Run Art workflow."""
    try:
        # 1. Connect to Strava API
        print("Fetching Strava access token...")
        access_token, expires_at = get_strava_access_token()
        
        print("Initializing Strava client...")
        strava_client = Client(access_token=access_token)
        # Set client properties to avoid warnings and enable auto-refresh
        strava_client.refresh_token = STRAVA_REFRESH_TOKEN
        strava_client.client_id = STRAVA_CLIENT_ID
        strava_client.client_secret = STRAVA_CLIENT_SECRET
        # Set token expiration time as timestamp (unix time)
        strava_client.token_expires = expires_at
        
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