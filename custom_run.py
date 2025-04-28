#!/usr/bin/env python
"""
Generate Strava Run Art using custom run data
"""
import os
import sys
import base64
import datetime
from datetime import timedelta
import logging
from pathlib import Path
from dotenv import load_dotenv

import openai

# Import necessary functions from main.py
from main import (
    generate_image, 
    analyze_run_type
)

def ensure_output_dir():
    """Ensure the output directory exists."""
    output_dir = os.getenv("OUTPUT_DIR", "generated_images")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def main():
    """Generate run artwork using custom data."""
    # Load environment variables
    load_dotenv()  # Load environment variables from a .env file if present

    # Custom run data (using metric units)
    activity_title = "12x400 Sprint Intervals"  # Title of the activity
    distance_km = 7.77
    # Keep in metric units instead of converting to miles
    
    # Pace in min/km (5:15/km)
    pace_min_per_km = 5.25  # 5:15/km in decimal
    pace_min = int(pace_min_per_km)
    pace_sec = int((pace_min_per_km - pace_min) * 60)
    pace_str = f"{pace_min}:{pace_sec:02d} min/km"
    
    # Convert time string to seconds
    time_parts = "40m49s".replace('m', ':').replace('s', '').split(':')
    minutes = int(time_parts[0])
    seconds = int(time_parts[1]) if len(time_parts) > 1 else 0
    total_seconds = minutes * 60 + seconds
    moving_time = timedelta(seconds=total_seconds)
    duration_formatted = f"{minutes}:{seconds:02d} minutes"
    
    # Keep elevation in meters
    elevation_gain_m = 0  # If you have elevation data, set it here
    
    location = "Vancouver, Canada"
    
    # Set run type based on activity name (detect if it's an interval workout)
    activity_name_lower = activity_title.lower()
    if any(keyword in activity_name_lower for keyword in ['hiit', 'sprint', 'tabata', 'high intensity']):
        run_type = "High Intensity Interval Training"
    elif any(keyword in activity_name_lower for keyword in ['interval', 'repeat', 'x400', '400m', '800m']):
        run_type = "Interval Run"
    else:
        run_type = "Tempo Run"  # Default, can be customized
    
    # Build the prompt with metric units and include title
    prompt = f"Create a stylized running poster celebrating a recent {run_type.lower()}. "
    prompt += f"Activity title: '{activity_title}'. "
    prompt += f"The run was {distance_km} km with duration {duration_formatted} and avg pace {pace_str}. "
    prompt += f"The run included {elevation_gain_m} meters of elevation gain. "
    prompt += f"The run took place in {location}. Show visual elements or scenery that represents this location. "
    prompt += "The runner should look like the person in the reference image, but in running gear. "
    prompt += "Keep the same facial features and general appearance, but show them in motion with running attire. "
    prompt += "This is for personal, non-commercial use only. "
    prompt += "Overall style should evoke accomplishment and athleticism, with dynamic motion and inspirational feel. "
    prompt += f"Add visual elements showing the distance ({distance_km} km) and pace ({pace_str}) "
    prompt += "statistics artistically integrated into the design. "
    prompt += "Do not duplicate any numbers in the image - each statistic should appear only once. "
    prompt += "This is purely fictional artwork for personal use."
    
    # Set up the image path
    image_path = "bryanphotos/Bryan.jpg"  # Use the available image
    
    # Validate the image exists
    if not os.path.exists(image_path):
        print(f"Error: Image '{image_path}' not found.")
        return 1
    
    print("Custom Run Data (Metric Units):")
    print(f"- Activity Title: {activity_title}")
    print(f"- Run Type: {run_type}")
    print(f"- Distance: {distance_km} km")
    print(f"- Pace: {pace_str}")
    print(f"- Duration: {duration_formatted}")
    print(f"- Location: {location}")
    
    print("\nGenerating image with prompt:")
    print(prompt)
    
    # Generate the image using the existing function
    try:
        # Custom version of generate_image that uses malich.jpeg
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Ensure output directory exists
        output_dir = ensure_output_dir()
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_path = f"{output_dir}/custom_run_{timestamp}.png"
        
        print(f"Output directory: {output_dir}")
        print(f"Will save to: {output_path}")
        
        # Image generation parameters
        image_size = os.getenv("IMAGE_SIZE", "1024x1024")
        
        print(f"OpenAI SDK version: {openai.__version__}")
        print(f"Sending image generation request. Model=gpt-image-1, Size={image_size}")
        
        # Open the custom reference image
        with open(image_path, "rb") as image_file:
            print(f"Sending request with image: {image_path}")
            response = client.images.edit(
                model="gpt-image-1",
                image=image_file,
                prompt=prompt
            )
        
        print(f"Response received: {response}")
        print(f"Response data type: {type(response.data)}")
        print(f"Response data length: {len(response.data)}")
        
        # Display the first data item
        if response.data and len(response.data) > 0:
            first_item = response.data[0]
            print(f"First item attributes: {dir(first_item)}")
            
            # Check for URL
            if hasattr(first_item, 'url') and first_item.url:
                image_url = first_item.url
                print(f"Image URL found: {image_url}")
                
                # Try to download from URL
                try:
                    import requests
                    resp = requests.get(image_url, stream=True)
                    if resp.status_code == 200:
                        with open(output_path, "wb") as f:
                            for chunk in resp.iter_content(1024):
                                f.write(chunk)
                        print(f"SUCCESS: Image downloaded and saved locally at: {output_path}")
                    else:
                        print(f"Failed to download image from URL. Status code: {resp.status_code}")
                except Exception as e:
                    print(f"Error downloading image from URL: {e}")
            
            # Check for base64 data
            if hasattr(first_item, 'b64_json') and first_item.b64_json:
                print("Base64 data found, saving directly...")
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(first_item.b64_json))
                print(f"SUCCESS: Image saved directly from base64 at: {output_path}")
            
            # If neither was successful
            if not os.path.exists(output_path):
                print("WARNING: Failed to save image by either URL or base64 method")
        else:
            print("No data items found in response")
        
    except Exception as e:
        print(f"Error generating image: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
