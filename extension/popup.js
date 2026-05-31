// ---------------------------------------------------------------------------
// SRT Translator — Chrome Extension Popup
// ---------------------------------------------------------------------------

const API_URL = "http://localhost:8000/translate-srt";

const fileInput  = document.getElementById("file-input");
const fileLabel  = document.getElementById("file-label");
const btnTrans   = document.getElementById("btn-translate");
const btnDl      = document.getElementById("btn-download");
const statusEl   = document.getElementById("status");

let selectedFile = null;
let translated   = null;   // { output_filename, translated_content }

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

function downloadBlob(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function resetState() {
  translated = null;
  btnDl.disabled = true;
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (!file) return;

  selectedFile = file;
  fileLabel.textContent = file.name;
  fileLabel.classList.add("has-file");
  btnTrans.disabled = false;
  setStatus(`Ready: ${file.name}`, "status-idle");
  resetState();
});

btnTrans.addEventListener("click", async () => {
  if (!selectedFile) return;

  btnTrans.disabled = true;
  setStatus("Translating…", "status-loading");
  resetState();

  try {
    // 1. Read file
    let content;
    try {
      content = await readFile(selectedFile);
    } catch {
      setStatus("Failed to read file. Please try again.", "status-error");
      btnTrans.disabled = false;
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
        "Cannot reach local server.\nPlease start the local server first:\npython server/main.py",
        "status-error"
      );
      btnTrans.disabled = false;
      return;
    }

    // 3. Parse response
    if (!resp.ok) {
      const detail = (await resp.json().catch(() => ({}))).detail || `HTTP ${resp.status}`;
      setStatus(`Translation failed: ${detail}`, "status-error");
      btnTrans.disabled = false;
      return;
    }

    const data = await resp.json();
    translated = data;

    setStatus(
      `Done — ${selectedFile.name} → ${data.output_filename}`,
      "status-success"
    );
    btnDl.disabled = false;

  } catch (e) {
    setStatus(`Unexpected error: ${e.message}`, "status-error");
  } finally {
    btnTrans.disabled = false;
  }
});

btnDl.addEventListener("click", () => {
  if (!translated) return;
  downloadBlob(translated.output_filename, translated.translated_content);
  setStatus(`Downloaded: ${translated.output_filename}`, "status-success");
});
