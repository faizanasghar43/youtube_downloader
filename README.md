# YouTube Video Downloader with Frontend

A modern, responsive YouTube video downloader with integrated ads, SEO optimization, and a beautiful frontend built with FastAPI and Bootstrap.

## Features

- 🎥 **YouTube Video Download**: Download videos in various qualities (1080p, 720p, 480p, etc.)
- 🎵 **Audio Extraction**: Convert videos to MP3 format
- 📱 **YouTube Shorts Support**: Download YouTube Shorts and live streams
- 📝 **Transcript Extraction**: Get transcripts for videos up to 1 minute
- 🌍 **Multi-language Support**: Transcripts in multiple languages
- 🚀 **Fast & Secure**: Uses proxy rotation for reliable downloads
- ☁️ **S3 Integration**: Automatic upload to AWS S3
- 📱 **Responsive Design**: Works on desktop, tablet, and mobile
- 🔍 **SEO Optimized**: Meta tags, structured data, sitemap
- 📊 **Analytics**: Google Analytics integration
- 🎨 **Modern UI**: Beautiful Bootstrap-based interface

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file with the following variables:

```env
# Proxy Configuration
PROXY_PASSWORD=your_proxy_password

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_BUCKET_NAME=your_bucket_name
AWS_REGION=us-east-1

# Domain Configuration (Required for SEO)
DOMAIN=https://your-domain.com

# Google Analytics (Optional)
GA_MEASUREMENT_ID=GA_MEASUREMENT_ID

# Transcript Service Configuration (Required for transcript feature)
TRANSCRIPT_PROXY_USERNAME=your_transcript_proxy_username
TRANSCRIPT_PROXY_PASSWORD=your_transcript_proxy_password
```

### 3. Update Configuration

Edit the configuration in `youtube.py`:

```python
CONFIG = {
    "PROXY_PASSWORD": os.getenv("PROXY_PASSWORD"),
    "PROXY_USERNAMES": [
        "your-proxy-1", "your-proxy-2", "your-proxy-3",
        # Add your proxy usernames
    ],
    "AWS_ACCESS_KEY": os.getenv("AWS_ACCESS_KEY_ID"),
    "AWS_SECRET_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "AWS_BUCKET_NAME": os.getenv("AWS_BUCKET_NAME"),
    "AWS_REGION": os.getenv("AWS_REGION", "us-east-1")
}
```

### 4. Update Analytics (Optional)

Replace `GA_MEASUREMENT_ID` with your actual Google Analytics measurement ID:

```html
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
```

### 5. Update Domain URLs

Update the domain URLs in:
- `templates/base.html` (Open Graph and Twitter meta tags)
- `static/sitemap.xml`
- `static/robots.txt`

### 6. Run the Application

```bash
python youtube.py
```

The application will be available at `http://localhost:8000`

## Project Structure

```
├── templates/
│   ├── base.html          # Base template with SEO and ads
│   ├── index.html         # Main download page
│   ├── how_it_works.html  # How it works page
│   ├── privacy.html       # Privacy policy
│   └── terms.html         # Terms of service
├── static/
│   ├── css/
│   │   └── style.css      # Custom CSS styles
│   ├── js/
│   │   └── main.js        # JavaScript functionality
│   ├── images/            # Static images
│   ├── sitemap.xml        # SEO sitemap
│   └── robots.txt         # SEO robots file
├── youtube.py             # Main FastAPI application
├── main.py                # YouTube transcript API
└── requirements.txt       # Python dependencies
```

## API Endpoints

### Frontend Routes
- `GET /` - Main download page
- `GET /how-it-works` - How it works page
- `GET /privacy` - Privacy policy
- `GET /terms` - Terms of service
- `GET /sitemap.xml` - SEO sitemap
- `GET /robots.txt` - SEO robots file

### API Routes
- `GET /api/health` - API health check
- `POST /download` - Download video (frontend)
- `POST /api/download` - Download video (API)
- `POST /transcript` - Get transcript (frontend)
- `POST /api/transcript` - Get transcript (API)
- `POST /download-async` - Async download
- `GET /status/{download_id}` - Download status

## SEO Features

- **Meta Tags**: Comprehensive meta tags for social sharing
- **Open Graph**: Facebook and Twitter card support
- **Structured Data**: JSON-LD schema markup
- **Sitemap**: XML sitemap for search engines
- **Robots.txt**: Search engine crawling instructions
- **Canonical URLs**: Prevent duplicate content issues

## Analytics & Tracking

- **Google Analytics**: User behavior tracking
- **Event Tracking**: Download success/failure events
- **User Engagement**: Form interactions and page views

## Customization

### Styling
Edit `static/css/style.css` to customize the appearance.

### JavaScript
Modify `static/js/main.js` to add custom functionality.

### Templates
Update HTML templates in the `templates/` directory.

## Production Deployment

1. **Environment**: Use a production WSGI server like Gunicorn
2. **Domain**: Update all domain references
3. **SSL**: Enable HTTPS for security
4. **CDN**: Use a CDN for static files
5. **Monitoring**: Set up application monitoring

## License

This project is for educational purposes. Please respect YouTube's Terms of Service and copyright laws when using this application.

## Support

For issues and questions, please check the documentation or create an issue in the repository.
