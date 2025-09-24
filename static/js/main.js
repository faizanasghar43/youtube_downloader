// Main JavaScript for YouTube Downloader

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize animations
    initAnimations();
    
    // Initialize form enhancements
    initFormEnhancements();
    
    // Initialize URL validation
    initUrlValidation();
    
    // Initialize ad loading
    initAdLoading();
});

// Animation initialization
function initAnimations() {
    // Add fade-in animation to elements as they come into view
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe elements for animation
    document.querySelectorAll('.feature-card, .card, .accordion-item').forEach(el => {
        observer.observe(el);
    });
}

// Form enhancements
function initFormEnhancements() {
    const form = document.getElementById('downloadForm');
    const urlInput = document.getElementById('videoUrl');
    const qualitySelect = document.getElementById('quality');
    const formatSelect = document.getElementById('format');
    
    // Auto-detect YouTube URL format
    urlInput.addEventListener('input', function() {
        const url = this.value;
        if (isValidYouTubeUrl(url)) {
            this.classList.remove('is-invalid');
            this.classList.add('is-valid');
            
            // Extract video ID for preview
            const videoId = extractVideoId(url);
            if (videoId) {
                showVideoPreview(videoId);
            }
        } else if (url.length > 0) {
            this.classList.remove('is-valid');
            this.classList.add('is-invalid');
        } else {
            this.classList.remove('is-valid', 'is-invalid');
        }
    });
    
    // Format change handler
    formatSelect.addEventListener('change', function() {
        if (this.value === 'true') {
            // Audio only - hide quality options
            qualitySelect.parentElement.style.display = 'none';
        } else {
            // Video - show quality options
            qualitySelect.parentElement.style.display = 'block';
        }
    });
}

// URL validation
function initUrlValidation() {
    const urlInput = document.getElementById('videoUrl');
    
    // Real-time URL validation
    urlInput.addEventListener('blur', function() {
        validateYouTubeUrl(this);
    });
}

// Validate YouTube URL
function validateYouTubeUrl(input) {
    const url = input.value.trim();
    
    if (!url) {
        input.classList.remove('is-valid', 'is-invalid');
        return false;
    }
    
    if (isValidYouTubeUrl(url)) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        return true;
    } else {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
        return false;
    }
}

// Check if URL is a valid YouTube URL
function isValidYouTubeUrl(url) {
    const patterns = [
        /^https?:\/\/(www\.)?youtube\.com\/watch\?v=[\w-]+/,
        /^https?:\/\/(www\.)?youtu\.be\/[\w-]+/,
        /^https?:\/\/(www\.)?youtube\.com\/embed\/[\w-]+/,
        /^https?:\/\/(www\.)?youtube\.com\/v\/[\w-]+/
    ];
    
    return patterns.some(pattern => pattern.test(url));
}

// Extract video ID from URL
function extractVideoId(url) {
    const patterns = [
        /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([\w-]+)/,
    ];
    
    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match) {
            return match[1];
        }
    }
    return null;
}

// Show video preview
function showVideoPreview(videoId) {
    // Remove existing preview
    const existingPreview = document.getElementById('videoPreview');
    if (existingPreview) {
        existingPreview.remove();
    }
    
    // Create preview element
    const preview = document.createElement('div');
    preview.id = 'videoPreview';
    preview.className = 'mt-3 p-3 bg-light rounded';
    preview.innerHTML = `
        <div class="row align-items-center">
            <div class="col-md-2">
                <img src="https://img.youtube.com/vi/${videoId}/mqdefault.jpg" 
                     alt="Video thumbnail" class="img-fluid rounded">
            </div>
            <div class="col-md-10">
                <h6 class="mb-1">Video Preview</h6>
                <p class="text-muted mb-0">Ready to download this video</p>
            </div>
        </div>
    `;
    
    // Insert after URL input
    const urlInput = document.getElementById('videoUrl');
    urlInput.parentElement.parentElement.appendChild(preview);
}

// Initialize ad loading
function initAdLoading() {
    // No ads to load currently
    // This function is kept for future ad integration
}

// Utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
}

// Error handling
function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');
    
    errorText.textContent = message;
    errorDiv.style.display = 'block';
    
    // Scroll to error
    errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
    
    // Track error
    if (typeof gtag !== 'undefined') {
        gtag('event', 'error', {
            'event_category': 'user_error',
            'event_label': message
        });
    }
}

function hideError() {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.style.display = 'none';
}

// Success handling
function showSuccess(message, videoInfo, downloadUrl) {
    const resultDiv = document.getElementById('downloadResult');
    const resultMessage = document.getElementById('resultMessage');
    const videoInfoDiv = document.getElementById('videoInfo');
    const downloadLink = document.getElementById('downloadLink');
    
    resultMessage.textContent = message;
    
    if (videoInfo) {
        const infoHtml = `
            <div class="row">
                <div class="col-md-6">
                    <strong>Title:</strong> ${videoInfo.title}<br>
                    <strong>Duration:</strong> ${formatDuration(videoInfo.duration)}
                </div>
                <div class="col-md-6">
                    <strong>Channel:</strong> ${videoInfo.uploader}<br>
                    <strong>Views:</strong> ${videoInfo.view_count.toLocaleString()}
                </div>
            </div>
        `;
        videoInfoDiv.innerHTML = infoHtml;
    }
    
    if (downloadUrl) {
        downloadLink.href = downloadUrl;
    }
    
    resultDiv.style.display = 'block';
    
    // Scroll to result
    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
    
    // Track success
    if (typeof gtag !== 'undefined') {
        gtag('event', 'download_success', {
            'event_category': 'engagement',
            'event_label': 'video_downloaded'
        });
    }
}

function hideSuccess() {
    const resultDiv = document.getElementById('downloadResult');
    resultDiv.style.display = 'none';
}

// Loading state management
function showLoading() {
    const spinner = document.getElementById('loadingSpinner');
    const downloadBtn = document.getElementById('downloadBtn');
    
    spinner.style.display = 'block';
    downloadBtn.disabled = true;
    downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
    
    // Hide other messages
    hideError();
    hideSuccess();
}

function hideLoading() {
    const spinner = document.getElementById('loadingSpinner');
    const downloadBtn = document.getElementById('downloadBtn');
    
    spinner.style.display = 'none';
    downloadBtn.disabled = false;
    downloadBtn.innerHTML = '<i class="fas fa-download me-2"></i>Download Video';
}

// Copy to clipboard functionality
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            showToast('Copied to clipboard!');
        });
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showToast('Copied to clipboard!');
    }
}

// Toast notification
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas fa-check-circle me-2"></i>
            ${message}
        </div>
    `;
    
    // Add styles
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #28a745;
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        z-index: 9999;
        animation: slideInRight 0.3s ease-out;
    `;
    
    document.body.appendChild(toast);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// Add CSS for toast animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
