import io
import json
import urllib.request

import av
import boto3
from PIL import Image

s3 = boto3.client('s3')
THUMBNAIL_SIZE = (300, 300)
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.webm', '.mkv')

BUCKET_SERVERS = {
    "django-weddingram-s3": "https://weddingram.manuelminambres.es",
    "django-weddingram-s3-stg": "https://stg.weddingram.manuelminambres.es"
}

def lambda_handler(event, context):
    record = event['Records'][0]['s3']
    bucket = record['bucket']['name']
    key = record['object']['key']
    django_url = BUCKET_SERVERS[bucket]
    print(f"Processing: {key}")

    # Download original from S3
    obj = s3.get_object(Bucket=bucket, Key=key)
    original_bytes = obj['Body'].read()

    if key.lower().endswith(VIDEO_EXTENSIONS):
        container = av.open(io.BytesIO(original_bytes))
        for frame in container.decode(video=0):
            img = frame.to_image()
            break
    else:
        img = Image.open(io.BytesIO(original_bytes)).convert('RGB')

    # Generate thumbnail
    img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format='WEBP', quality=75)
    buffer.seek(0)

    # Upload thumbnail
    filename = key.split('/')[-1]
    thumb_key = f"thumbnails/{filename}"
    s3.put_object(
        Bucket=bucket,
        Key=thumb_key,
        Body=buffer.getvalue(),
        ContentType='image/webp',
    )

    thumb_url = f"https://{bucket}.s3.amazonaws.com/{thumb_key}"
    print(f"Thumbnail uploaded: {thumb_url}")

    # Notify Django
    payload = json.dumps({'key': key, 'thumb_url': thumb_url}).encode()
    req = urllib.request.Request(
        f"{django_url}/set_thumbnail/",
        data=payload,
        headers={
            'Content-Type': 'application/json',
        }
    )
    urllib.request.urlopen(req, timeout=10)
    print("Django notified successfully")