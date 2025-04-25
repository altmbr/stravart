#!/usr/bin/env python3
"""Test script for image generation using OpenAI API.

This script uses gpt-image-1 for image generation.
"""

import base64
import os
import sys
from pathlib import Path
from io import BytesIO

import openai
from dotenv import load_dotenv
from openai import OpenAI

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL not available. Images will be saved as raw files.")

# Load environment variables from .env file
load_dotenv()

# Retrieve API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise EnvironmentError(
        "OPENAI_API_KEY environment variable not set. "
        "Please set it in your shell or .env file before running this script."
    )

client = OpenAI(api_key=api_key)

# Create output directory
output_dir = Path("generated_images")
output_dir.mkdir(exist_ok=True)

# Print OpenAI SDK version for debugging
print(f"OpenAI SDK version: {openai.__version__}")

# Define the prompt
prompt = """
Create a stylized image of a superhero dog soaring above a futuristic city. 
The dog is a golden retriever wearing a bright red cape and a blue mask.
It should be flying dramatically with its cape flowing in the wind against 
a sunset sky with purple and orange hues. The futuristic city below has 
tall glass skyscrapers with neon lights.
"""

print(f"Generating image with prompt:\n{prompt}")

# Generate image with gpt-image-1
try:
    print("\nGenerating image with gpt-image-1...")
    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024",
    )
    print(" Successfully generated image with gpt-image-1!")
    
    # Handle URL response from gpt-image-1
    image_url = result.data[0].url
    print(f"Image URL: {image_url}")
    
    if image_url:
        import requests
        print("Downloading image from URL...")
        response = requests.get(image_url)
        if response.status_code == 200:
            output_path = output_dir / "superhero_dog_gpt_image_1.png"
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f" Image saved to: {output_path}")
            sys.exit(0)  # Exit successfully
except Exception as e:
    print(f"Error with gpt-image-1: {e}")
    if hasattr(e, "body"):
        print(f"Error details: {e.body}")
    sys.exit(1)