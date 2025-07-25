# VideoShrink - Free MP4 Compressor for YouTube

A web-based MP4 video compressor optimized for YouTube uploads. Compress your videos while maintaining high quality with an intuitive drag-and-drop interface.

🌐 **Live Site:** [videoshrink.com](https://videoshrink.com)

## Features

- **Web-based Interface**: No software installation required
- **Drag & Drop Upload**: Easy file selection with visual feedback
- **Real-time Progress**: Live compression progress monitoring
- **YouTube Optimized**: H.264 codec with optimal settings
- **High Audio Quality**: AAC encoding at 128k bitrate
- **Multiple Bitrate Options**: 1M, 1.5M, 2M, 3M bitrates available
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Secure Processing**: Files automatically deleted after download

## Tech Stack

- **Backend**: Python Flask
- **Video Processing**: FFmpeg
- **Frontend**: HTML5, CSS3, JavaScript
- **Deployment**: Heroku
- **Domain**: Squarespace DNS

## Local Development

### Prerequisites
1. Python 3.6+
2. FFmpeg installed on system
3. Git

### Installation
```bash
git clone https://github.com/yourusername/videoshrink.git
cd videoshrink
pip install -r requirements.txt
```

### Run Locally
```bash
python app.py
```
Visit `http://localhost:5000`

### Environment Variables
```bash
PORT=5000
FLASK_ENV=development
```

## Project Structure

```
videoshrink/
├── app.py                 # Flask web application
├── mp4_compressor.py      # Core compression logic
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Main web interface
├── static/               # CSS, JS, images
├── uploads/              # Temporary upload storage
├── outputs/              # Compressed video storage
└── README.md
```

## API Endpoints

- `GET /` - Main web interface
- `POST /upload` - Upload and start compression
- `GET /status/<job_id>` - Check compression progress
- `GET /download/<job_id>` - Download compressed video
- `GET /debug` - FFmpeg path debugging

## Compression Settings

| Bitrate Option | Resolution | Typical Reduction |
|----------------|------------|-------------------|
| 1M             | 480p       | 40-60%           |
| 1.5M           | 720p       | 45-65%           |
| 2M (default)   | 1080p      | 50-70%           |
| 3M             | 1080p+     | 45-65%           |

## Deployment

### Heroku Deployment
```bash
heroku create your-app-name
heroku buildpacks:add --index 1 https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
heroku buildpacks:add --index 2 heroku/python
git push heroku main
```

### Custom Domain Setup
```bash
heroku domains:add yourdomain.com
heroku domains:add www.yourdomain.com
heroku certs:auto:enable
```

## File Size Limits

- **Maximum Upload**: 500MB
- **Supported Format**: MP4 only
- **Processing Time**: ~1-3 minutes per 100MB

## Browser Support

- ✅ Chrome 60+
- ✅ Firefox 55+
- ✅ Safari 12+
- ✅ Edge 79+

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:
- 📧 Email: support@videoshrink.com
- 🐛 Issues: GitHub Issues page
- 📖 Docs: This README