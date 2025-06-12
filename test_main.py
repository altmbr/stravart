#!/usr/bin/env python3
"""
End-to-end test for StravaRunArt application.
Tests the complete workflow with real API calls.
"""

import os
import sys
import json
import base64
from datetime import datetime
from pathlib import Path
import subprocess
import time

# Add parent directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import openai
from openai import OpenAI

# Load environment variables
load_dotenv()

# Test configuration
TEST_OUTPUT_DIR = "test_generated_images"
TEST_LOG_FILE = "test_run.log"

class StravaRunArtTest:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.test_start_time = datetime.now()
        self.log_file = open(TEST_LOG_FILE, 'w')
        
    def log(self, message):
        """Log message to both console and file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.log_file.write(log_entry + "\n")
        self.log_file.flush()
        
    def setup_test_environment(self):
        """Set up test directories and environment."""
        self.log("Setting up test environment...")
        
        # Create test output directory
        os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
        
        # Override output directory for test
        os.environ["OUTPUT_DIR"] = TEST_OUTPUT_DIR
        
        # Clean up old test images
        for file in Path(TEST_OUTPUT_DIR).glob("*.png"):
            file.unlink()
            self.log(f"Removed old test image: {file}")
            
    def run_main_with_auto_selection(self):
        """Run main.py with automated activity selection."""
        self.log("Running main.py with automated selection...")
        
        # Create a subprocess to run main.py and automatically select option 1
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a moment for the script to start
        time.sleep(2)
        
        # Send "1" to select the first activity
        stdout, stderr = process.communicate(input="1\n")
        
        # Log output
        self.log("STDOUT:")
        for line in stdout.split('\n'):
            if line.strip():
                self.log(f"  {line}")
                
        if stderr:
            self.log("STDERR:")
            for line in stderr.split('\n'):
                if line.strip():
                    self.log(f"  {line}")
                    
        return process.returncode == 0, stdout, stderr
        
    def find_generated_image(self):
        """Find the most recently generated image."""
        self.log("Looking for generated image...")
        
        images = list(Path(TEST_OUTPUT_DIR).glob("*.png"))
        if not images:
            self.log("ERROR: No images found in test output directory")
            return None
            
        # Get the most recent image
        latest_image = max(images, key=lambda p: p.stat().st_mtime)
        self.log(f"Found generated image: {latest_image}")
        
        return latest_image
        
    def validate_image_with_gpt4(self, image_path):
        """Use GPT-4 Vision to analyze and validate the generated image."""
        self.log(f"Validating image with GPT-4 Vision: {image_path}")
        
        # Read and encode the image
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Analyze this image and answer the following questions:
1. Does this appear to be an artistic poster or artwork?
2. Can you see any running or athletic-related imagery?
3. Are there any visible statistics, numbers, or data (like distance, pace, time)?
4. Is there a person or runner visible in the image?
5. What is the overall artistic style of the image?
6. Does this look like it could be a Strava activity poster?

Please provide a detailed description and then give a simple YES/NO answer to: 
"Does this appear to be a successfully generated Strava run art poster that combines athletic data with artistic imagery?"
"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            analysis = response.choices[0].message.content
            self.log("GPT-4 Vision Analysis:")
            for line in analysis.split('\n'):
                if line.strip():
                    self.log(f"  {line}")
                    
            # Check if the analysis indicates success
            success = "YES" in analysis.upper() and any(
                keyword in analysis.lower() 
                for keyword in ["poster", "athletic", "running", "strava", "artistic"]
            )
            
            return success, analysis
            
        except Exception as e:
            self.log(f"ERROR during image validation: {str(e)}")
            return False, str(e)
            
    def run_test(self):
        """Run the complete end-to-end test."""
        self.log("=== Starting StravaRunArt End-to-End Test ===")
        
        try:
            # Setup
            self.setup_test_environment()
            
            # Run main application
            success, stdout, stderr = self.run_main_with_auto_selection()
            
            if not success:
                self.log("ERROR: main.py did not complete successfully")
                return False
                
            # Find generated image
            image_path = self.find_generated_image()
            if not image_path:
                self.log("ERROR: No generated image found")
                return False
                
            # Validate image size
            image_size = os.path.getsize(image_path)
            self.log(f"Image size: {image_size:,} bytes")
            
            if image_size < 10000:  # Less than 10KB is suspiciously small
                self.log("ERROR: Image file is too small, likely corrupted")
                return False
                
            # Validate image with GPT-4
            validation_success, analysis = self.validate_image_with_gpt4(image_path)
            
            if validation_success:
                self.log("✅ Test PASSED: Image successfully generated and validated")
                return True
            else:
                self.log("❌ Test FAILED: Image validation did not pass")
                return False
                
        except Exception as e:
            self.log(f"ERROR: Unexpected error during test: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return False
            
        finally:
            self.log(f"Test duration: {datetime.now() - self.test_start_time}")
            self.log("=== Test Complete ===")
            self.log_file.close()
            
    def cleanup(self):
        """Clean up test artifacts."""
        # Keep the generated images and logs for manual inspection
        pass


def main():
    """Run the test suite."""
    print("Starting StravaRunArt test suite...")
    
    # Check for required environment variables
    required_vars = ["STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please ensure .env file contains all required variables")
        return 1
        
    # Run test
    test = StravaRunArtTest()
    success = test.run_test()
    
    # Print summary
    print("\n" + "="*50)
    print(f"Test Result: {'PASSED ✅' if success else 'FAILED ❌'}")
    print(f"Log file: {TEST_LOG_FILE}")
    print(f"Generated images: {TEST_OUTPUT_DIR}/")
    print("="*50)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())