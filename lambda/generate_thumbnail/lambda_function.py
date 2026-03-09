import io
import os
import subprocess
import boto3
from PIL import Image
from urllib.parse import unquote_plus

s3 = boto3.client('s3')
THUMBNAIL_SIZE = (300, 300)
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.webm', '.mkv')

def get_video_thumbnail(original_bytes):
    input_path = '/tmp/input_video'
    output_path = '/tmp/thumb.jpg'
    with open(input_path, 'wb') as f:
        f.write(original_bytes)
    subprocess.run([
        '/opt/bin/ffmpeg',
        '-i', input_path,
        '-ss', '00:00:01',
        '-vframes', '1',
        output_path,
        '-y'
    ], check=True)
    return Image.open(output_path)

def lambda_handler(event, context):
    record = event['Records'][0]['s3']
    bucket = record['bucket']['name']
    key = unquote_plus(record['object']['key'])

    # Only process uploads/
    if not key.startswith('uploads/'):
        print(f"Skipping {key} - not in uploads/")
        return

    print(f"Processing: {key}")

    # Download original from S3
    obj = s3.get_object(Bucket=bucket, Key=key)
    original_bytes = obj['Body'].read()

    # Generate thumbnail
    if key.lower().endswith(VIDEO_EXTENSIONS):
        img = get_video_thumbnail(original_bytes)
    else:
        img = Image.open(io.BytesIO(original_bytes))

    img = img.convert('RGB')
    img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format='WEBP', quality=75)
    buffer.seek(0)

    # Thumbnail always gets .webp extension regardless of original
    filename = key.split('/')[-1]
    filename_no_ext = os.path.splitext(filename)[0]
    thumb_key = f"thumbnails/{filename_no_ext}.webp"

    s3.put_object(
        Bucket=bucket,
        Key=thumb_key,
        Body=buffer.getvalue(),
        ContentType='image/webp',
    )
    print(f"Thumbnail uploaded: {thumb_key}")