// ---------------------------------------------------------------------------
// SRT Translator — YouTube Content Script
// ---------------------------------------------------------------------------
// 只在 youtube.com/watch 页面运行，不读取字幕，不注入 DOM。
// 仅提供视频标题和 URL 给 popup。

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_VIDEO_INFO") {
    // 去掉 " - YouTube" 后缀
    const title = (document.title || "").replace(/\s*-\s*YouTube\s*$/, "").trim();
    sendResponse({
      url: window.location.href,
      title: title || document.title,
    });
  }
});
