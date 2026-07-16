import os
from flask import Flask, redirect, jsonify, request
import yt_dlp

app = Flask(__name__)

def get_youtube_url(video_id, is_live=False):
    ydl_opts = {
        'format': 'b/best' if is_live else 'best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('url')
    except Exception:
        return None

@app.route('/live/<video_id>.m3u8')
def get_live(video_id):
    stream_url = get_youtube_url(video_id, is_live=True)
    if stream_url:
        return redirect(stream_url, code=302)
    return jsonify({"status": "error", "message": "Gagal mengambil live stream"}), 500

@app.route('/live/<video_id>.mp4')
def get_mp4(video_id):
    stream_url = get_youtube_url(video_id, is_live=False)
    if stream_url:
        # Di Vercel kita harus langsung redirect agar tidak terkena limit timeout 10 detik
        return redirect(stream_url, code=302)
    return jsonify({"status": "error", "message": "Gagal mengambil video MP4"}), 500

# Bagian ini penting agar Flask terbaca oleh Vercel
def handler(request, response):
    return app(request, response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
