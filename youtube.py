from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict
import yt_dlp
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import requests
import random
import tempfile
import os
from pathlib import Path
import asyncio
import uvicorn
from datetime import datetime
import uuid
import mimetypes


# Pydantic models
class VideoDownloadRequest(BaseModel):
    url: HttpUrl
    quality: Optional[str] = "best"
    audio_only: Optional[bool] = False


class VideoDownloadResponse(BaseModel):
    success: bool
    message: str
    video_url: Optional[str] = None
    video_info: Optional[Dict] = None
    download_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    message: str


# FastAPI app
app = FastAPI(
    title="YouTube Video Downloader API",
    description="Download YouTube videos with proxy rotation and upload to S3",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WebshareVideoDownloader:
    def __init__(self, proxy_password: str, proxy_usernames: Optional[List[str]] = None,
                 aws_access_key: str = None, aws_secret_key: str = None,
                 aws_bucket_name: str = None, aws_region: str = "us-east-1"):
        """
        Initialize the video downloader with Webshare proxy rotation and S3 upload
        """
        self.proxy_password = proxy_password

        if proxy_usernames:
            self.proxy_usernames = proxy_usernames
        else:
            self.proxy_usernames = [f"lvzvdcev-{i}" for i in range(1, 11)]

        self.proxy_endpoint = "p.webshare.io:80"

        # AWS S3 configuration
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_bucket_name = aws_bucket_name
        self.aws_region = aws_region
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print(f"ACCESS_KEY : {self.aws_access_key}")
        print(f"SECRET_KEY : {self.aws_secret_key}")
        print(f"BUCKET_NAME : {self.aws_bucket_name}")
        print(f"AWS_REGION : {self.aws_region}")
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        # Initialize S3 client
        if all([aws_access_key, aws_secret_key, aws_bucket_name]):
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )
        else:
            self.s3_client = None
            print("Warning: S3 credentials not provided. S3 upload will be disabled.")

    def test_proxy_connection(self) -> bool:
        """Test if the proxy configuration is working"""
        try:
            proxy_url = self.get_proxy_config()
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }

            response = requests.get('http://httpbin.org/ip',
                                    proxies=proxies,
                                    timeout=10)

            return response.status_code == 200
        except Exception:
            return False

    def get_proxy_config(self) -> str:
        """Get a random proxy from available proxies for rotation"""
        username = random.choice(self.proxy_usernames)
        proxy_url = f"http://{username}:{self.proxy_password}@{self.proxy_endpoint}"
        return proxy_url

    def get_yt_dlp_options(self, output_path: str, quality: str = "best",
                           audio_only: bool = False) -> Dict:
        """Get yt-dlp options with proxy configuration"""
        proxy_url = self.get_proxy_config()

        base_options = {
            'proxy': proxy_url,
            'outtmpl': output_path,
            'ignoreerrors': False,
            'retries': 3,
            'sleep_interval': 1,
            'max_sleep_interval': 5,
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
        }

        if audio_only:
            base_options.update({
                'format': 'bestaudio/best',
                'extractaudio': True,
                'audioformat': 'mp3',
                'audioquality': '192K',
            })
        else:
            if quality == "best":
                base_options['format'] = 'best[height<=1080]'
            elif quality == "worst":
                base_options['format'] = 'worst'
            else:
                base_options['format'] = f'best[height<={quality[:-1]}]'

        return base_options

    async def download_video(self, url: str, quality: str = "best",
                             audio_only: bool = False) -> Dict:
        """Download video and upload to S3"""
        download_id = str(uuid.uuid4())

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Create output template
                output_template = os.path.join(temp_dir, f"{download_id}.%(ext)s")

                # Get yt-dlp options
                options = self.get_yt_dlp_options(output_template, quality, audio_only)

                # Download video
                with yt_dlp.YoutubeDL(options) as ydl:
                    # Get video info first
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'Unknown Title')
                    duration = info.get('duration', 0)
                    uploader = info.get('uploader', 'Unknown')
                    view_count = info.get('view_count', 0)

                    video_info = {
                        'title': title,
                        'duration': duration,
                        'uploader': uploader,
                        'view_count': view_count,
                        'original_url': url
                    }

                    # Download the video
                    ydl.download([url])

                # Find the downloaded file
                downloaded_files = list(Path(temp_dir).glob(f"{download_id}.*"))

                if not downloaded_files:
                    return {
                        'success': False,
                        'message': 'No file was downloaded',
                        'video_info': video_info
                    }

                downloaded_file = downloaded_files[0]

                # Upload to S3 if configured
                if self.s3_client and self.aws_bucket_name:
                    s3_url = await self.upload_to_s3(downloaded_file, download_id, title)

                    return {
                        'success': True,
                        'message': 'Video downloaded and uploaded successfully',
                        'video_url': s3_url,
                        'video_info': video_info,
                        'download_id': download_id
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Video downloaded but S3 upload not configured',
                        'video_info': video_info
                    }

            except Exception as e:
                return {
                    'success': False,
                    'message': f'Error downloading video: {str(e)}',
                    'download_id': download_id
                }

    async def upload_to_s3(self, file_path: Path, download_id: str, title: str) -> str:
        """Upload file to S3 and return the URL"""
        try:
            # Clean title for S3 key
            clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            clean_title = clean_title.replace(' ', '_')[:50]  # Limit length

            # Create S3 key
            file_extension = file_path.suffix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            s3_key = f"youtube_videos/{timestamp}_{clean_title}_{download_id}{file_extension}"

            # Determine content type
            content_type, _ = mimetypes.guess_type(str(file_path))
            if not content_type:
                content_type = 'application/octet-stream'

            # Upload to S3
            extra_args = {'ContentType': content_type}

            self.s3_client.upload_file(
                str(file_path),
                self.aws_bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )

            # Generate S3 URL
            s3_url = f"https://{self.aws_bucket_name}.s3.{self.aws_region}.amazonaws.com/{s3_key}"

            return s3_url

        except Exception as e:
            raise Exception(f"S3 upload failed: {str(e)}")


# Configuration - Replace with your actual values
CONFIG = {
    "PROXY_PASSWORD": os.getenv("PROXY_PASSWORD"),
    "PROXY_USERNAMES": [
        "lvzvdcev-1", "lvzvdcev-2", "lvzvdcev-3", "lvzvdcev-4", "lvzvdcev-5",
        "lvzvdcev-6", "lvzvdcev-7", "lvzvdcev-8", "lvzvdcev-9", "lvzvdcev-10"
    ],
    "AWS_ACCESS_KEY": os.getenv("AWS_ACCESS_KEY_ID"),
    "AWS_SECRET_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "AWS_BUCKET_NAME": os.getenv("AWS_BUCKET_NAME", "your-bucket-name"),
    "AWS_REGION": os.getenv("AWS_REGION", "us-east-1")
}

# Initialize downloader
downloader = WebshareVideoDownloader(
    proxy_password=CONFIG["PROXY_PASSWORD"],
    proxy_usernames=CONFIG["PROXY_USERNAMES"],
    aws_access_key=CONFIG["AWS_ACCESS_KEY"],
    aws_secret_key=CONFIG["AWS_SECRET_KEY"],
    aws_bucket_name=CONFIG["AWS_BUCKET_NAME"],
    aws_region=CONFIG["AWS_REGION"]
)


# API Routes
@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="YouTube Video Downloader API is running"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check including proxy test"""
    proxy_working = downloader.test_proxy_connection()
    s3_configured = downloader.s3_client is not None

    if proxy_working and s3_configured:
        return HealthResponse(
            status="healthy",
            message="All services are operational"
        )
    else:
        issues = []
        if not proxy_working:
            issues.append("Proxy connection failed")
        if not s3_configured:
            issues.append("S3 not configured")

        return HealthResponse(
            status="degraded",
            message=f"Issues detected: {', '.join(issues)}"
        )


@app.post("/download", response_model=VideoDownloadResponse)
async def download_video(request: VideoDownloadRequest):
    """Download video and upload to S3"""
    try:
        result = await downloader.download_video(
            url=str(request.url),
            quality=request.quality,
            audio_only=request.audio_only
        )

        return VideoDownloadResponse(
            success=result['success'],
            message=result['message'],
            video_url=result.get('video_url'),
            video_info=result.get('video_info'),
            download_id=result.get('download_id')
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/download-async", response_model=Dict)
async def download_video_async(request: VideoDownloadRequest, background_tasks: BackgroundTasks):
    """Start video download as background task"""
    download_id = str(uuid.uuid4())

    # Add the download task to background tasks
    background_tasks.add_task(
        download_video_background,
        str(request.url),
        request.quality,
        request.audio_only,
        download_id
    )

    return {
        "message": "Download started",
        "download_id": download_id,
        "status": "processing"
    }


async def download_video_background(url: str, quality: str, audio_only: bool, download_id: str):
    """Background task for video download"""
    # This would typically update a database or cache with the result
    # For now, it just performs the download
    result = await downloader.download_video(url, quality, audio_only)
    print(f"Background download {download_id} completed: {result}")


@app.get("/status/{download_id}")
async def get_download_status(download_id: str):
    """Get status of a background download (placeholder)"""
    # In a real implementation, you'd check a database or cache
    return {
        "download_id": download_id,
        "status": "completed",  # This would be dynamic
        "message": "Status checking not implemented yet"
    }


# Run the server
if __name__ == "__main__":
    uvicorn.run(
        "youtube:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )