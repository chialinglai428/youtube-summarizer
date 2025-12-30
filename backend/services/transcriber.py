"""
語音轉文字服務 (使用 OpenAI Whisper)
Whisper 為可選依賴，主要使用 YouTube 字幕模式
"""
import os

# Whisper 為可選依賴
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("[Transcriber] Whisper 未安裝，僅支援字幕模式")


class TranscriberService:
    def __init__(self, model_size: str = "base"):
        """
        初始化 Whisper 模型

        Args:
            model_size: 模型大小 (tiny, base, small, medium, large)
        """
        self.model = None
        self.model_size = model_size
        self.available = WHISPER_AVAILABLE

    def _load_model(self):
        """延遲載入模型"""
        if not WHISPER_AVAILABLE:
            raise RuntimeError("Whisper 未安裝，無法進行語音轉文字。請使用有字幕的 YouTube 影片。")
        if self.model is None:
            print(f"載入 Whisper {self.model_size} 模型...")
            self.model = whisper.load_model(self.model_size)
        return self.model

    def transcribe(self, audio_path: str) -> dict:
        """
        將音訊轉換為文字（含時間軸）

        Args:
            audio_path: 音訊檔案路徑

        Returns:
            dict: {
                "text": 完整文字,
                "segments": [{
                    "start": 開始時間（秒）,
                    "end": 結束時間（秒）,
                    "text": 該段文字
                }]
            }
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"找不到音訊檔案: {audio_path}")

        model = self._load_model()

        print("正在轉換語音為文字...")
        result = model.transcribe(
            audio_path,
            language="zh",  # 可改為 None 讓模型自動偵測
            verbose=False
        )

        return {
            "text": result["text"],
            "segments": [
                {
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip()
                }
                for segment in result["segments"]
            ]
        }

    def format_timestamp(self, seconds: float) -> str:
        """將秒數格式化為 HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
