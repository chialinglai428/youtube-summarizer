/**
 * Podcast 摘要工具 - Frontend Application
 */

// 自動判斷 API 網址：本機開發用 localhost，正式環境用 Render
const API_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:5001/api'
    : 'https://youtube-summarizer-api.onrender.com/api';

// DOM 元素
const elements = {
    urlInput: document.getElementById('podcast-url'),
    submitBtn: document.getElementById('submit-btn'),
    loadingSection: document.getElementById('loading-section'),
    loadingText: document.getElementById('loading-text'),
    resultSection: document.getElementById('result-section'),
    errorSection: document.getElementById('error-section'),
    errorMessage: document.getElementById('error-message'),
    podcastTitle: document.getElementById('podcast-title'),
    podcastDuration: document.getElementById('podcast-duration'),
    sourceBadge: document.getElementById('source-badge'),
    timestamps: document.getElementById('timestamps'),
    // V3 精華內容版
    oneLinerCard: document.getElementById('one-liner-card'),
    oneLiner: document.getElementById('one-liner'),
    articleCard: document.getElementById('article-card'),
    article: document.getElementById('article'),
    insightsCard: document.getElementById('insights-card'),
    insights: document.getElementById('insights'),
    dataHighlightsCard: document.getElementById('data-highlights-card'),
    dataHighlights: document.getElementById('data-highlights'),
    quotesCard: document.getElementById('quotes-card'),
    quotes: document.getElementById('quotes'),
    copyBtn: document.getElementById('copy-btn'),
    newBtn: document.getElementById('new-btn'),
    retryBtn: document.getElementById('retry-btn'),
    steps: {
        download: document.getElementById('step-download'),
        summarize: document.getElementById('step-summarize')
    }
};

// 狀態
let currentResult = null;

// 初始化
function init() {
    elements.submitBtn.addEventListener('click', handleSubmit);
    elements.urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSubmit();
    });
    elements.copyBtn.addEventListener('click', handleCopy);
    elements.newBtn.addEventListener('click', handleNew);
    elements.retryBtn.addEventListener('click', handleSubmit);
}

// 提交處理
async function handleSubmit() {
    const url = elements.urlInput.value.trim();

    if (!url) {
        showError('請輸入 YouTube 連結');
        return;
    }

    if (!isValidUrl(url)) {
        showError('請輸入有效的 YouTube 連結');
        return;
    }

    // 顯示載入狀態
    showLoading();

    try {
        // 進度更新
        updateStep('download', 'active');

        const response = await fetch(`${API_URL}/summarize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url })
        });

        updateStep('download', 'completed');
        updateStep('summarize', 'active');

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || '處理失敗');
        }

        updateStep('summarize', 'completed');

        // 顯示結果
        currentResult = data;
        showResult(data);

    } catch (error) {
        showError(error.message);
    }
}

// 驗證 URL
function isValidUrl(url) {
    const youtubePattern = /(youtube\.com|youtu\.be)\//;
    return youtubePattern.test(url);
}

// 顯示載入狀態
function showLoading() {
    elements.loadingSection.hidden = false;
    elements.resultSection.hidden = true;
    elements.errorSection.hidden = true;
    elements.submitBtn.disabled = true;

    // 重置步驟狀態
    Object.values(elements.steps).forEach(step => {
        if (step) step.classList.remove('active', 'completed');
    });
}

// 更新步驟狀態
function updateStep(step, status) {
    const stepElement = elements.steps[step];
    if (stepElement) {
        stepElement.classList.remove('active', 'completed');
        stepElement.classList.add(status);
    }

    const texts = {
        download: '正在取得字幕...',
        summarize: '正在生成精華文章...'
    };

    if (status === 'active') {
        elements.loadingText.textContent = texts[step];
    }
}

// 顯示結果
function showResult(data) {
    elements.loadingSection.hidden = true;
    elements.resultSection.hidden = false;
    elements.errorSection.hidden = true;
    elements.submitBtn.disabled = false;

    // 標題與來源
    elements.podcastTitle.textContent = data.title;
    elements.podcastDuration.textContent = data.duration || '';

    // 來源標籤
    if (data.source === 'subtitles') {
        elements.sourceBadge.textContent = '字幕模式';
        elements.sourceBadge.className = 'source-badge';
    } else {
        elements.sourceBadge.textContent = 'Whisper 轉錄';
        elements.sourceBadge.className = 'source-badge whisper';
    }

    // 一句話總結
    if (data.one_liner) {
        elements.oneLiner.textContent = data.one_liner;
        elements.oneLinerCard.hidden = false;
    } else {
        elements.oneLinerCard.hidden = true;
    }

    // V3: 精華內容
    if (data.article && data.article.length > 0) {
        elements.article.innerHTML = data.article
            .map(section => `
                <div class="article-section">
                    <h4 class="article-subtitle">${escapeHtml(section.subtitle || '')}</h4>
                    <p class="article-text">${escapeHtml(section.content || '')}</p>
                </div>
            `)
            .join('');
        elements.articleCard.hidden = false;
    } else {
        elements.articleCard.hidden = true;
    }

    // 商業分析師觀點
    if (data.insights && data.insights.length > 0) {
        elements.insights.innerHTML = data.insights
            .map(insight => `
                <div class="insight-item">
                    <p>${escapeHtml(insight)}</p>
                </div>
            `)
            .join('');
        elements.insightsCard.hidden = false;
    } else {
        elements.insightsCard.hidden = true;
    }

    // 數據亮點
    if (data.data_highlights && data.data_highlights.length > 0) {
        elements.dataHighlights.innerHTML = data.data_highlights
            .map(d => `<li>${escapeHtml(d)}</li>`)
            .join('');
        elements.dataHighlightsCard.hidden = false;
    } else {
        elements.dataHighlightsCard.hidden = true;
    }

    // 金句摘錄
    if (data.quotes && data.quotes.length > 0) {
        elements.quotes.innerHTML = data.quotes
            .map(q => `
                <div class="quote-item">
                    <p class="quote-text">${escapeHtml(q.text || q)}</p>
                    ${q.time ? `<p class="quote-time">${escapeHtml(q.time)}</p>` : ''}
                </div>
            `)
            .join('');
        elements.quotesCard.hidden = false;
    } else {
        elements.quotesCard.hidden = true;
    }

    // 時間導航
    elements.timestamps.innerHTML = (data.timestamps || [])
        .map(ts => `
            <div class="timestamp-item">
                <span class="timestamp-time">${escapeHtml(ts.time || '')}</span>
                <span class="timestamp-topic">${escapeHtml(ts.topic || '')}</span>
            </div>
        `)
        .join('');
}

// 顯示錯誤
function showError(message) {
    elements.loadingSection.hidden = true;
    elements.resultSection.hidden = true;
    elements.errorSection.hidden = false;
    elements.submitBtn.disabled = false;
    elements.errorMessage.textContent = message;
}

// 複製摘要
async function handleCopy() {
    if (!currentResult) return;

    const sections = [
        `📺 ${currentResult.title}`,
        currentResult.duration ? `⏱️ ${currentResult.duration}` : '',
        ''
    ];

    // 一句話總結
    if (currentResult.one_liner) {
        sections.push(`💡 ${currentResult.one_liner}`, '');
    }

    // 精華內容
    if (currentResult.article && currentResult.article.length > 0) {
        sections.push('📖 精華內容', '');
        currentResult.article.forEach(section => {
            sections.push(`【${section.subtitle || ''}】`);
            sections.push(section.content || '');
            sections.push('');
        });
    }

    // 看點與延伸思考
    if (currentResult.insights && currentResult.insights.length > 0) {
        sections.push('💡 看點與延伸思考：');
        currentResult.insights.forEach(insight => sections.push(`• ${insight}`));
        sections.push('');
    }

    // 數據亮點
    if (currentResult.data_highlights && currentResult.data_highlights.length > 0) {
        sections.push('📊 數據亮點：');
        currentResult.data_highlights.forEach(d => sections.push(`• ${d}`));
        sections.push('');
    }

    // 金句摘錄
    if (currentResult.quotes && currentResult.quotes.length > 0) {
        sections.push('💬 金句摘錄：');
        currentResult.quotes.forEach(q => {
            const text = q.text || q;
            const time = q.time ? ` (${q.time})` : '';
            sections.push(`"${text}"${time}`);
        });
        sections.push('');
    }

    // 時間導航
    if (currentResult.timestamps && currentResult.timestamps.length > 0) {
        sections.push('⏱️ 時間導航：');
        currentResult.timestamps.forEach(t => sections.push(`[${t.time}] ${t.topic}`));
    }

    const text = sections.filter(s => s !== undefined).join('\n');

    try {
        await navigator.clipboard.writeText(text);
        elements.copyBtn.textContent = '已複製！';
        setTimeout(() => {
            elements.copyBtn.textContent = '複製摘要';
        }, 2000);
    } catch (err) {
        alert('複製失敗，請手動複製');
    }
}

// 分析新節目
function handleNew() {
    elements.urlInput.value = '';
    elements.resultSection.hidden = true;
    elements.urlInput.focus();
    currentResult = null;
}

// 工具函數
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// 啟動
init();
