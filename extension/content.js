// ---------------------------------------------------------------------------
// SRT Translator — YouTube Content Script
// ---------------------------------------------------------------------------
// 只在 youtube.com/watch 页面运行。
// 不读取字幕内容、不注入 DOM 覆盖。
// 提供：视频标题、URL、可用字幕语言列表。

console.log("[SRT Translator] content script loaded — " + window.location.href);

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_VIDEO_INFO") {
    const title = (document.title || "").replace(/\s*-\s*YouTube\s*$/, "").trim();
    sendResponse({
      url: window.location.href,
      title: title || document.title,
    });
  }

  if (message.type === "GET_CAPTIONS") {
    detectCaptionsWithRetry().then(sendResponse);
    return true; // 保持通道开放，等待异步返回
  }
});

// ---------------------------------------------------------------------------
// 带重试的字幕检测
// ---------------------------------------------------------------------------

async function detectCaptionsWithRetry(maxRetries = 10, delayMs = 500) {
  for (let i = 0; i < maxRetries; i++) {
    console.log(`[SRT Translator] capture attempt ${i + 1}/${maxRetries}`);

    const result = await tryExtractCaptions();
    if (result.found) {
      console.log(`[SRT Translator] captions found: ${result.languages.length} languages`);
      return result;
    }
    if (result.status === "not_found") {
      // 确定没有字幕，不需要重试
      console.log("[SRT Translator] no captions available for this video");
      return result;
    }

    // detection_failed — 等待页面加载，稍后重试
    if (i < maxRetries - 1) {
      await sleep(delayMs);
    }
  }

  console.log("[SRT Translator] detection failed after all retries");
  return { found: false, status: "detection_failed", languages: [] };
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// ---------------------------------------------------------------------------
// 提取逻辑
// ---------------------------------------------------------------------------

async function tryExtractCaptions() {
  // 方法 1：注入脚本到页面主世界读取 ytInitialPlayerResponse
  const fromMainWorld = await readFromMainWorld();
  if (fromMainWorld) {
    const tracks = tryGet(
      () => fromMainWorld.captions.playerCaptionsTracklistRenderer.captionTracks
    );
    if (tracks && tracks.length > 0) {
      console.log("[SRT Translator] source: main-world injection");
      return buildResult(tracks);
    }
    // 有 ytInitialPlayerResponse 但没有 captionTracks → 确定无字幕
    if (tracks !== undefined && tracks !== null && tracks.length === 0) {
      console.log("[SRT Translator] source: main-world — captions empty");
      return { found: false, status: "not_found", languages: [] };
    }
  }

  // 方法 2：从 <script> 标签文本中解析 ytInitialPlayerResponse JSON
  const fromScripts = extractFromScriptTags();
  if (fromScripts) {
    const tracks = tryGet(
      () => fromScripts.captions.playerCaptionsTracklistRenderer.captionTracks
    );
    if (tracks && tracks.length > 0) {
      console.log("[SRT Translator] source: script-tag JSON parse");
      return buildResult(tracks);
    }
  }

  // 方法 3：从 <script> 中直接搜索 captionTracks 附近的 JSON 片段
  const rawTracks = extractCaptionTracksFromRawScript();
  if (rawTracks && rawTracks.length > 0) {
    console.log("[SRT Translator] source: raw captionTracks search");
    return buildResult(rawTracks);
  }

  console.log("[SRT Translator] all methods returned nothing");
  return { found: false, status: "detection_failed", languages: [] };
}

// ---------------------------------------------------------------------------
// 方法 1：注入主世界脚本
// ---------------------------------------------------------------------------

function readFromMainWorld() {
  return new Promise((resolve) => {
    const channel = "srt-yt-" + Math.random().toString(36).slice(2);

    const handler = (e) => {
      if (e.data && e.data.__srtChannel === channel) {
        window.removeEventListener("message", handler);
        resolve(e.data.payload || null);
      }
    };
    window.addEventListener("message", handler);

    const script = document.createElement("script");
    script.textContent = `
      (function() {
        var data = null;
        try { data = window.ytInitialPlayerResponse; } catch(e) {}
        window.postMessage({ __srtChannel: "${channel}", payload: data }, "*");
      })();
    `;
    (document.head || document.documentElement).appendChild(script);
    script.remove();

    // 超时保护
    setTimeout(() => {
      window.removeEventListener("message", handler);
      resolve(null);
    }, 2000);
  });
}

// ---------------------------------------------------------------------------
// 方法 2：从 script 标签文本中提取 JSON（花括号计数）
// ---------------------------------------------------------------------------

function extractFromScriptTags() {
  const scripts = document.querySelectorAll("script:not([src])");
  for (const s of scripts) {
    const text = s.textContent || "";
    const idx = text.indexOf("ytInitialPlayerResponse");
    if (idx === -1) continue;

    const json = extractBalancedJSON(text, idx);
    if (json) {
      try {
        return JSON.parse(json);
      } catch {
        console.log("[SRT Translator] script JSON parse failed, retrying");
        continue;
      }
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// 方法 3：直接搜 captionTracks 附近 JSON 数组
// ---------------------------------------------------------------------------

function extractCaptionTracksFromRawScript() {
  const scripts = document.querySelectorAll("script:not([src])");
  for (const s of scripts) {
    const text = s.textContent || "";

    // 找 "captionTracks" 关键字附近的 JSON 数组 [...]
    const idx = text.indexOf('"captionTracks"');
    if (idx === -1) continue;

    // 跳过 "captionTracks": 后面的冒号和空白
    const afterKey = text.slice(idx + 15);
    const arrStart = afterKey.indexOf("[");
    if (arrStart === -1 || arrStart > 200) continue;

    const arrJSON = extractBalancedArray(afterKey, arrStart);
    if (arrJSON) {
      try {
        return JSON.parse(arrJSON);
      } catch {
        continue;
      }
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// JSON 提取工具：花括号 / 方括号计数
// ---------------------------------------------------------------------------

function extractBalancedJSON(text, searchFrom) {
  // 找到 searchFrom 之后的第一个 '{'
  const start = text.indexOf("{", searchFrom);
  if (start === -1) return null;

  let depth = 0;
  let inString = false;
  let escaped = false;

  for (let i = start; i < text.length; i++) {
    const ch = text[i];
    if (escaped) { escaped = false; continue; }
    if (ch === "\\") { escaped = true; continue; }
    if (ch === '"')  { inString = !inString; continue; }
    if (inString) continue;
    if (ch === "{") depth++;
    if (ch === "}") {
      depth--;
      if (depth === 0) return text.slice(start, i + 1);
    }
  }
  return null;
}

function extractBalancedArray(text, searchFrom) {
  const start = searchFrom; // 已经指向 '['
  let depth = 0;
  let inString = false;
  let escaped = false;

  for (let i = start; i < text.length; i++) {
    const ch = text[i];
    if (escaped) { escaped = false; continue; }
    if (ch === "\\") { escaped = true; continue; }
    if (ch === '"')  { inString = !inString; continue; }
    if (inString) continue;
    if (ch === "[") depth++;
    if (ch === "]") {
      depth--;
      if (depth === 0) return text.slice(start, i + 1);
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// 工具
// ---------------------------------------------------------------------------

function tryGet(fn) {
  try { return fn(); } catch { return null; }
}

function buildResult(tracks) {
  const languages = tracks.map((t) => ({
    languageCode: t.languageCode || "",
    name: (t.name && t.name.simpleText) || t.languageCode || "unknown",
    kind: t.kind || "manual",
    hasBaseUrl: !!t.baseUrl,
  }));

  return { found: true, status: "found", languages };
}
