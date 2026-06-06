// ---------------------------------------------------------------------------
// SRT Translator — Chrome Extension Popup (v0.5.0)
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
const btnDlSrt   = document.getElementById("btn-dl-srt");

let selectedFile  = null;
let translated    = null;         // { output_filename, translated_content }
let youtubeTitle  = null;         // 非空=当前页是YouTube视频
let captionTracks = [];           // [{ languageCode, name, kind, baseUrl }]

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

function downloadFilename() {
  if (youtubeTitle) {
    return safeFilename(youtubeTitle) + ".zh.srt";
  }
  return translated ? translated.output_filename : "output.zh.srt";
}

function cleanTitle(raw) {
  return (raw || "").replace(/\s*-\s*YouTube\s*$/i, "").trim();
}

// ---------------------------------------------------------------------------
// Captions UI
// ---------------------------------------------------------------------------

function renderCaptions(data) {
  captionTracks = [];
  btnDlSrt.disabled = true;

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
  captionTracks = data.languages;

  // 渲染 radio 列表
  let html = "";
  for (let i = 0; i < captionTracks.length; i++) {
    const lang = captionTracks[i];
    const tag = lang.kind === "asr"
      ? '<span class="tag tag-asr">auto</span>'
      : (lang.kind !== "manual" ? `<span class="tag tag-manual">${lang.kind}</span>` : "");
    html += `<label class="track-row">`
      + `<input type="radio" name="track" value="${i}">`
      + `${lang.name} (${lang.languageCode})${tag}`
      + `</label>`;
  }
  capList.innerHTML = html;

  // 选中第一个有 baseUrl 的 track
  for (let i = 0; i < captionTracks.length; i++) {
    if (captionTracks[i].baseUrl) {
      capList.querySelector(`input[value="${i}"]`).checked = true;
      btnDlSrt.disabled = false;
      break;
    }
  }

  // radio 切换时启用/禁用下载按钮
  capList.querySelectorAll("input[type=radio]").forEach((r) => {
    r.addEventListener("change", () => {
      btnDlSrt.disabled = false;
    });
  });

  capBox.classList.add("visible");
}

// ---------------------------------------------------------------------------
// SRT 下载
// ---------------------------------------------------------------------------

btnDlSrt.addEventListener("click", async () => {
  const sel = capList.querySelector("input[name=track]:checked");
  if (!sel) {
    setStatus("Please choose a caption track first.", "status-error");
    return;
  }

  const idx  = parseInt(sel.value);
  const track = captionTracks[idx];
  if (!track || !track.baseUrl) {
    setStatus("This track has no downloadable URL.", "status-error");
    return;
  }

  btnDlSrt.disabled = true;
  setStatus("Downloading captions…", "status-loading");

  try {
    const raw = await fetchCaptions(track.baseUrl);
    const srt = timedtextToSrt(raw);
    if (!srt) {
      throw new Error("empty result");
    }

    const outName = youtubeTitle
      ? safeFilename(youtubeTitle) + "." + (track.languageCode === "en" ? "en" : track.languageCode) + ".srt"
      : "captions." + track.languageCode + ".srt";

    downloadBlob(outName, srt);
    setStatus("Downloaded: " + outName, "status-success");
  } catch (e) {
    console.debug("SRT Translator: caption download failed", e);
    setStatus("Could not download captions for this track.", "status-error");
  } finally {
    btnDlSrt.disabled = false;
  }
});

async function fetchCaptions(baseUrl) {
  // 优先 JSON3
  const json3Url = baseUrl + "&fmt=json3";
  try {
    const resp = await fetch(json3Url);
    if (resp.ok) {
      const text = await resp.text();
      if (text && text.includes('"events"')) return text;
    }
  } catch { /* fall through */ }

  // 回退原始 XML
  const resp = await fetch(baseUrl);
  if (!resp.ok) throw new Error("HTTP " + resp.status);
  return resp.text();
}

// ---------------------------------------------------------------------------
// timedtext → SRT
// ---------------------------------------------------------------------------

function timedtextToSrt(raw) {
  // 尝试 JSON3
  if (raw.includes('"events"')) return json3ToSrt(raw);
  // 否则按 XML
  return xmlToSrt(raw);
}

function json3ToSrt(raw) {
  let data;
  try { data = JSON.parse(raw); } catch { return null; }
  const events = data.events || [];
  if (events.length === 0) return null;

  const lines = [];
  let n = 0;
  for (const ev of events) {
    if (!ev.segs) continue;
    const text = ev.segs.map((s) => s.utf8 || "").join("").trim();
    if (!text) continue;
    n++;
    const startMs = ev.tStartMs || 0;
    const endMs   = startMs + (ev.dDurationMs || 0);
    lines.push(String(n));
    lines.push(msToSrtTime(startMs) + " --> " + msToSrtTime(endMs));
    lines.push(decodeEntities(text));
    lines.push("");
  }
  return n > 0 ? lines.join("\n") : null;
}

function xmlToSrt(raw) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(raw, "text/xml");
  const els = doc.querySelectorAll("text, p");
  if (els.length === 0) return null;

  const lines = [];
  let n = 0;
  for (const el of els) {
    let start = parseFloat(el.getAttribute("t") || el.getAttribute("start") || "0");
    let dur   = parseFloat(el.getAttribute("d") || el.getAttribute("dur") || "0");
    // YouTube timedtext: t/d 单位是毫秒；某些旧格式可能是秒
    if (start < 1000 && dur < 100 && els.length > 1) { start *= 1000; dur *= 1000; }
    const text = (el.textContent || "").trim();
    if (!text) continue;
    n++;
    const sMs = Math.round(start);
    const eMs = Math.round(start + dur);
    lines.push(String(n));
    lines.push(msToSrtTime(sMs) + " --> " + msToSrtTime(eMs));
    lines.push(decodeEntities(text));
    lines.push("");
  }
  return n > 0 ? lines.join("\n") : null;
}

function msToSrtTime(ms) {
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  const mi = Math.floor(ms % 1000);
  return (
    String(h).padStart(2, "0") + ":" +
    String(m).padStart(2, "0") + ":" +
    String(s).padStart(2, "0") + "," +
    String(mi).padStart(3, "0")
  );
}

function decodeEntities(text) {
  return text
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/&apos;/gi, "'")
    .replace(/&#x27;/gi, "'")
    .replace(/&#(\d+);/g, (_, d) => String.fromCharCode(parseInt(d, 10)))
    .replace(/\s*\n\s*/g, "\n")
    .trim();
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

    const url = new URL(tab.url);
    const isYouTube = (
      url.hostname === "www.youtube.com" ||
      url.hostname === "youtube.com" ||
      url.hostname === "m.youtube.com"
    ) && url.pathname.startsWith("/watch");

    dbgIsYt.textContent = isYouTube ? "yes" : "no";

    if (!isYouTube) return;

    // ---- 获取视频标题 ----
    if (tab.title) {
      youtubeTitle = cleanTitle(tab.title);
      dbgTitle.textContent = youtubeTitle || "(empty after clean)";
      ytTitle.textContent = youtubeTitle;
      ytInfo.classList.add("visible");
      if (!selectedFile) {
        setStatus("YouTube: " + youtubeTitle, "status-idle");
      }
    } else {
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
  }
})();

// ---------------------------------------------------------------------------
// 手动上传 .srt → 翻译（保留）
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
    let content;
    try {
      content = await readFile(selectedFile);
    } catch {
      setStatus("Failed to read file. Please try again.", "status-error");
      return;
    }

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

    if (!resp.ok) {
      const detail = (await resp.json().catch(() => ({}))).detail || `HTTP ${resp.status}`;
      setStatus(`Translation failed: ${detail}`, "status-error");
      return;
    }

    const data = await resp.json();
    translated = data;

    const outName = downloadFilename();
    setStatus("Done — " + outName, "status-success");
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
