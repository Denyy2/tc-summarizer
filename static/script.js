const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".panel");
const textInput = document.getElementById("text-input");
const fileInput = document.getElementById("file-input");
const fileLabel = document.getElementById("file-label");
const submitBtn = document.getElementById("submit-btn");
const errorEl = document.getElementById("error");
const resultEl = document.getElementById("result");
const resultMeta = document.getElementById("result-meta");
const resultBody = document.getElementById("result-body");
const samplesEl = document.getElementById("samples");

let mode = "paste";

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    mode = tab.dataset.mode;
    tabs.forEach((t) => t.classList.toggle("active", t === tab));
    panels.forEach((p) => p.classList.toggle("hidden", p.dataset.panel !== mode));
    hideError();
  });
});

fileInput.addEventListener("change", () => {
  fileLabel.textContent = fileInput.files[0]?.name || "Choose a PDF, PNG, or JPEG";
});

function hideError() {
  errorEl.classList.add("hidden");
  errorEl.textContent = "";
}

function showError(message) {
  errorEl.textContent = message;
  errorEl.classList.remove("hidden");
}

async function loadSamples() {
  try {
    const res = await fetch("/api/samples");
    const items = await res.json();
    items.forEach((item, i) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = `Try sample ${i + 1}`;
      btn.addEventListener("click", () => {
        textInput.value = item.text;
      });
      samplesEl.appendChild(btn);
    });
  } catch {
    // Samples are a nice-to-have; failing silently is fine here.
  }
}
loadSamples();

submitBtn.addEventListener("click", async () => {
  hideError();
  resultEl.classList.add("hidden");

  const formData = new FormData();
  if (mode === "upload") {
    const file = fileInput.files[0];
    if (!file) return showError("Choose a file first.");
    formData.append("file", file);
  } else {
    const text = textInput.value.trim();
    if (!text) return showError("Paste some text first.");
    formData.append("text", text);
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Summarizing…";

  try {
    const res = await fetch("/summarize", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) {
      showError(data.error || "Something went wrong.");
      return;
    }

    resultMeta.innerHTML = "";
    if (data.usedOcr) {
      resultMeta.innerHTML += "<span>OCR used</span>";
    }
    resultMeta.innerHTML += `<span>${data.extractedChars.toLocaleString()} chars extracted</span>`;
    resultBody.textContent = data.summary;
    resultEl.classList.remove("hidden");
    resultEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch {
    showError("Network error — is the server running?");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Summarize";
  }
});
