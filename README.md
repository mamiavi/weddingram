# 📸 Weddingram

A Django web application for event guests to upload and download photos and videos in real time. Built to run on a Raspberry Pi 4 with AWS handling all the heavy lifting — file storage (S3), thumbnail generation (Lambda), and ZIP downloads (Lambda).

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Local Development Setup](#local-development-setup)
- [Docker Setup](#docker-setup)
  - [Local (docker-compose.yml)](#local-docker-composeyml)
  - [Staging (docker-compose.stg.yml)](#staging-docker-composestgyml)
  - [Production (docker-compose.prod.yml)](#production-docker-composeprodymll)
- [AWS Setup](#aws-setup)
  - [1. S3 Bucket](#1-s3-bucket)
  - [2. IAM User](#2-iam-user)
  - [3. Lambda — Thumbnail Generator](#3-lambda--thumbnail-generator)
  - [4. Lambda — ZIP Generator](#4-lambda--zip-generator)
  - [5. S3 Lifecycle Rule (auto-cleanup)](#5-s3-lifecycle-rule-auto-cleanup)
- [Environment Variables Reference](#environment-variables-reference)
- [Authentication](#authentication)
- [Nginx](#nginx)

---

## Overview

Guests access the app via a **magic token link** (no password needed), upload photos and videos from their phones, and browse a paginated gallery. They can select files and download them as a ZIP.

Everything heavy is offloaded to AWS so the Raspberry Pi only handles lightweight API calls:

- Images are compressed and converted to WebP **in the browser** before upload
- Files go **directly from the browser to S3** via presigned URLs — they never pass through the server
- Thumbnails are generated automatically by a **Lambda triggered by S3**
- ZIP downloads are created by a **second Lambda** and delivered straight from S3 to the user

---

## Architecture

```
Browser
  │
  ├── GET /gallery/           ──►  Django (Pi)  ──►  DB (file records)
  │
  ├── POST /get_upload_url/   ──►  Django (Pi)  ──►  returns S3 presigned URL
  │
  ├── PUT (file)              ─────────────────────────────►  S3 (uploads/)
  │                                                              │
  │                                                    S3 triggers Lambda
  │                                                              │
  │                                                    Lambda: generate-thumbnail
  │                                                              │
  │                                                    ├──►  S3 (thumbnails/)
  │                                                    └──►  POST /set_thumbnail/ ──► Django ──► DB
  │
  ├── POST /save_file_url/    ──►  Django (Pi)  ──►  saves S3 key to DB
  │
  └── POST /download_selected_zip/
            ──►  Django (Pi)  ──►  Lambda: generate-gallery-zip
                                              │
                                   ├──►  pulls files from S3
                                   ├──►  saves ZIP to S3 (zips/)
                                   └──►  returns presigned URL ──► browser downloads from S3
```

---

## Project Structure

```
weddingram/
├── auth/
│   └── backends.py              # Token-based authentication backend
├── photos/
│   ├── assets/                  # Source JS, CSS, images (pre-collectstatic)
│   │   ├── css/styles.css
│   │   ├── img/logo.png
│   │   └── js/
│   │       ├── gallery.js       # Gallery pagination, lightbox, selection, download
│   │       ├── upload.js        # File compression + presigned S3 upload flow
│   │       ├── countdown.js
│   │       └── utils.js
│   ├── migrations/
│   ├── templates/
│   │   ├── gallery.html
│   │   ├── upload.html
│   │   └── countdown.html
│   ├── models.py                # File model (S3 key + thumbnail_url)
│   ├── views.py                 # All app views
│   ├── urls.py
│   ├── forms.py
│   └── middleware.py
├── weddingram/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── templates/
│   └── registration/login.html
├── Dockerfile
├── docker-compose.yml           # Local development
├── docker-compose.stg.yml       # Staging
├── docker-compose.prod.yml      # Production (Raspberry Pi)
├── entrypoint.sh                # DB migrations + collectstatic on container start
├── nginx.conf                   # Nginx reverse proxy config
├── nginx_static.conf            # Nginx static files config
├── manage.py
└── requirements.txt
```

---

## Requirements

**To run locally (without Docker):**
- Python 3.11+
- pip
- Pillow (`pip install Pillow`) — for local thumbnail generation

**To run with Docker:**
- Docker
- Docker Compose

**AWS services (production only):**
- S3
- Lambda × 2
- IAM

---

## Local Development Setup

### Without Docker

```bash
git clone https://github.com/mamiavi/weddingram.git
cd weddingram
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
DEBUG=True
SECRET_KEY=your-local-django-secret-key
BUCKET_FILESTORE=False
```

Run migrations and start the server:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

In local mode (`BUCKET_FILESTORE=False`):
- Files are stored in `media/uploads/`
- Thumbnails are generated synchronously by Django using Pillow
- ZIPs are built in memory and served directly by Django
- No AWS credentials needed

---

## Docker Setup

The project includes three Docker Compose configurations for different environments. All share the same `Dockerfile` and `entrypoint.sh`, which automatically runs migrations and `collectstatic` on startup.

### Local (docker-compose.yml)

```bash
docker compose up --build
```

Uses local file storage. No AWS required. App available at `http://localhost:8000`.

### Staging (docker-compose.stg.yml)

```bash
docker compose -f docker-compose.stg.yml up --build
```

Uses S3 for storage. Requires AWS environment variables. Useful for testing the full AWS flow before deploying to the Pi.

### Production (docker-compose.prod.yml)

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Runs Django + Gunicorn + Nginx. Requires all environment variables below. This is what runs on the Raspberry Pi.

#### Setting environment variables for Docker

Create a `.env.prod` file (never commit this):

```env
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=yourdomain.com,192.168.x.x

BUCKET_FILESTORE=True
AWS_ACCESS_KEY_ID=your-key-id
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=eu-north-1

INTERNAL_SECRET=your-shared-lambda-secret
DJANGO_URL=http://yourdomain.com
```

Then reference it in `docker-compose.prod.yml`:

```yaml
env_file:
  - .env.prod
```

---

## AWS Setup

Complete all steps below before switching to production mode (`BUCKET_FILESTORE=True`).

---

### 1. S3 Bucket

1. Go to **AWS Console → S3 → Create bucket**
2. Name it (e.g. `weddingram-media`) and choose your region (e.g. `eu-north-1`)
3. **Uncheck "Block all public access"** — the bucket must be publicly readable for media URLs to work in the browser
4. After creating, go to **Permissions → Bucket policy** and add:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
    }
  ]
}
```

5. Go to **Permissions → CORS** and add:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": []
  }
]
```

The bucket will contain these folders (created automatically):

| Folder | Contents |
|---|---|
| `uploads/` | Original files uploaded by guests |
| `thumbnails/` | Auto-generated WebP thumbnails (400×400) |
| `zips/` | Temporary ZIP files for download (auto-deleted after 1 day) |

---

### 2. IAM User

This user provides credentials for your Django app to access S3 and invoke Lambda.

1. Go to **IAM → Users → Create user**, name it `django-s3-user`
2. Attach the policy **`AmazonS3FullAccess`**
3. Add a custom inline policy for Lambda invoke (replace values as needed):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:eu-north-1:YOUR_ACCOUNT_ID:function:generate-gallery-zip"
    }
  ]
}
```

4. Go to **Security credentials → Create access key** — save the key ID and secret as `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

---

### 3. Lambda — Thumbnail Generator

Triggered automatically by S3 whenever a file is uploaded to `uploads/`. Generates a 400×400 WebP thumbnail, saves it to `thumbnails/`, then calls back Django to update the database record.

#### Create the function

1. **Lambda → Create function**
2. Name: `generate-thumbnail`, Runtime: Python 3.12
3. Click **Create**

#### Add the Pillow layer

Pillow is not built into Lambda. Use the public Klayers layer:

1. Inside your function → scroll to **Layers → Add a layer**
2. Choose **Specify an ARN**
3. Find your region's ARN at: `https://api.klayers.cloud/api/v2/p3.12/layers/latest/eu-north-1/html`
   Find the **Pillow** row and copy the ARN
4. Paste it → **Verify → Add**

#### Configuration

Go to **Configuration → Environment variables**:

| Key | Value |
|---|---|
| `BUCKET_NAME` | your S3 bucket name |
| `DJANGO_URL` | your app's public URL, e.g. `http://yourdomain.com` (no trailing slash) |
| `INTERNAL_SECRET` | a random secret string, must match `INTERNAL_SECRET` in Django |

Go to **Configuration → Permissions** → click the execution role → **Attach policies** → add `AmazonS3FullAccess`.

Go to **Configuration → General configuration** → set **timeout to 2 minutes**.

#### S3 Trigger

**Configuration → Triggers → Add trigger:**
- Source: **S3**
- Bucket: your bucket
- Event type: **PUT**
- Prefix: `uploads/`
- Acknowledge the warning → **Add**

#### Function code

```python
import boto3
import io
import os
import urllib.request
import json
from PIL import Image

s3 = boto3.client('s3')
BUCKET = os.environ['BUCKET_NAME']
THUMBNAIL_SIZE = (400, 400)
DJANGO_URL = os.environ['DJANGO_URL']
INTERNAL_SECRET = os.environ['INTERNAL_SECRET']
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.webm', '.mkv')

def lambda_handler(event, context):
    record = event['Records'][0]['s3']
    key = record['object']['key']

    if key.lower().endswith(VIDEO_EXTENSIONS):
        print(f"Skipping video: {key}")
        return

    print(f"Processing: {key}")
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    original_bytes = obj['Body'].read()

    image = Image.open(io.BytesIO(original_bytes)).convert('RGB')
    image.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)

    buffer = io.BytesIO()
    image.save(buffer, format='WEBP', quality=75)
    buffer.seek(0)

    filename = key.split('/')[-1]
    thumb_key = f"thumbnails/{filename}.webp"

    s3.put_object(
        Bucket=BUCKET,
        Key=thumb_key,
        Body=buffer.getvalue(),
        ContentType='image/webp',
    )

    thumb_url = f"https://{BUCKET}.s3.amazonaws.com/{thumb_key}"
    print(f"Thumbnail uploaded: {thumb_url}")

    payload = json.dumps({'key': key, 'thumb_url': thumb_url}).encode()
    req = urllib.request.Request(
        f"{DJANGO_URL}/set_thumbnail/",
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'X-Internal-Secret': INTERNAL_SECRET,
        }
    )
    urllib.request.urlopen(req, timeout=10)
    print("Django notified successfully")
```

---

### 4. Lambda — ZIP Generator

Invoked on demand by Django when a user requests a ZIP. Pulls the selected files from S3, zips them in memory, saves to `zips/`, and returns a presigned download URL valid for 1 hour.

#### Create the function

1. **Lambda → Create function**
2. Name: `generate-gallery-zip`, Runtime: Python 3.12
3. Click **Create**

> No extra layers needed — `zipfile` is built into Python.

#### Configuration

**Configuration → Environment variables:**

| Key | Value |
|---|---|
| `BUCKET_NAME` | your S3 bucket name |

**Configuration → Permissions** → attach `AmazonS3FullAccess` to the execution role.

**Configuration → General configuration** → set **timeout to 5 minutes**.

> This function has **no S3 trigger** — it is invoked directly by Django.

#### Function code

```python
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

    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET, 'Key': zip_key},
        ExpiresIn=3600  # 1 hour
    )
    return {'download_url': url}
```

---

### 5. S3 Lifecycle Rule (auto-cleanup)

ZIP files accumulate in `zips/` after each download. This rule deletes them automatically after 1 day — no code required.

1. **S3 → your bucket → Management → Lifecycle rules → Create lifecycle rule**
2. Rule name: `delete-temp-zips`
3. Prefix: `zips/`
4. Add action: **Expire current versions of objects** → after **1 day**
5. Save

---

## Environment Variables Reference

| Variable | Required in prod | Description |
|---|---|---|
| `DEBUG` | No (defaults to False) | Django debug mode |
| `SECRET_KEY` | Yes | Django secret key |
| `ALLOWED_HOSTS` | Yes | Comma-separated list of allowed hosts |
| `BUCKET_FILESTORE` | Yes | `True` to use S3; `False` for local file storage |
| `AWS_ACCESS_KEY_ID` | Yes | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | Yes | IAM user secret key |
| `AWS_STORAGE_BUCKET_NAME` | Yes | S3 bucket name |
| `AWS_S3_REGION_NAME` | Yes | AWS region (e.g. `eu-north-1`) |
| `INTERNAL_SECRET` | Yes | Shared secret between Django and the thumbnail Lambda |
| `DJANGO_URL` | Lambda env only | Public URL of the app, used by Lambda to call `/set_thumbnail/` |

---

## Authentication

The app uses a **token-based authentication system** (`auth/backends.py`). Guests don't log in with a username/password — instead, they receive a unique URL of the form:

```
http://yourdomain.com/login/<token>/
```

Tokens are managed via the Django admin panel (`/admin/`). Create a token for each guest or share a single token for the whole event — your choice.

To create a superuser for admin access:

```bash
# Without Docker
python manage.py createsuperuser

# With Docker
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

---

## Nginx

The project includes two Nginx configs:

**`nginx.conf`** — reverse proxy, forwards requests to Gunicorn (Django):
- Handles the main app traffic
- Sets `client_max_body_size` to allow large video uploads (adjust if needed)
- Proxies to Django container on port 8000

**`nginx_static.conf`** — serves Django static files directly:
- Serves `STATIC_ROOT` without hitting Django
- Used in production to keep the app container lean

Both are mounted into the Nginx container via `docker-compose.prod.yml`. No manual Nginx installation needed on the Pi — it runs as a container.