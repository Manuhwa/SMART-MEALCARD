function initials(student) {
  return `${(student.first_name || " ")[0]}${(student.last_name || " ")[0]}`.toUpperCase();
}

function photoHtml(student) {
  if (student.photo) {
    return `<img src="${student.photo}" alt="${student.full_name}">`;
  }
  return initials(student);
}

function renderQrCodes() {
  if (typeof QRCode === "undefined") return;
  document.querySelectorAll("[data-qr]").forEach((el) => {
    if (el.dataset.ready) return;
    el.innerHTML = "";
    new QRCode(el, {
      text: el.dataset.qr,
      width: 78,
      height: 78,
      colorDark: "#0c3324",
      colorLight: "#ffffff",
      correctLevel: QRCode.CorrectLevel.M,
    });
    el.dataset.ready = "1";
  });
}

function paintResult(box, cls, title, body, student) {
  box.className = `result ${cls}`;
  const photo = student
    ? `<div class="photo">${photoHtml(student)}</div>`
    : `<div class="photo">ID</div>`;
  const extra = student
    ? `<p><strong>${student.full_name}</strong><br>${student.srn}<br>${student.programme}</p>`
    : "";
  box.innerHTML = `${photo}<div><p class="status-word">${title}</p><p>${body}</p>${extra}</div>`;
}

async function postJson(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  return { res, data };
}

function setupCamera(onCode) {
  const reader = document.getElementById("reader");
  const button = document.getElementById("camera-btn");
  if (!reader || !button || typeof Html5Qrcode === "undefined") return;
  let scanner = null;
  button.addEventListener("click", async () => {
    if (scanner) {
      await scanner.stop();
      scanner = null;
      reader.hidden = true;
      button.textContent = "Camera";
      return;
    }
    scanner = new Html5Qrcode("reader");
    reader.hidden = false;
    button.textContent = "Stop camera";
    try {
      await scanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: 220 },
        (text) => onCode(text)
      );
    } catch (err) {
      reader.hidden = true;
      button.textContent = "Camera";
      alert("Camera could not start. Type the SRN instead.");
      scanner = null;
    }
  });
}

function setupAttendance() {
  const root = document.querySelector('[data-page="attendance"]');
  if (!root) return;
  const input = document.getElementById("scan-input");
  const result = document.getElementById("scan-result");
  const payload = () => ({
    srn: input.value,
    date: root.dataset.date,
    session: root.dataset.session,
    course: root.dataset.course,
    status: "present",
  });

  async function mark(body) {
    if (!body.srn) return;
    const { data } = await postJson("/api/attendance/mark", body);
    if (data.ok) {
      paintResult(result, "served", "Present", data.message, data.student);
      input.value = "";
      setTimeout(() => window.location.reload(), 700);
    } else {
      paintResult(result, "missing", "Not found", data.message || "Could not mark attendance.");
    }
  }

  document.getElementById("scan-btn")?.addEventListener("click", () => mark(payload()));
  input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      mark(payload());
    }
  });
  document.querySelectorAll(".mark-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      mark({
        srn: btn.dataset.srn,
        date: root.dataset.date,
        session: root.dataset.session,
        course: root.dataset.course,
        status: btn.dataset.status,
      });
    });
  });
  setupCamera((code) => {
    input.value = code;
    mark(payload());
  });
}

function setupMeals() {
  const root = document.querySelector('[data-page="meals"]');
  if (!root) return;
  const input = document.getElementById("scan-input");
  const result = document.getElementById("scan-result");

  async function serve(srn) {
    if (!srn) return;
    const { data } = await postJson("/api/meals/serve", { srn, meal: root.dataset.meal });
    if (data.ok) {
      paintResult(result, "served", "Portion issued", data.message, data.student);
      input.value = "";
      setTimeout(() => window.location.reload(), 900);
      return;
    }
    const map = {
      not_cleared: ["blocked", "Not cleared"],
      already_served: ["repeat", "Already served"],
      not_found: ["missing", "Unknown card"],
      inactive: ["blocked", "Inactive ID"],
    };
    const [cls, title] = map[data.code] || ["missing", "Cannot serve"];
    paintResult(result, cls, title, data.message || "Meal refused.", data.student);
  }

  document.getElementById("scan-btn")?.addEventListener("click", () => serve(input.value));
  input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      serve(input.value);
    }
  });
  setupCamera((code) => {
    input.value = code;
    serve(code);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  renderQrCodes();
  setupAttendance();
  setupMeals();
});
