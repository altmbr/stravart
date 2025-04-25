import base64
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client with API key
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

prompt = """
Transform this person into wearing a professional business suit. 
Keep the same pose and facial expression, but add a well-fitted suit 
with a white dress shirt and tie. Make it look natural and professional.
"""

result = client.images.edit(
    model="gpt-image-1",
    image=open("bryanphotos/Bryan.jpg", "rb"),
    prompt=prompt
)

image_base64 = result.data[0].b64_json
image_bytes = base64.b64decode(image_base64)

# Save the image to a file
with open("bryan_in_suit.png", "wb") as f:
    f.write(image_bytes)
