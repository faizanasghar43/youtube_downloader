from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict
import yt_dlp
import boto3
import requests
import random
import tempfile
import os
from pathlib import Path
import uvicorn
from datetime import datetime
import uuid
import mimetypes
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig


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


class TranscriptRequest(BaseModel):
    url: HttpUrl
    language: Optional[str] = "en"


class TranscriptResponse(BaseModel):
    success: bool
    message: str
    transcript: Optional[List[Dict]] = None
    video_info: Optional[Dict] = None
    transcript_text: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    message: str


# FastAPI app
app = FastAPI(
    title="YouTube Video Downloader",
    description="Download YouTube videos with proxy rotation and upload to S3",
    version="1.0.0"
)

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

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
            'retries': 5,
            'sleep_interval': 2,
            'max_sleep_interval': 10,
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'extract_flat': False,
            'no_warnings': False,
            'prefer_insecure': False,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
            'cookiesfrombrowser': None,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_skip': ['configs'],
                    'player_client': ['android', 'web']
                }
            }
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
                # Support for YouTube Shorts and regular videos
                base_options['format'] = 'best[height<=1080][ext=mp4]/best[height<=1080]/best[ext=mp4]/best'
            elif quality == "worst":
                base_options['format'] = 'worst[ext=mp4]/worst'
            else:
                # Specific quality with mp4 preference
                height = quality[:-1] if quality.endswith('p') else quality
                base_options['format'] = f'best[height<={height}][ext=mp4]/best[height<={height}]/best[ext=mp4]/best'

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

                # Download video with better error handling
                with yt_dlp.YoutubeDL(options) as ydl:
                    try:
                        # Get video info first
                        info = ydl.extract_info(url, download=False)
                        if not info:
                            return {
                                'success': False,
                                'message': 'Could not extract video information. The video may be private, deleted, or restricted.',
                                'download_id': download_id
                            }
                            
                        title = info.get('title', 'Unknown Title')
                        duration = info.get('duration', 0)
                        uploader = info.get('uploader', 'Unknown')
                        view_count = info.get('view_count', 0)
                        video_type = info.get('duration', 0) <= 60 and 'shorts' in url.lower() or 'shorts' in info.get('webpage_url', '').lower()

                        video_info = {
                            'title': title,
                            'duration': duration,
                            'uploader': uploader,
                            'view_count': view_count,
                            'original_url': url,
                            'is_shorts': video_type
                        }

                        # Download the video
                        ydl.download([url])

                    except yt_dlp.DownloadError as e:
                        error_msg = str(e)
                        if "403" in error_msg or "Forbidden" in error_msg:
                            return {
                                'success': False,
                                'message': 'Access denied. The video may be private, age-restricted, or blocked in your region. Try using a different proxy or VPN.',
                                'video_info': video_info if 'video_info' in locals() else None,
                                'download_id': download_id
                            }
                        elif "404" in error_msg or "Not Found" in error_msg:
                            return {
                                'success': False,
                                'message': 'Video not found. The video may have been deleted or the URL is incorrect.',
                                'download_id': download_id
                            }
                        elif "Sign in" in error_msg or "login" in error_msg.lower():
                            return {
                                'success': False,
                                'message': 'This video requires sign-in to view. We cannot download private or restricted videos.',
                                'download_id': download_id
                            }
                        else:
                            return {
                                'success': False,
                                'message': f'Download failed: {error_msg}',
                                'video_info': video_info if 'video_info' in locals() else None,
                                'download_id': download_id
                            }

                # Find the downloaded file
                downloaded_files = list(Path(temp_dir).glob(f"{download_id}.*"))

                if not downloaded_files:
                    return {
                        'success': False,
                        'message': 'No file was downloaded. The video may not be available in the requested format.',
                        'video_info': video_info if 'video_info' in locals() else None,
                        'download_id': download_id
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
                        'video_info': video_info,
                        'download_id': download_id
                    }

            except Exception as e:
                error_msg = str(e)
                return {
                    'success': False,
                    'message': f'Unexpected error: {error_msg}',
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


class YouTubeTranscriptService:
    def __init__(self, proxy_username: str, proxy_password: str):
        """
        Initialize the YouTube transcript service with Webshare proxy configuration
        """
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password
        
        # Initialize YouTubeTranscriptApi with Webshare proxy configuration
        self.ytt_api = YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=proxy_username,
                proxy_password=proxy_password,
                filter_ip_locations=["us", "ca", "de", "gb"],  # US, Canada, Germany, UK
            )
        )
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        import re
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([\w-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def get_video_info(self, video_id: str) -> Dict:
        """Get basic video information"""
        try:
            # Use yt-dlp to get video info
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                return {
                    'title': info.get('title', 'Unknown Title'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'video_id': video_id
                }
        except Exception as e:
            return {
                'title': 'Unknown Title',
                'duration': 0,
                'uploader': 'Unknown',
                'view_count': 0,
                'video_id': video_id,
                'error': str(e)
            }
    
    async def get_transcript(self, url: str, language: str = "en") -> Dict:
        """Get transcript for a YouTube video"""
        try:
            # Extract video ID
            video_id = self.extract_video_id(str(url))
            if not video_id:
                return {
                    'success': False,
                    'message': 'Invalid YouTube URL. Could not extract video ID.',
                    'video_info': None,
                    'transcript': None,
                    'transcript_text': None
                }
            
            # Get video info
            video_info = await self.get_video_info(video_id)
            
            # Check if video is longer than 1 minute (60 seconds)
            if video_info.get('duration', 0) > 60:
                return {
                    'success': False,
                    'message': 'Video is longer than 1 minute. Transcription is only available for videos up to 1 minute.',
                    'video_info': video_info,
                    'transcript': None,
                    'transcript_text': None
                }
            
            # Fetch transcript
            transcript = self.ytt_api.fetch(video_id, languages=[language])
            
            # Convert transcript to list of dictionaries
            transcript_data = []
            transcript_text = ""
            
            for snippet in transcript:
                transcript_data.append({
                    'start': snippet.start,
                    'duration': snippet.duration,
                    'text': snippet.text
                })
                transcript_text += snippet.text + " "
            
            return {
                'success': True,
                'message': 'Transcript fetched successfully',
                'video_info': video_info,
                'transcript': transcript_data,
                'transcript_text': transcript_text.strip()
            }
            
        except Exception as e:
            error_message = str(e)
            if "No transcript" in error_message:
                error_message = "No transcript available for this video. The video may not have captions enabled."
            elif "Video unavailable" in error_message:
                error_message = "Video is unavailable or private."
            else:
                error_message = f"Error fetching transcript: {error_message}"
            
            return {
                'success': False,
                'message': error_message,
                'video_info': await self.get_video_info(self.extract_video_id(str(url)) or ""),
                'transcript': None,
                'transcript_text': None
            }


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
    "AWS_REGION": os.getenv("AWS_REGION", "us-east-1"),
    "DOMAIN": os.getenv("DOMAIN", "http://localhost:8000"),
    "GA_MEASUREMENT_ID": os.getenv("GA_MEASUREMENT_ID", "GA_MEASUREMENT_ID"),
    "TRANSCRIPT_PROXY_USERNAME": os.getenv("TRANSCRIPT_PROXY_USERNAME", "lvzvdcev"),
    "TRANSCRIPT_PROXY_PASSWORD": os.getenv("TRANSCRIPT_PROXY_PASSWORD", "aml70orzku77")
}

# Initialize services
downloader = WebshareVideoDownloader(
    proxy_password=CONFIG["PROXY_PASSWORD"],
    proxy_usernames=CONFIG["PROXY_USERNAMES"],
    aws_access_key=CONFIG["AWS_ACCESS_KEY"],
    aws_secret_key=CONFIG["AWS_SECRET_KEY"],
    aws_bucket_name=CONFIG["AWS_BUCKET_NAME"],
    aws_region=CONFIG["AWS_REGION"]
)

transcript_service = YouTubeTranscriptService(
    proxy_username=CONFIG["TRANSCRIPT_PROXY_USERNAME"],
    proxy_password=CONFIG["TRANSCRIPT_PROXY_PASSWORD"]
)


# Frontend Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page with download form"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_date": datetime.now(),
        "domain": CONFIG["DOMAIN"],
        "ga_measurement_id": CONFIG["GA_MEASUREMENT_ID"]
    })

@app.get("/how-it-works", response_class=HTMLResponse)
async def how_it_works(request: Request):
    """How it works page"""
    return templates.TemplateResponse("how_it_works.html", {
        "request": request,
        "current_date": datetime.now(),
        "domain": CONFIG["DOMAIN"]
    })

@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    """Privacy policy page"""
    return templates.TemplateResponse("privacy.html", {
        "request": request,
        "current_date": datetime.now(),
        "domain": CONFIG["DOMAIN"]
    })

@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    """Terms of service page"""
    return templates.TemplateResponse("terms.html", {
        "request": request,
        "current_date": datetime.now(),
        "domain": CONFIG["DOMAIN"]
    })

@app.get("/sitemap.xml")
async def sitemap():
    """Sitemap for SEO"""
    return FileResponse("static/sitemap.xml", media_type="application/xml")

@app.get("/robots.txt")
async def robots():
    """Robots.txt for SEO"""
    robots_content = f"""User-agent: *
Allow: /
Disallow: /api/
Disallow: /health
Sitemap: {CONFIG["DOMAIN"]}/sitemap.xml"""
    return FileResponse("static/robots.txt", media_type="text/plain")

# API Routes
@app.get("/api/health", response_model=HealthResponse)
async def api_health_check():
    """API health check endpoint"""
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

@app.post("/api/download", response_model=VideoDownloadResponse)
async def api_download_video(request: VideoDownloadRequest):
    """API endpoint for downloading video"""
    return await download_video(request)

@app.post("/transcript", response_model=TranscriptResponse)
async def get_transcript(request: TranscriptRequest):
    """Get transcript for a YouTube video (max 1 minute)"""
    try:
        result = await transcript_service.get_transcript(
            url=str(request.url),
            language=request.language
        )
        
        return TranscriptResponse(
            success=result['success'],
            message=result['message'],
            transcript=result.get('transcript'),
            video_info=result.get('video_info'),
            transcript_text=result.get('transcript_text')
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transcript", response_model=TranscriptResponse)
async def api_get_transcript(request: TranscriptRequest):
    """API endpoint for getting transcript"""
    return await get_transcript(request)


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