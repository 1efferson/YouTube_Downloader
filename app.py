from flask import Flask, render_template, request, send_from_directory, jsonify, Response
import yt_dlp
import os
import subprocess
import requests
from datetime import datetime
import hashlib
import time
from threading import Lock, Thread
import json
import sys
import urllib3
import socket

# Network fixes
urllib3.disable_warnings()
socket.setdefaulttimeout(30)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024
progress_lock = Lock()
current_progress = {}

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
        if total:
            percent_float = downloaded / total * 100
        else:
            percent_float = 0.0

        with progress_lock:
            current_progress[video_id] = percent_float
            print(f"\rDownload Progress: {percent_float:.2f}%", end='', flush=True)
    elif d['status'] == 'finished':
        with progress_lock:
            current_progress[video_id] = 100
            print("\nDownload completed!")

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

from threading import Thread

@app.route('/get_info', methods=['POST'])
def get_info():
    video_url = request.form.get('url', '').strip()

    if not video_url:
        return jsonify({'status': 'error', 'message': 'Please enter a YouTube URL'}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': False,
            'skip_download': True,
            'socket_timeout': 10,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
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
                'thumbnail': info.get('thumbnail'),  # direct YouTube URL here
                'duration': info.get('duration', 0),
                'video_id': video_id
})


    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



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
            'outtmpl': f'downloads/%(id)s.%(ext)s',
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

            print(f"\nStarting download: {info.get('title', 'Unknown')}")
            ydl.download([video_url])

            with progress_lock:
                current_progress[video_id] = 100

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
        print(f"\nDownload error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# @app.route('/thumbnails/<filename>')
# def serve_thumbnail(filename):
#     return send_from_directory('static/thumbnails', filename)

if __name__ == '__main__':
    app.run(debug=True)
