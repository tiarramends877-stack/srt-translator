// ---------------------------------------------------------------------------
// SRT Translator — Chrome Extension Popup
// ---------------------------------------------------------------------------

const API_URL = "http://localhost:8000/translate-srt";

const fileInput  = document.getElementById("file-input");
const fileLabel  = document.getElementById("file-label");
const btnTrans   = document.getElementById("btn-translate");
const btnDl      = document.getElementById("btn-download");
const statusEl   = document.getElementById("status");
const ytInfo     = document.getElementById("yt-info");
const ytTitle    = document.getElementById("yt-title");
const dbgUrl     = document.getElementById("dbg-url");
const dbgIsYt    = document.getElementById("dbg-is-yt");
const dbgTitle   = document.getElementById("dbg-title");
const dbgCapt    = document.getElementById("dbg-captions");
const capBox     = document.getElementById("captions-box");
const capList    = document.getElementById("captions-list");

let selectedFile = null;
let translated   = null;           // { output_filename, translated_content }
let youtubeTitle = null;           // 非空=当前页是YouTube视频

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setStatus(text, cls) {
  statusEl.textContent = text;
  statusEl.className   = cls;
}

function readFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload  = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.readAsText(file, "UTF-8");
  });
}

/** 将视频标题转为安全文件名：保留中文、英文、数字、空格、连字符、下划线 */
function safeFilename(title) {
  return title
    .replace(/[^\w一-鿿 \-]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 120);
}

function downloadBlob(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function setLoading(loading) {
  btnTrans.disabled = loading;
  btnTrans.textContent = loading ? "Translating…" : "Translate";
  if (loading) {
    btnTrans.classList.add("loading");
  } else {
    btnTrans.classList.remove("loading");
  }
}

/** 返回本次下载应使用的文件名 */
function downloadFilename() {
  if (youtubeTitle) {
    return safeFilename(youtubeTitle) + ".zh.srt";
  }
  return translated ? translated.output_filename : "output.zh.srt";
}

/** 清除 " - YouTube" 后缀，返回干净的标题 */
function cleanTitle(raw) {
  return (raw || "").replace(/\s*-\s*YouTube\s*$/i, "").trim();
}

/** 渲染字幕语言列表 */
function renderCaptions(data) {
  if (!data || data.status === "detection_failed") {
    dbgCapt.textContent = "detection failed";
    capList.innerHTML = "Could not detect captions. Try refreshing the YouTube page.";
    capBox.classList.add("visible");
    return;
  }
  if (data.status === "not_found" || !data.languages || data.languages.length === 0) {
    dbgCapt.textContent = "none";
    capList.innerHTML = "No captions found for this video.";
    capBox.classList.add("visible");
    return;
  }
  dbgCapt.textContent = `yes (${data.languages.length})`;

  let html = "<ul>";
  for (const lang of data.languages) {
    const tag = lang.kind === "asr"
      ? '<span class="tag tag-asr">auto</span>'
      : (lang.kind !== "manual" ? `<span class="tag tag-manual">${lang.kind}</span>` : "");
    html += `<li>${lang.name} (${lang.languageCode})${tag}</li>`;
  }
  html += "</ul>";
  capList.innerHTML = html;
  capBox.classList.add("visible");
}

// ---------------------------------------------------------------------------
// YouTube 检测（popup 打开时）
// ---------------------------------------------------------------------------

(async function detectYouTube() {
  dbgUrl.textContent   = "…";
  dbgIsYt.textContent  = "…";
  dbgTitle.textContent = "…";
  dbgCapt.textContent  = "…";

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url) {
      dbgUrl.textContent = "(no tab)";
      return;
    }

    dbgUrl.textContent = tab.url;

    // 解析 URL，检查是否是 YouTube 视频页
    const url = new URL(tab.url);
    const isYouTube = (
      url.hostname === "www.youtube.com" ||
      url.hostname === "youtube.com" ||
      url.hostname === "m.youtube.com"
    ) && url.pathname.startsWith("/watch");

    dbgIsYt.textContent = isYouTube ? "yes" : "no";

    if (!isYouTube) return; // 非 YouTube，什么都不做

    // ---- 获取视频标题 ----
    // 方案 A：直接用 tab.title（不需要 content script）
    if (tab.title) {
      youtubeTitle = cleanTitle(tab.title);
      dbgTitle.textContent = youtubeTitle || "(empty after clean)";
      ytTitle.textContent = youtubeTitle;
      ytInfo.classList.add("visible");
      if (!selectedFile) {
        setStatus("YouTube: " + youtubeTitle, "status-idle");
      }
    } else {
      // 方案 B：fallback 到 content script
      dbgTitle.textContent = "(tab.title empty, trying content script)";
      try {
        const info = await chrome.tabs.sendMessage(tab.id, { type: "GET_VIDEO_INFO" });
        if (info && info.title) {
          youtubeTitle = cleanTitle(info.title);
          dbgTitle.textContent = youtubeTitle || "(empty after clean)";
          ytTitle.textContent = youtubeTitle;
          ytInfo.classList.add("visible");
          setStatus("YouTube: " + youtubeTitle, "status-idle");
        }
      } catch {
        dbgTitle.textContent = "(content script unavailable)";
      }
    }

    // ---- 获取字幕语言列表 ----
    try {
      const captions = await chrome.tabs.sendMessage(tab.id, { type: "GET_CAPTIONS" });
      renderCaptions(captions);
    } catch {
      dbgCapt.textContent = "detection failed";
      capList.innerHTML = "Could not detect captions. Try refreshing the YouTube page.";
      capBox.classList.add("visible");
    }

  } catch (err) {
    dbgUrl.textContent = "error: " + err.message;
    console.debug("SRT Translator: tab query failed", err);
  }
})();

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (!file) return;

  selectedFile = file;
  fileLabel.textContent = "📄 " + file.name;
  fileLabel.classList.add("has-file");
  btnTrans.disabled = false;
  btnDl.disabled = true;
  translated = null;
  setStatus("Ready to translate: " + file.name, "status-idle");
});

btnTrans.addEventListener("click", async () => {
  if (!selectedFile) {
    setStatus("Please choose a .srt file first", "status-error");
    return;
  }

  setLoading(true);
  setStatus("Translating…", "status-loading");
  translated = null;
  btnDl.disabled = true;

  try {
    // 1. Read file
    let content;
    try {
      content = await readFile(selectedFile);
    } catch {
      setStatus("Failed to read file. Please try again.", "status-error");
      return;
    }

    // 2. Call API
    let resp;
    try {
      resp = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: selectedFile.name,
          content: content,
        }),
      });
    } catch {
      setStatus(
        "Please start the local server first:\npython server/main.py\n→ http://localhost:8000",
        "status-error"
      );
      return;
    }

    // 3. Parse response
    if (!resp.ok) {
      const detail = (await resp.json().catch(() => ({}))).detail || `HTTP ${resp.status}`;
      setStatus(`Translation failed: ${detail}`, "status-error");
      return;
    }

    const data = await resp.json();
    translated = data;

    const outName = downloadFilename();
    setStatus(
      "Done — " + outName,
      "status-success"
    );
    btnDl.disabled = false;

  } catch (e) {
    setStatus(`Unexpected error: ${e.message}`, "status-error");
  } finally {
    setLoading(false);
  }
});

btnDl.addEventListener("click", () => {
  if (!translated) return;
  const outName = downloadFilename();
  downloadBlob(outName, translated.translated_content);
  setStatus("Downloaded: " + outName, "status-success");
});
