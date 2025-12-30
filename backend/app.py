"""
Spotify Podcast Summarizer - Backend API
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import ssl

# 確保 ffmpeg 路徑在 PATH 中
home_bin = os.path.expanduser("~/bin")
if os.path.exists(home_bin):
    os.environ["PATH"] = f"{home_bin}:{os.environ.get('PATH', '')}"

# 修復 macOS SSL 憑證問題
try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
except ImportError:
    pass

# 創建不驗證的 SSL 上下文（開發用）
ssl._create_default_https_context = ssl._create_unverified_context

from services.spotify import SpotifyService
from services.transcriber import TranscriberService
from services.summarizer import SummarizerService

load_dotenv()

app = Flask(__name__)
CORS(app)

# 初始化服務
spotify_service = SpotifyService()
transcriber_service = TranscriberService()
summarizer_service = SummarizerService()


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({"status": "ok", "message": "Server is running"})


@app.route('/api/summarize', methods=['POST'])
def summarize_podcast():
    """
    摘要 Podcast 節目

    Request Body:
        - url: Spotify Podcast 連結

    Response:
        - title: 節目標題
        - summary: 重點摘要（條列式）
        - timestamps: 關鍵時間軸
    """
    data = request.get_json()

    if not data or 'url' not in data:
        return jsonify({"error": "請提供 Spotify Podcast 連結"}), 400

    url = data['url']

    try:
        # Step 1: 下載 Podcast（YouTube 會優先嘗試取得字幕）
        print(f"[Step 1] 開始下載: {url}")
        audio_path, metadata = spotify_service.download_podcast(url)

        # Step 2: 取得文字稿
        # V2: 如果已有字幕，直接使用（跳過 Whisper）
        if metadata.get('has_subtitles') and metadata.get('transcript'):
            print(f"[Step 2] 使用 YouTube 字幕（快速模式）")
            transcript = metadata['transcript']
            print(f"[Step 2] 字幕載入完成，共 {len(transcript.get('segments', []))} 段")
        else:
            print(f"[Step 1] 下載完成: {audio_path}")
            print(f"[Step 2] 開始轉錄...")
            transcript = transcriber_service.transcribe(audio_path)
            print(f"[Step 2] 轉錄完成，共 {len(transcript.get('segments', []))} 段")

        # Step 3: 生成摘要
        print(f"[Step 3] 開始生成摘要...")
        summary = summarizer_service.generate_summary(transcript, metadata)
        print(f"[Step 3] 摘要完成")

        # 清理暫存檔案
        if audio_path:
            spotify_service.cleanup(audio_path)

        return jsonify({
            "success": True,
            "version": "v3",
            "title": metadata.get('title', '未知標題'),
            "duration": metadata.get('duration', ''),
            "source": "subtitles" if metadata.get('has_subtitles') else "whisper",
            # V3 精華內容版
            "one_liner": summary.get('one_liner', ''),
            "article": summary.get('article', []),
            "insights": summary.get('insights', []),
            "data_highlights": summary.get('data_highlights', []),
            "quotes": summary.get('quotes', []),
            "timestamps": summary.get('timestamps', [])
        })

    except Exception as e:
        import traceback
        print(f"[ERROR] {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)
