"""
Podcast 下載服務（透過 ListenNotes API 或直接 RSS）
"""
import os
import tempfile
import re
import uuid
import requests
import urllib3
import xml.etree.ElementTree as ET

# 暫時關閉 SSL 警告（開發用）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SpotifyService:
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.listennotes_api_key = os.getenv('LISTENNOTES_API_KEY', '')
        self.listennotes_base_url = 'https://listen-api.listennotes.com/api/v2'

    def download_podcast(self, url: str) -> tuple:
        """
        下載 Podcast 音訊

        Args:
            url: Spotify 或 YouTube Podcast 連結

        Returns:
            tuple: (音訊檔案路徑, 元資料)
        """
        if 'spotify.com' in url:
            return self._download_spotify_podcast(url)
        elif 'youtube.com' in url or 'youtu.be' in url:
            return self._download_youtube_podcast(url)
        else:
            raise ValueError("不支援的連結格式，請使用 Spotify 或 YouTube 連結")

    def _download_spotify_podcast(self, url: str) -> tuple:
        """透過 ListenNotes 或搜尋方式下載 Spotify Podcast"""
        episode_id = self._extract_spotify_episode_id(url)
        if not episode_id:
            raise ValueError("無效的 Spotify Podcast 連結")

        # 方法 1: 使用 ListenNotes API（如果有 API Key）
        if self.listennotes_api_key:
            try:
                return self._download_via_listennotes(episode_id, url)
            except Exception as e:
                print(f"ListenNotes API 失敗: {e}")

        # 方法 2: 從 Spotify oEmbed 取得標題，再搜尋 RSS
        try:
            return self._download_via_search(episode_id, url)
        except Exception as e:
            raise Exception(
                f"無法下載此 Podcast。\n"
                f"建議：請到 ListenNotes.com 申請免費 API Key 以獲得更好的支援。\n"
                f"錯誤：{str(e)}"
            )

    def _download_via_listennotes(self, episode_id: str, original_url: str) -> tuple:
        """使用 ListenNotes API 搜尋並下載"""
        headers = {'X-ListenAPI-Key': self.listennotes_api_key}

        # 先從 Spotify 取得標題
        title = self._get_spotify_title(episode_id)

        # 用標題搜尋 ListenNotes
        search_url = f"{self.listennotes_base_url}/search"
        params = {
            'q': title,
            'type': 'episode',
            'len_min': 1,
        }

        response = requests.get(search_url, headers=headers, params=params, timeout=30, verify=False)
        response.raise_for_status()
        data = response.json()

        if not data.get('results'):
            raise Exception("在 ListenNotes 找不到此節目")

        # 取第一個結果
        episode = data['results'][0]
        audio_url = episode.get('audio')

        if not audio_url:
            raise Exception("找不到音訊連結")

        # 下載音訊
        audio_file = self._download_audio_file(audio_url)

        metadata = {
            'title': episode.get('title_original', title),
            'url': original_url,
            'duration': self._format_duration(episode.get('audio_length_sec', 0)),
            'podcast_name': episode.get('podcast', {}).get('title_original', ''),
        }

        return audio_file, metadata

    def _download_via_search(self, episode_id: str, original_url: str) -> tuple:
        """透過公開搜尋取得 Podcast RSS 並下載"""
        # 從 Spotify oEmbed 取得標題
        title = self._get_spotify_title(episode_id)

        if not title:
            raise Exception("無法取得節目標題")

        # 嘗試用 iTunes Search API 找到 RSS（免費且不需 API Key）
        itunes_url = "https://itunes.apple.com/search"
        params = {
            'term': title,
            'media': 'podcast',
            'entity': 'podcastEpisode',
            'limit': 10,
        }

        response = requests.get(itunes_url, params=params, timeout=30, verify=False)
        response.raise_for_status()
        data = response.json()

        results = data.get('results', [])

        # 找到最匹配的結果
        audio_url = None
        episode_title = title
        podcast_name = ''
        duration = 0

        for result in results:
            if result.get('episodeUrl'):
                audio_url = result['episodeUrl']
                episode_title = result.get('trackName', title)
                podcast_name = result.get('collectionName', '')
                duration = result.get('trackTimeMillis', 0) // 1000
                break

        if not audio_url:
            raise Exception(f"找不到「{title}」的音訊來源")

        # 下載音訊
        audio_file = self._download_audio_file(audio_url)

        metadata = {
            'title': episode_title,
            'url': original_url,
            'duration': self._format_duration(duration),
            'podcast_name': podcast_name,
        }

        return audio_file, metadata

    def _get_spotify_title(self, episode_id: str) -> str:
        """從 Spotify oEmbed API 取得節目標題"""
        try:
            embed_url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/episode/{episode_id}"
            response = requests.get(embed_url, timeout=10, verify=False)
            if response.status_code == 200:
                data = response.json()
                return data.get('title', '')
        except Exception:
            pass
        return ''

    def _download_youtube_podcast(self, url: str) -> tuple:
        """下載 YouTube Podcast（優先取得字幕）"""
        import shutil
        # 自動尋找 yt-dlp：優先系統安裝，其次本機 venv
        ytdlp_path = shutil.which('yt-dlp')
        if not ytdlp_path:
            venv_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ytdlp_path = os.path.join(venv_path, 'venv', 'bin', 'yt-dlp')

        unique_id = str(uuid.uuid4())[:8]

        import subprocess

        # 取得影片資訊
        print("[YouTube] 取得影片資訊...")
        info_cmd = [ytdlp_path, '--print', '%(title)s', '--print', '%(duration)s', '--no-download', url]
        info_result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=60)
        info_lines = info_result.stdout.strip().split('\n')
        title = info_lines[0] if info_lines else '未知標題'
        duration = int(info_lines[1]) if len(info_lines) > 1 and info_lines[1].isdigit() else 0

        metadata = {
            'title': title,
            'url': url,
            'duration': self._format_duration(duration),
        }

        # V2: 優先嘗試取得字幕（速度快很多）
        print("[YouTube] 嘗試取得字幕...")
        subtitle_result = self._get_youtube_subtitles(url, ytdlp_path, unique_id)

        if subtitle_result:
            print("[YouTube] 成功取得字幕！跳過音訊下載")
            metadata['has_subtitles'] = True
            metadata['transcript'] = subtitle_result
            return None, metadata  # 不需要音訊檔案

        # 沒有字幕，下載音訊
        print("[YouTube] 無可用字幕，下載音訊...")
        output_file = os.path.join(self.temp_dir, f"podcast_{unique_id}.mp3")

        download_cmd = [
            ytdlp_path, '-x', '--audio-format', 'mp3',
            '-o', output_file, url
        ]
        result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=600)

        if not os.path.exists(output_file):
            # 嘗試找其他格式
            for ext in ['.m4a', '.webm', '.opus']:
                alt_file = output_file.replace('.mp3', ext)
                if os.path.exists(alt_file):
                    output_file = alt_file
                    break

        if not os.path.exists(output_file):
            raise Exception("YouTube 下載失敗")

        metadata['has_subtitles'] = False
        return output_file, metadata

    def _get_youtube_subtitles(self, url: str, ytdlp_path: str, unique_id: str) -> dict:
        """嘗試取得 YouTube 字幕"""
        import subprocess

        subtitle_file = os.path.join(self.temp_dir, f"subtitle_{unique_id}")

        # 嘗試取得字幕（優先中文，其次英文，最後自動生成）
        for lang in ['zh-TW', 'zh-Hant', 'zh', 'en', 'en-US']:
            try:
                cmd = [
                    ytdlp_path,
                    '--write-sub',
                    '--write-auto-sub',
                    '--sub-lang', lang,
                    '--sub-format', 'vtt',
                    '--skip-download',
                    '-o', subtitle_file,
                    url
                ]
                subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                # 檢查是否有字幕檔案
                for ext in ['.vtt', f'.{lang}.vtt']:
                    vtt_file = subtitle_file + ext
                    if os.path.exists(vtt_file):
                        transcript = self._parse_vtt_file(vtt_file)
                        os.remove(vtt_file)  # 清理
                        if transcript and len(transcript.get('segments', [])) > 0:
                            return transcript
            except Exception as e:
                print(f"[YouTube] 取得 {lang} 字幕失敗: {e}")
                continue

        return None

    def _parse_vtt_file(self, vtt_path: str) -> dict:
        """解析 VTT 字幕檔案"""
        try:
            with open(vtt_path, 'r', encoding='utf-8') as f:
                content = f.read()

            segments = []
            full_text = []

            # 解析 VTT 格式
            lines = content.split('\n')
            current_start = 0
            current_end = 0
            current_text = []

            for line in lines:
                line = line.strip()

                # 跳過 WEBVTT 標頭和空行
                if not line or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
                    continue

                # 時間行格式: 00:00:00.000 --> 00:00:05.000
                if '-->' in line:
                    # 儲存前一段
                    if current_text:
                        text = ' '.join(current_text).strip()
                        # 移除重複的自動字幕標記
                        text = re.sub(r'<[^>]+>', '', text)
                        if text and text not in full_text[-3:] if full_text else True:
                            segments.append({
                                'start': current_start,
                                'end': current_end,
                                'text': text
                            })
                            full_text.append(text)

                    # 解析新時間
                    time_parts = line.split('-->')
                    current_start = self._vtt_time_to_seconds(time_parts[0].strip())
                    current_end = self._vtt_time_to_seconds(time_parts[1].strip().split()[0])
                    current_text = []

                # 數字序號行（跳過）
                elif line.isdigit():
                    continue

                # 文字內容
                else:
                    current_text.append(line)

            # 最後一段
            if current_text:
                text = ' '.join(current_text).strip()
                text = re.sub(r'<[^>]+>', '', text)
                if text:
                    segments.append({
                        'start': current_start,
                        'end': current_end,
                        'text': text
                    })
                    full_text.append(text)

            return {
                'text': ' '.join(full_text),
                'segments': segments
            }
        except Exception as e:
            print(f"[YouTube] 解析字幕失敗: {e}")
            return None

    def _vtt_time_to_seconds(self, time_str: str) -> float:
        """將 VTT 時間格式轉換為秒數"""
        try:
            # 格式: 00:00:00.000 或 00:00.000
            parts = time_str.replace(',', '.').split(':')
            if len(parts) == 3:
                hours, minutes, seconds = parts
                return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            elif len(parts) == 2:
                minutes, seconds = parts
                return int(minutes) * 60 + float(seconds)
        except:
            pass
        return 0

    def _extract_spotify_episode_id(self, url: str) -> str:
        """從 URL 提取 Spotify episode ID"""
        pattern = r'spotify\.com/episode/([a-zA-Z0-9]+)'
        match = re.search(pattern, url)
        return match.group(1) if match else None

    def _download_audio_file(self, audio_url: str) -> str:
        """下載音訊檔案"""
        unique_id = str(uuid.uuid4())[:8]

        # 根據 URL 判斷副檔名
        ext = '.mp3'
        if '.m4a' in audio_url:
            ext = '.m4a'
        elif '.wav' in audio_url:
            ext = '.wav'

        output_file = os.path.join(self.temp_dir, f"podcast_{unique_id}{ext}")

        response = requests.get(audio_url, stream=True, timeout=300, verify=False, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        response.raise_for_status()

        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return output_file

    def _format_duration(self, seconds: int) -> str:
        """格式化時長"""
        if not seconds or seconds <= 0:
            return ""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours > 0:
            return f"{hours} 小時 {minutes} 分鐘"
        return f"{minutes} 分鐘"

    def cleanup(self, file_path: str):
        """清理暫存檔案"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
