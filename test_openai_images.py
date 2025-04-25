#!/usr/bin/env python3
"""Test script for OpenAI image generation API.

This script demonstrates various options for the OpenAI image generation API.
Based on: https://platform.openai.com/docs/api-reference/images/create
"""

import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Retrieve API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise EnvironmentError(
        "OPENAI_API_KEY environment variable not set. "
        "Please set it in your shell or .env file before running this script."
    )

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Create output directory
output_dir = Path("generated_images")
output_dir.mkdir(exist_ok=True)

def generate_and_save_image(prompt: str, model: str = "gpt-image-1", size: str = "1024x1024", 
                          quality: str = "standard", style: str = "natural", 
                          response_format: str = "url", n: int = 1) -> str:
    """Generate an image and save it to disk.
    
    Args:
        prompt: The text description of the image to generate
        model: The model to use (gpt-image-1)
        size: The size of the image (1024x1024, 1024x1792, or 1792x1024)
        quality: The quality of the image (standard or hd)
        style: The style of the image (natural or vivid)
        response_format: The format of the response (url or b64_json)
        n: The number of images to generate (1-10)
    
    Returns:
        The path to the saved image
    """
    print(f"\nGenerating image with parameters:")
    print(f"  Model: {model}")
    print(f"  Size: {size}")
    print(f"  Quality: {quality}")
    print(f"  Style: {style}")
    print(f"  Response format: {response_format}")
    print(f"  Number of images: {n}")
    print(f"  Prompt: {prompt}")
    
    try:
        # Generate the image
        response = client.images.generate(
            model=model,
            prompt=prompt,
            size=size,
            quality=quality,
            style=style,
            response_format=response_format,
            n=n
        )
        
        # Handle the response based on format
        if response_format == "url":
            # Get the URL and download the image
            image_url = response.data[0].url
            print(f"Image URL: {image_url}")
            
            # Download the image
            response = requests.get(image_url)
            if response.status_code == 200:
                # Save the image
                output_path = output_dir / f"generated_image_{size}_{style}.png"
                with open(output_path, "wb") as f:
                    f.write(response.content)
                print(f"Image saved to: {output_path}")
                return str(output_path)
        else:  # b64_json
            # Decode and save the base64 image
            import base64
            image_data = base64.b64decode(response.data[0].b64_json)
            output_path = output_dir / f"generated_image_{size}_{style}.png"
            with open(output_path, "wb") as f:
                f.write(image_data)
            print(f"Image saved to: {output_path}")
            return str(output_path)
            
    except Exception as e:
        print(f"Error generating image: {e}")
        if hasattr(e, "body"):
            print(f"Error details: {e.body}")
        raise

def main():
    """Run the test script with various image generation options."""
    # Test case 1: Basic image generation
    prompt1 = "A serene landscape with mountains and a lake at sunset"
    generate_and_save_image(prompt1)
    
    # Test case 2: Different size
    prompt2 = "A futuristic cityscape with flying cars"
    generate_and_save_image(prompt2, size="1024x1792")
    
    # Test case 3: HD quality and vivid style
    prompt3 = "A vibrant abstract painting with bold colors"
    generate_and_save_image(prompt3, quality="hd", style="vivid")
    
    # Test case 4: Multiple images
    prompt4 = "A cute cartoon cat playing with yarn"
    generate_and_save_image(prompt4, n=2)
    
    print("\nAll test cases completed!")

if __name__ == "__main__":
    main() 