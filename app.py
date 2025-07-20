from flask import Flask, render_template, request, send_from_directory, jsonify, Response
import yt_dlp
import os
import subprocess
import requests
from datetime import datetime
import time
import threading
from threading import Lock
import json
import urllib3
import socket
import base64  # Needed to decode the cookies from base64 (not used for public videos)

# ==============================
# Public-Only Mode Configuration
# ==============================

# Skip setting cookies, because public videos don't need login.
# Keeping this in case I switch back later.

cookie_b64 = os.getenv("YT_COOKIES_B64")  # Render environment variable
cookie_path = "/tmp/cookies.txt"  # Temporary file location to save decoded cookies

if cookie_b64:
    # Only needed login access needed — currently NOT used.
    with open(cookie_path, "wb") as f:
        f.write(base64.b64decode(cookie_b64))
else:
    # You can safely ignore this warning in public-only mode
    print("YT_COOKIES_B64 not set — skipping cookies setup for public videos.")

# ==========================================
# Network settings and Flask app setup
# ==========================================

urllib3.disable_warnings()
socket.setdefaulttimeout(30)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB limit
progress_lock = Lock()
current_progress = {}

# Need to ensure required directories exist for storing downloaded files and thumbnails.
os.makedirs('static/thumbnails', exist_ok=True)
os.makedirs('downloads', exist_ok=True)

def is_ffmpeg_installed():
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def progress_hook(d, video_id):
    if d['status'] == 'downloading':
        downloaded = d.get("downloaded_bytes", 0)
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        percent_float = (downloaded / total * 100) if total else 0.0

        with progress_lock:
            current_progress[video_id] = percent_float
            print(f"\rDownload Progress: {percent_float:.2f}%", end='', flush=True)

    elif d['status'] == 'finished':
        with progress_lock:
            current_progress[video_id] = 100
            print("\nDownload completed!")

def delete_file_later(path, delay=10):
    time.sleep(delay)
    if os.path.exists(path):
        os.remove(path)
        print(f"[CLEANUP] Deleted file: {path}")

@app.route("/")
def home():
    current_time = datetime.now().strftime("%H:%M") 
    return render_template("index.html", time=current_time)

@app.route('/progress/<video_id>')
def progress(video_id):
    def generate():
        last_progress = -1
        while True:
            with progress_lock:
                progress = current_progress.get(video_id, 0)

            if progress != last_progress:
                yield f"data: {json.dumps({'progress': progress})}\n\n"
                last_progress = progress

            if progress >= 100:
                yield f"data: {json.dumps({'progress': 100, 'completed': True})}\n\n"
                break

            time.sleep(0.5)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )

def save_thumbnail_async(url, path):
    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://www.youtube.com/'
        }, timeout=3)
        if response.ok:
            with open(path, 'wb') as f:
                f.write(response.content)
    except:
        pass

# Retrieve the YouTube video URL submitted from the frontend form.
@app.route('/get_info', methods=['POST'])
def get_info():
    video_url = request.form.get('url', '').strip()

    if not video_url:
        return jsonify({'status': 'error', 'message': 'Please enter a valid YouTube video URL.'}), 400

    try:
        ydl_opts = {
            'quiet': True,
            # 'cookiefile': cookie_path, Removed: Not needed for public videos
            'extract_flat': False,
            'skip_download': True,
            'socket_timeout': 10,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            },
            'referer': 'https://www.youtube.com/',
            'retries': 3
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            video_id = info.get('id')
            thumbnail_url = info.get('thumbnail')

            with progress_lock:
                current_progress[video_id] = 0

            return jsonify({
                'status': 'success',
                'title': info.get('title', 'YouTube Video'),
                'thumbnail': thumbnail_url,
                'duration': info.get('duration', 0),
                'video_id': video_id
            })

    except yt_dlp.utils.DownloadError as de:
        error_msg = str(de)

        if "Sign in to confirm you’re not a bot" in error_msg:
            return jsonify({
                'status': 'error',
                'message': (
                    "This video requires login. Please try a different public video."
                )
            }), 403
        elif "This video is unavailable" in error_msg:
            return jsonify({'status': 'error', 'message': 'This video is unavailable. Please check the URL and try again.'}), 404
        elif "login" in error_msg.lower():
            return jsonify({'status': 'error', 'message': 'This video requires you to be signed in. Please try a different public video.'}), 403
        elif "Video unavailable in your country" in error_msg:
            return jsonify({'status': 'error', 'message': 'This video is not available in your region.'}), 403
        elif "Unsupported URL" in error_msg:
            return jsonify({'status': 'error', 'message': 'The provided URL is not a valid YouTube video link.'}), 400
        else:
            return jsonify({'status': 'error', 'message': 'Could not retrieve video info. Please try again later.'}), 500

    except yt_dlp.utils.ExtractorError:
        return jsonify({'status': 'error', 'message': 'Failed to extract video data. The video may be private or age-restricted.'}), 403

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Something went wrong: {str(e)}'}), 500
    
#  Handle download request (MP4 or MP3) 

@app.route('/download', methods=['GET'])
def download():
    video_url = request.args.get('url')
    download_type = request.args.get('download_type', 'mp4')
    video_id = request.args.get('video_id')

    if not video_url or not video_id:
        return jsonify({'status': 'error', 'message': 'URL and video ID required'}), 400

    try:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' if download_type == 'mp4' else 'bestaudio/best',

            # 'cookiefile': cookie_path, Removed: Not needed for public video downloads

            'outtmpl': f'downloads/%(id)s.%(ext)s',
            'quiet': True,
            'progress': True,
            'newline': True,
            'progress_hooks': [lambda d: progress_hook(d, video_id)],
            'socket_timeout': 30,
            'extract_flat': True,
            'force_ipv4': True,
            'retries': 10,
            'fragment_retries': 10,
            'skip_unavailable_fragments': True,
            'no_warnings': False,
            'ignoreerrors': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Referer': 'https://www.youtube.com/'
            },
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls']
                }
            },
            'compat_opts': {
                'no-youtube-unavailable-videos': True
            }
        }

        if download_type == 'mp3':
            if not is_ffmpeg_installed():
                return jsonify({'status': 'error', 'message': 'FFmpeg is required for MP3 conversion'}), 400
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            filename = ydl.prepare_filename(info)

            if download_type == 'mp3':
                filename = filename.replace('.webm', '.mp3').replace('.m4a', '.mp3')

            print(f"\n[INFO] Starting download: {info.get('title', 'Unknown')}")
            ydl.download([video_url])

            with progress_lock:
                current_progress[video_id] = 100

            filepath = os.path.join('downloads', os.path.basename(filename))

            threading.Thread(target=delete_file_later, args=(filepath,)).start()

            return send_from_directory(
                'downloads',
                os.path.basename(filename),
                as_attachment=True,
                mimetype='audio/mpeg' if download_type == 'mp3' else 'video/mp4',
                download_name=os.path.basename(filename)
            )

    except Exception as e:
        with progress_lock:
            current_progress[video_id] = -1

        error_message = str(e).lower()

        if "login required" in error_message or "sign in" in error_message:
            user_message = "This video requires login. Please try a different public video."
        elif "private" in error_message:
            user_message = "This video is private and cannot be downloaded."
        elif "unavailable" in error_message:
            user_message = "This video is not available in your region or has been removed."
        elif "copyright" in error_message:
            user_message = "This video is restricted due to copyright."
        else:
            user_message = "An error occurred while trying to download the video. Please check the URL and try again."

        print(f"[ERROR] {str(e)}")
        return jsonify({'status': 'error', 'message': user_message}), 500

if __name__ == '__main__':
    app.run(debug=True)
