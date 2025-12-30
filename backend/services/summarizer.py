"""
AI 摘要生成服務 (使用 Claude API) - V2 深度洞察版
"""
import os
import anthropic
import json


class SummarizerService:
    def __init__(self):
        self.client = None

    def _get_client(self):
        """取得 Anthropic 客戶端"""
        if self.client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("請設定 ANTHROPIC_API_KEY 環境變數")
            self.client = anthropic.Anthropic(api_key=api_key)
        return self.client

    def generate_summary(self, transcript: dict, metadata: dict) -> dict:
        """
        生成 Podcast 深度摘要 (V2)

        Args:
            transcript: 語音轉文字結果 {"text": str, "segments": list}
            metadata: Podcast 元資料

        Returns:
            dict: {
                "one_liner": 一句話總結,
                "points": [關鍵洞察],
                "data_highlights": [數據亮點],
                "quotes": [金句摘錄],
                "chapters": [章節摘要],
                "timestamps": [時間軸]
            }
        """
        client = self._get_client()

        # 準備帶時間軸的文字稿
        segments_text = self._format_segments(transcript["segments"])

        prompt = f"""你是一位資深的內容編輯，擅長將長篇對談整理成有脈絡、易讀的精華文章。

## 節目資訊
- 標題：{metadata.get('title', '未知')}
- 時長：{metadata.get('duration', '未知')}

## 原始內容（含時間軸）
{segments_text}

## 任務：將對談整理成精華文章

請將這段對談內容重新組織成一篇有結構、有脈絡的精華文章。不是條列式摘要，而是讓讀者能快速掌握核心觀點的深度整理。

### 文章結構要求：

1. **一句話總結**（30字內）
   - 這集的核心主題與價值

2. **精華內容**（800-1200字）
   - 用流暢的段落呈現，不是條列式
   - 保留對談中的精彩觀點和論述邏輯
   - 適當引用原話增加可信度
   - 分成 3-5 個段落，每段有小標題
   - 語氣專業但易讀

3. **看點與延伸思考**（3-5 點）
   - 以商業分析師的角度，提出這集節目的獨特看點
   - 可以是：商業洞察、決策框架、反直覺觀點、值得深思的問題
   - 每點要有觀點和延伸思考，不只是摘要

4. **關鍵數據**（如有提及）
   - 格式：數據 → 意義

5. **金句摘錄**（2-3 句最精彩的原話）

6. **時間導航**（放最後，供想回看的人使用）
   - 5-8 個關鍵時間點

## 回覆格式（JSON）
```json
{{
    "one_liner": "一句話總結",
    "article": [
        {{
            "subtitle": "段落小標題",
            "content": "這是一段完整的文章內容，用流暢的文字描述觀點和論述，可以引用「對談中的原話」來增加可信度。這段應該有 150-250 字左右，讓讀者能理解完整的脈絡。"
        }},
        {{
            "subtitle": "第二個段落標題",
            "content": "繼續展開另一個重要觀點..."
        }}
    ],
    "insights": [
        "【看點】觀點描述 → 這代表什麼？為什麼重要？可以如何應用？",
        "【延伸思考】提出一個值得深思的問題或框架"
    ],
    "data_highlights": [
        "數據 → 意義說明"
    ],
    "quotes": [
        {{"time": "12:30", "text": "值得記住的原話"}},
        {{"time": "45:00", "text": "另一句金句"}}
    ],
    "timestamps": [
        {{"time": "00:00", "topic": "開場主題"}},
        {{"time": "05:30", "topic": "討論重點"}}
    ]
}}
```

注意：
- 使用繁體中文
- article 的每個段落要有實質內容（150-250字），不是摘要式的幾句話
- insights 要有深度，展現商業分析師的洞察力
- 重點是讓沒看過影片的人也能快速吸收精華
- 保留對談的洞察深度，不要流於表面描述
- 只回覆 JSON，不要其他文字"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # 解析回應
        response_text = message.content[0].text

        try:
            # 找到 JSON 部分
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            json_str = response_text[start:end]
            result = json.loads(json_str)

            # 確保向後兼容（V1 格式）
            if 'points' not in result:
                result['points'] = []
            if 'timestamps' not in result:
                result['timestamps'] = []

            return result
        except Exception as e:
            print(f"[Summarizer] JSON 解析失敗: {e}")
            # 如果解析失敗，返回基本格式
            return {
                "one_liner": "",
                "points": [response_text],
                "data_highlights": [],
                "quotes": [],
                "chapters": [],
                "timestamps": []
            }

    def _format_segments(self, segments: list) -> str:
        """格式化段落（含時間軸）- 智慧取樣確保涵蓋全片"""
        if not segments:
            return ""

        max_chars = 100000  # 約 25000 tokens
        total_segments = len(segments)

        # 計算全部內容的長度
        all_lines = []
        for seg in segments:
            time = self._format_time(seg["start"])
            all_lines.append(f"[{time}] {seg['text']}")

        total_content = "\n".join(all_lines)

        # 如果內容不超過限制，直接返回全部
        if len(total_content) <= max_chars:
            return total_content

        # 內容過長：採用分段取樣策略
        # 將影片分成 5 個區段，每區段取一定比例
        formatted = []
        chars_per_section = max_chars // 5  # 每區段約 20000 字元

        section_size = total_segments // 5
        sections = [
            (0, section_size, "【開場】"),
            (section_size, section_size * 2, "【前段】"),
            (section_size * 2, section_size * 3, "【中段】"),
            (section_size * 3, section_size * 4, "【後段】"),
            (section_size * 4, total_segments, "【結尾】"),
        ]

        for start_idx, end_idx, label in sections:
            section_chars = 0
            formatted.append(f"\n{label}")

            for i in range(start_idx, end_idx):
                if i >= len(segments):
                    break
                seg = segments[i]
                time = self._format_time(seg["start"])
                line = f"[{time}] {seg['text']}"

                if section_chars + len(line) > chars_per_section:
                    formatted.append("...")
                    break

                formatted.append(line)
                section_chars += len(line)

        return "\n".join(formatted)

    def _format_time(self, seconds: float) -> str:
        """格式化時間"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
