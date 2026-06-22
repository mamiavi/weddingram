import boto3
import io
import os
import uuid
import zipfile

s3 = boto3.client('s3')
BUCKET = os.environ['BUCKET_NAME']

def lambda_handler(event, context):
    keys = event['keys']
    zip_key = f"zips/temp_{uuid.uuid4()}.zip"
    tmp_zip_path = '/tmp/output.zip'

    # Write ZIP to disk instead of memory
    with zipfile.ZipFile(tmp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for key in keys:
            obj = s3.get_object(Bucket=BUCKET, Key=key)
            filename = key.split('/')[-1]
            # Stream directly to zip without loading all in memory
            with zf.open(filename, 'w') as zf_file:
                for chunk in obj['Body'].iter_chunks(chunk_size=1024*1024):
                    zf_file.write(chunk)

    # Upload ZIP from disk to S3
    s3.upload_file(tmp_zip_path, BUCKET, zip_key)

    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET, 'Key': zip_key},
        ExpiresIn=3600
    )
    return {'download_url': url}