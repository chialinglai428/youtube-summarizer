# 🎙️ Spotify Podcast 摘要工具

自動擷取 Spotify Podcast 內容，生成重點摘要與關鍵時間軸。

## 功能特色

- 📥 貼上 Spotify Podcast 連結即可使用
- 🎯 自動生成重點條列摘要
- ⏱️ 標註關鍵時間軸
- 📋 一鍵複製摘要內容

## 技術架構

```
spotify-podcast-summarizer/
├── backend/                 # Python Flask 後端
│   ├── app.py              # API 主程式
│   ├── requirements.txt    # Python 依賴
│   ├── .env.example        # 環境變數範例
│   └── services/
│       ├── spotify.py      # Spotify 下載服務
│       ├── transcriber.py  # 語音轉文字 (Whisper)
│       └── summarizer.py   # AI 摘要 (Claude)
│
└── frontend/               # 網頁前端
    ├── index.html
    ├── css/style.css
    └── js/app.js
```

## 安裝步驟

### 1. 後端設定

```bash
cd backend

# 建立虛擬環境
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入 API Key
```

### 2. 設定 API Key

編輯 `backend/.env`：

```
ANTHROPIC_API_KEY=your_api_key_here
```

### 3. 啟動服務

```bash
# 啟動後端 (在 backend 目錄)
python app.py

# 開啟前端
# 用瀏覽器開啟 frontend/index.html
# 或使用 Live Server
```

## 使用方式

1. 開啟網頁
2. 貼上 Spotify Podcast 連結
3. 點擊「生成摘要」
4. 等待處理完成
5. 查看摘要與時間軸

## 注意事項

- 首次執行會下載 Whisper 模型，需要一些時間
- 較長的 Podcast 處理時間較久
- 需要穩定的網路連線

## 授權

MIT License
