import os
from dotenv import load_dotenv
import openai
import boto3
import base64
from datetime import datetime


# 2. Configure AWS S3
bucket_name = os.getenv("AWS_S3_BUCKET_NAME", "website-dashbot")
s3_folder = "news-images"  # folder inside bucket


def generate_and_upload_image(prompt: str, filename_prefix: str = "ai_image"):
    # Load environment variables
    load_dotenv()
    
    # Check OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    
    # Check AWS credentials
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    if not aws_access_key or not aws_secret_key:
        raise ValueError("AWS credentials not set. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
    
    # Initialize S3 client with credentials
    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=os.getenv("AWS_REGION", "eu-central-1")
    )

    # Generate image with OpenAI
    response = openai.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024",
        n=1,
    )    # 4. Decode base64 to bytes

    if not response.data or len(response.data) == 0:
        raise ValueError("No image data received from OpenAI")
    
    image_b64 = response.data[0].b64_json
    if not image_b64:
        raise ValueError("No base64 data in image response")
        
    image_bytes = base64.b64decode(image_b64)

    # 5. Create filename with timestamp
    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    # 6. Upload to S3
    s3_key = f"{s3_folder}/{filename}"
    s3.put_object(
        Bucket=bucket_name, Key=s3_key, Body=image_bytes, ContentType="image/png"
    )

    # 7. Return the public S3 URL (if bucket is public)
    region = os.getenv("AWS_REGION", "eu-central-1")
    url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
    return url


# Example usage
if __name__ == "__main__":
    prompt = "earth from space. beautiful vivid, breathtaking."
    url = generate_and_upload_image(prompt, filename_prefix="climate")
    print("Image uploaded to:", url)
