import os
from flask import Flask, Response, redirect, jsonify, request
import subprocess
import requests
import threading
import time

app = Flask(__name__)
stream_cache = {}

def get_yt_link(video_id, is_live=False):
    url = f"https://www.youtube.com/watch?v={video_id}"
    if is_live:
        try:
            cmd = ["yt-dlp", "-g", "--youtube-include-hls-manifest", "-f", "b/best", "--no-warnings", "--quiet", url]
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')
            lines = [line.strip() for line in output.splitlines() if line.strip().startswith('http')]
            if lines: return lines[0]
        except Exception: pass
    else:
        try:
            cmd = ["yt-dlp", "-g", "-f", "best[ext=mp4]/bestvideo+bestaudio/best", "--no-warnings", "--quiet", url]
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')
            lines = [line.strip() for line in output.splitlines() if line.strip().startswith('http')]
            if lines: return lines[0]
        except Exception: pass
    return None

def update_cache(video_id, is_live):
    cache_key = f"{video_id}_{is_live}"
    stream_url = get_yt_link(video_id, is_live)
    if stream_url:
        stream_cache[cache_key] = {'url': stream_url, 'timestamp': time.time()}

@app.route('/live/<video_id>.m3u8')
def get_live_stream(video_id):
    cache_key = f"{video_id}_True"
    now = time.time()
    cache = stream_cache.get(cache_key)
    if not cache or (now - cache['timestamp']) > 900:
        if not cache:
            update_cache(video_id, is_live=True)
            cache = stream_cache.get(cache_key)
        else:
            threading.Thread(target=update_cache, args=(video_id, True)).start()
    if cache and 'url' in cache: return redirect(cache['url'])
    return jsonify({"status": "error", "message": "Gagal mengambil live stream."}), 500

@app.route('/live/<video_id>.mp4')
def get_mp4_stream(video_id):
    cache_key = f"{video_id}_False"
    now = time.time()
    cache = stream_cache.get(cache_key)
    if not cache or (now - cache['timestamp']) > 900:
        if not cache:
            update_cache(video_id, is_live=False)
            cache = stream_cache.get(cache_key)
        else:
            threading.Thread(target=update_cache, args=(video_id, False)).start()
    if not cache or 'url' not in cache: return jsonify({"status": "error", "message": "Gagal mengambil video MP4."}), 500

    stream_url = cache['url']
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Connection': 'keep-alive'}
    range_header = request.headers.get('Range', None)
    if range_header: headers['Range'] = range_header

    req = requests.get(stream_url, headers=headers, stream=True)
    response_headers = {'Content-Type': 'video/mp4', 'Accept-Ranges': 'bytes', 'Access-Control-Allow-Origin': '*'}
    if 'Content-Length' in req.headers: response_headers['Content-Length'] = req.headers['Content-Length']
    if 'Content-Range' in req.headers: response_headers['Content-Range'] = req.headers['Content-Range']

    def generate():
        for chunk in req.iter_content(chunk_size=1024 * 256):
            if chunk: yield chunk

    status_code = req.status_code if req.status_code in [200, 206] else 200
    return Response(generate(), status=status_code, headers=response_headers)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
