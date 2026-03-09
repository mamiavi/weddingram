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
  - [2. IAM User and Group](#2-iam-user-and-group)
  - [3. Lambda — Thumbnail Generator](#3-lambda--thumbnail-generator)
  - [4. Lambda — ZIP Generator](#4-lambda--zip-generator)
  - [5. S3 Lifecycle Rule (auto-cleanup)](#5-s3-lifecycle-rule-auto-cleanup)
- [Raspberry Pi Time Sync](#raspberry-pi-time-sync)
- [Environment Variables Reference](#environment-variables-reference)
- [Authentication](#authentication)
- [Nginx](#nginx)

---

## Overview

Guests access the app via a **magic token link** (no password needed), upload photos and videos from their phones, and browse a gallery. They can select files and download them as a ZIP.

Everything heavy is offloaded to AWS so the Raspberry Pi only handles lightweight API calls:

- Images are compressed and converted to WebP **in the browser** before upload
- Files go **directly from the browser to S3** via presigned POST URLs — they never pass through the server
- Thumbnails are generated automatically by a **Lambda triggered by S3**
- ZIP downloads are created by a **second Lambda** and delivered straight from S3 to the user

---

## Architecture

```
Browser
  │
  ├── GET /gallery/              ──►  Django (Pi)  ──►  DB (file records)
  │
  ├── POST /get_upload_url/      ──►  Django (Pi)  ──►  returns S3 presigned POST URL
  │
  ├── POST (file) to S3          ─────────────────────────────►  S3 (uploads/)
  │                                                                    │
  │                                                         S3 triggers Lambda
  │                                                                    │
  │                                                         Lambda: generate-thumbnail
  │                                                                    │
  │                                                         └──►  S3 (thumbnails/)
  │
  ├── POST /save_file_url/       ──►  Django (Pi)  ──►  saves S3 key + thumbnail key to DB
  │
  └── POST /download_selected_zip/
            ──►  Django (Pi)  ──►  Lambda: generate-gallery-zip
                                              │
                                   ├──►  pulls files from S3
                                   ├──►  saves ZIP to S3 (zips/)
                                   └──►  returns presigned URL ──► browser downloads from S3
```

**Key design decisions:**

- The thumbnail key is derived deterministically from the upload key: `uploads/xxx_file.mp4` → `thumbnails/xxx_file.webp`. Django saves this path immediately when the file record is created, before Lambda has finished generating it. A fallback placeholder image is shown if the thumbnail is not yet ready.
- Lambda never calls back Django. The thumbnail path is predictable so no coordination is needed.
- Files are private in S3. All URLs served to the browser are presigned and expire after 1 hour.

---

## Project Structure

```
weddingram/
├── auth/
│   └── backends.py              # Token-based authentication backend
├── photos/
│   ├── assets/                  # Source JS, CSS, images (pre-collectstatic)
│   │   ├── css/styles.css
│   │   ├── img/
│   │   │   ├── logo.png
│   │   │   ├── img_thumbnail.jpg     # Placeholder shown while image thumbnail loads
│   │   │   └── video_thumbnail.png   # Placeholder shown while video thumbnail loads
│   │   └── js/
│   │       ├── gallery.js       # Gallery lightbox, selection, lazy loading, download
│   │       ├── upload.js        # File compression + presigned S3 upload flow
│   │       ├── countdown.js
│   │       └── utils.js
│   ├── migrations/
│   ├── templates/
│   │   ├── gallery.html
│   │   ├── upload.html
│   │   └── countdown.html
│   ├── models.py                # File model with thumbnail_url property
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
- Pillow — for local thumbnail generation
- PyAV — for local video thumbnail generation

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
- Thumbnails are generated synchronously by Django using Pillow (images) and PyAV (videos)
- Thumbnail filenames always use `.webp` extension regardless of original format
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

Runs Django + Gunicorn + Nginx. Requires all environment variables below.

#### Setting environment variables for Docker

Create a `.env.prod` file (never commit this):

```env
DEBUG=False
SECRET_KEY=your-production-secret-key

BUCKET_FILESTORE=True
AWS_ACCESS_KEY_ID=your-key-id
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=eu-north-1

POSTGRES_DB=weddingram
POSTGRES_USER=weddingram
POSTGRES_PASSWORD=your-db-password
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

Then reference it in `docker-compose.prod.yml`:

```yaml
env_file:
  - .env.prod
```

---

## AWS Setup

Complete all steps below before switching to production mode (`BUCKET_FILESTORE=True`).

> ⚠️ **Important:** Every Lambda function you create gets its own IAM execution role with minimal permissions. You must manually attach S3 permissions to each role after creation — see steps 3 and 4.

---

### 1. S3 Bucket

1. Go to **AWS Console → S3 → Create bucket**
2. Name it (e.g. `weddingram-media`) and choose your region (e.g. `eu-north-1`)
3. **Keep "Block all public access" ON** — files are private and served via presigned URLs
4. After creating, go to **Permissions → CORS** and add:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST"],
    "AllowedOrigins": ["https://yourdomain.com"],
    "ExposeHeaders": []
  }
]
```

The bucket will contain these folders (created automatically on first upload):

| Folder | Contents |
|---|---|
| `uploads/` | Original files uploaded by guests |
| `thumbnails/` | Auto-generated WebP thumbnails (300×300) |
| `zips/` | Temporary ZIP files for download (auto-deleted after 1 day) |

---

### 2. IAM User and Group

#### Create a group with S3 + Lambda permissions

1. Go to **IAM → User groups → Create group**, name it `django-s3-group`
2. Under **Attach permissions policies**, attach **`AmazonS3FullAccess`**
3. Create the group, then go into it → **Permissions → Add permissions → Create inline policy**:

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

Replace `YOUR_ACCOUNT_ID` with your 12-digit AWS account ID.

#### Create the IAM user

1. Go to **IAM → Users → Create user**, name it `django-s3-user`
2. Add it to the `django-s3-group` you just created
3. Go to **Security credentials → Create access key** → choose **Application running outside AWS**
4. Save the **Access key ID** and **Secret access key** — you won't see the secret again

---

### 3. Lambda — Thumbnail Generator

Triggered automatically by S3 whenever a file lands in `uploads/`. Generates a 300×300 WebP thumbnail and saves it to `thumbnails/` with the same filename but `.webp` extension.

> **No Django callback needed.** The thumbnail path is deterministic — Django already knows where it will be saved.

#### Create the function

1. **Lambda → Create function → Author from scratch**
2. Name: `generate-thumbnail`
3. Runtime: **Python 3.10**
4. Click **Create function**

#### Add the Pillow layer

1. Inside your function → scroll to **Layers → Add a layer**
2. Choose **Specify an ARN**
3. Find the Pillow ARN for your region and Python 3.10 at:
   `https://api.klayers.cloud/api/v2/p3.10/layers/latest/eu-north-1/html`
   Find the **Pillow** row and copy the ARN
4. Paste it → **Verify → Add**

#### Add the FFmpeg layer (for video thumbnails)

1. Go to **AWS Serverless Application Repository → Public applications**
2. Search for **`ffmpeg-lambda-layer`** → find the one by **serverlesspub** → **Deploy**
3. Once deployed, go back to your Lambda function → **Layers → Add a layer → Custom layers** → select the ffmpeg layer

#### Attach S3 permissions to the execution role

1. Go to **Configuration → Permissions** → click the execution role link
2. **Attach policies → Create inline policy**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR_BUCKET_NAME",
        "arn:aws:s3:::YOUR_BUCKET_NAME/*"
      ]
    }
  ]
}
```

#### Configuration

**Configuration → General configuration → Edit:**
- Timeout: **2 minutes**
- Memory: **512 MB**

#### S3 Trigger

**Configuration → Triggers → Add trigger:**
- Source: **S3**
- Bucket: your bucket
- Event type: **PUT**
- Prefix: `uploads/`
- Acknowledge the recursive invocation warning → **Add**

#### Function code

Paste this directly into the Lambda inline editor:

```python
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
    key = unquote_plus(record['object']['key'])  # S3 URL-encodes keys in events

    if not key.startswith('uploads/'):
        print(f"Skipping {key} - not in uploads/")
        return

    print(f"Processing: {key}")

    obj = s3.get_object(Bucket=bucket, Key=key)
    original_bytes = obj['Body'].read()

    if key.lower().endswith(VIDEO_EXTENSIONS):
        img = get_video_thumbnail(original_bytes)
    else:
        img = Image.open(io.BytesIO(original_bytes))

    img = img.convert('RGB')
    img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format='WEBP', quality=75)
    buffer.seek(0)

    filename = key.split('/')[-1]
    filename_no_ext = os.path.splitext(filename)[0]
    thumb_key = f"thumbnails/{filename_no_ext}.webp"

    s3.put_object(
        Bucket=bucket,
        Key=thumb_key,
        Body=buffer.getvalue(),
        ContentType='image/webp',
    )
    print(f"Thumbnail saved: {thumb_key}")
```

---

### 4. Lambda — ZIP Generator

Invoked on demand by Django when a user requests a ZIP download. Pulls the selected files from S3, zips them in memory, saves to `zips/`, and returns a presigned download URL valid for 1 hour.

#### Create the function

1. **Lambda → Create function → Author from scratch**
2. Name: `generate-gallery-zip`
3. Runtime: **Python 3.10** (or any version — no extra layers needed)
4. Click **Create function**

#### Attach S3 permissions to the execution role

Same as the thumbnail Lambda — go to **Configuration → Permissions → execution role → Create inline policy**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR_BUCKET_NAME",
        "arn:aws:s3:::YOUR_BUCKET_NAME/*"
      ]
    }
  ]
}
```

#### Configuration

**Configuration → General configuration → Edit:**
- Timeout: **5 minutes**

**Configuration → Environment variables:**

| Key | Value |
|---|---|
| `BUCKET_NAME` | your S3 bucket name |

> This function has **no S3 trigger** — it is invoked directly by Django via `boto3`.

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
        ExpiresIn=3600
    )
    return {'download_url': url}
```

---

### 5. S3 Lifecycle Rule (auto-cleanup)

ZIP files accumulate in `zips/` after each download. This rule deletes them automatically after 1 day.

1. **S3 → your bucket → Management → Lifecycle rules → Create lifecycle rule**
2. Rule name: `delete-temp-zips`
3. Prefix: `zips/`
4. Add action: **Expire current versions of objects** → after **1 day**
5. Save

---

## Raspberry Pi Time Sync

> ⚠️ **Critical:** AWS presigned URLs are extremely sensitive to clock skew. If the Pi's clock is out of sync, every S3 upload will fail with "Policy expired".

Check and fix the clock before deploying:

```bash
# Check current time
date

# Sync immediately
sudo apt install ntpdate -y
sudo ntpdate pool.ntp.org

# Enable automatic sync
sudo timedatectl set-ntp true
timedatectl status  # should show: System clock synchronized: yes
```

Add a cron job to keep it synced:

```bash
sudo crontab -e
# Add this line:
0 * * * * /usr/sbin/ntpdate pool.ntp.org
```

---

## Environment Variables Reference

| Variable | Required in prod | Description |
|---|---|---|
| `DEBUG` | No (defaults to False) | Django debug mode |
| `SECRET_KEY` | Yes | Django secret key |
| `BUCKET_FILESTORE` | Yes | `True` to use S3; `False` for local file storage |
| `AWS_ACCESS_KEY_ID` | Yes | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | Yes | IAM user secret key |
| `AWS_STORAGE_BUCKET_NAME` | Yes | S3 bucket name |
| `AWS_S3_REGION_NAME` | Yes | AWS region (e.g. `eu-north-1`) |
| `POSTGRES_DB` | Yes | PostgreSQL database name |
| `POSTGRES_USER` | Yes | PostgreSQL user |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `POSTGRES_HOST` | Yes | PostgreSQL host (e.g. `db` in Docker) |
| `POSTGRES_PORT` | Yes | PostgreSQL port (e.g. `5432`) |
| `WEDDING_DATE` | No | If set, enables countdown page before this date |

---

## Authentication

The app uses a **token-based authentication system** (`auth/backends.py`). Guests don't log in with a username/password — instead, they receive a unique URL:

```
https://yourdomain.com/login/<token>/
```

Tokens are managed via the Django admin panel (`/admin/`). Create a token per guest or share one for the whole event.

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

**`nginx.conf`** — reverse proxy, forwards requests to Gunicorn:
- Handles main app traffic
- Sets `client_max_body_size` to allow large video uploads
- Proxies to Django container on port 8000

**`nginx_static.conf`** — serves Django static files directly:
- Serves `STATIC_ROOT` without hitting Django
- Used in production to keep the app container lean

Both run as containers via `docker-compose.prod.yml` — no manual Nginx installation needed on the Pi.