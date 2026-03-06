import boto3
import io
import os
import json
import uuid
import zipfile

s3 = boto3.client('s3')
BUCKET = os.environ['BUCKET_NAME']

def lambda_handler(event, context):
    keys = event['keys']
    zip_key = f"zips/temp_{uuid.uuid4()}.zip"

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for key in keys:
            obj = s3.get_object(Bucket=BUCKET, Key=key)
            filename = key.split('/')[-1]
            zf.writestr(filename, obj['Body'].read())

    zip_buffer.seek(0)
    s3.put_object(
        Bucket=BUCKET,
        Key=zip_key,
        Body=zip_buffer.getvalue()
    )

    # Presigned URL valid for 1 hour
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET, 'Key': zip_key},
        ExpiresIn=3600
    )
    return {'download_url': url}