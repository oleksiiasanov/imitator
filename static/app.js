const form = document.getElementById("uploadForm");
const fileInput = document.getElementById("videoInput");
const uploadButton = document.getElementById("uploadButton");
const toggleButton = document.getElementById("toggleButton");
const uploadProgressBlock = document.getElementById("uploadProgressBlock");
const conversionProgressBlock = document.getElementById("conversionProgressBlock");
const uploadProgressBar = document.getElementById("uploadProgressBar");
const conversionProgressBar = document.getElementById("conversionProgressBar");
const uploadPercent = document.getElementById("uploadPercent");
const conversionPercent = document.getElementById("conversionPercent");
const messageBox = document.getElementById("messageBox");

const maxUploadBytes = 4 * 1024 * 1024 * 1024;
const allowedExtensions = [".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".ts", ".webm"];
let statusTimer = null;

function showMessage(text, type) {
  messageBox.style.display = "block";
  messageBox.className = "message " + type;
  messageBox.textContent = text;
}

function setProgress(bar, label, percent) {
  const safePercent = Math.max(0, Math.min(100, Number(percent) || 0));
  bar.style.width = safePercent + "%";
  label.textContent = safePercent + "%";
}

function setBusy(isBusy) {
  uploadButton.disabled = isBusy;
  fileInput.disabled = isBusy;
  if (toggleButton) {
    toggleButton.disabled = isBusy;
  }
}

function fileExtension(filename) {
  const dot = filename.lastIndexOf(".");
  return dot >= 0 ? filename.slice(dot).toLowerCase() : "";
}

function validateFile(file) {
  if (!file) {
    return "Оберіть відеофайл";
  }

  const extension = fileExtension(file.name);
  if (!allowedExtensions.includes(extension)) {
    return "Непідтримуваний формат файлу. Дозволено: " + allowedExtensions.join(", ");
  }

  if (file.size <= 0) {
    return "Файл порожній";
  }

  if (file.size > maxUploadBytes) {
    return "Файл завеликий. Максимум: 4 GB";
  }

  return "";
}

function resetProgress() {
  uploadProgressBlock.style.display = "none";
  conversionProgressBlock.style.display = "none";
  setProgress(uploadProgressBar, uploadPercent, 0);
  setProgress(conversionProgressBar, conversionPercent, 0);
}

function stopPolling() {
  if (statusTimer) {
    clearTimeout(statusTimer);
    statusTimer = null;
  }
}

function pollConversionStatus() {
  fetch("/upload-status", { cache: "no-store" })
    .then(response => response.json())
    .then(status => {
      conversionProgressBlock.style.display = "block";
      setProgress(conversionProgressBar, conversionPercent, status.percent || 0);

      if (status.phase === "error") {
        stopPolling();
        setBusy(false);
        showMessage("Помилка конвертації:\n" + (status.error || status.message || "Невідома помилка"), "err");
        return;
      }

      if (status.phase === "complete") {
        stopPolling();
        setProgress(conversionProgressBar, conversionPercent, 100);
        showMessage(status.message || "Готово. Відео завантажено, конвертовано і запущено.", "ok");
        setTimeout(() => window.location.reload(), 1000);
        return;
      }

      if (status.running) {
        showMessage(status.message || "Конвертація триває...", "ok");
        statusTimer = setTimeout(pollConversionStatus, 1000);
        return;
      }

      setBusy(false);
    })
    .catch(() => {
      showMessage("Не можу отримати статус конвертації", "err");
      statusTimer = setTimeout(pollConversionStatus, 2000);
    });
}

if (window.initialConversionRunning) {
  setBusy(true);
  conversionProgressBlock.style.display = "block";
  pollConversionStatus();
} else {
  resetProgress();
}

form.addEventListener("submit", function(e) {
  e.preventDefault();
  stopPolling();

  const file = fileInput.files[0];
  const validationError = validateFile(file);
  if (validationError) {
    resetProgress();
    showMessage(validationError, "err");
    return;
  }

  const formData = new FormData(form);
  const xhr = new XMLHttpRequest();

  setBusy(true);
  uploadProgressBlock.style.display = "block";
  conversionProgressBlock.style.display = "none";
  setProgress(uploadProgressBar, uploadPercent, 0);
  setProgress(conversionProgressBar, conversionPercent, 0);
  showMessage("Завантаження почалось...", "ok");

  xhr.upload.addEventListener("progress", function(e) {
    if (e.lengthComputable) {
      const percent = Math.round((e.loaded / e.total) * 100);
      setProgress(uploadProgressBar, uploadPercent, percent);

      if (percent >= 100) {
        showMessage("Файл завантажено. Очікую старт конвертації...", "ok");
      }
    }
  });

  xhr.onload = function() {
    let response = {};

    try {
      response = JSON.parse(xhr.responseText);
    } catch (e) {
      response = { ok: false, error: xhr.responseText };
    }

    if (xhr.status >= 200 && xhr.status < 300 && response.ok) {
      setProgress(uploadProgressBar, uploadPercent, 100);
      conversionProgressBlock.style.display = "block";
      showMessage(response.message || "Файл завантажено. Конвертація почалась...", "ok");
      pollConversionStatus();
    } else {
      setBusy(false);
      showMessage("Помилка:\n" + (response.error || "Невідома помилка"), "err");
    }
  };

  xhr.onerror = function() {
    setBusy(false);
    showMessage("Помилка мережі під час завантаження", "err");
  };

  xhr.open("POST", "/upload");
  xhr.send(formData);
});
