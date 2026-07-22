// Utilidades compartidas y navegación adaptable.
const $ = (s) => document.querySelector(s),
  toast = (m) => {
    let e = $("#toast");
    e.textContent = m;
    e.classList.add("show");
    setTimeout(() => e.classList.remove("show"), 3000);
  };
$(".menu")?.addEventListener("click", () =>
  document.querySelector("nav").classList.toggle("open"),
);
// Cliente HTTP común para consumir respuestas JSON de la API Flask.
async function api(url, o = {}) {
  o.headers = { ...o.headers, "Content-Type": "application/json" };
  let r = await fetch(url, o),
    d = await r.json();
  if (!r.ok) throw Error(d.message || "Error de conexión");
  return d;
}
// Administración de personas.
function openPerson() {
  personForm.reset();
  pid.value = "";
  personTitle.textContent = "Registrar persona";
  personDialog.showModal();
}
function editPerson(p) {
  openPerson();
  pid.value = p.id;
  personTitle.textContent = "Editar persona";
  [
    "codigo",
    "nombres",
    "apellidos",
    "correo",
    "telefono",
    "sede",
    "grupo",
  ].forEach((k) => (document.getElementById(k).value = p[k] || ""));
}
$("#personForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  let id = pid.value,
    d = {};
  [
    "codigo",
    "nombres",
    "apellidos",
    "correo",
    "telefono",
    "sede",
    "grupo",
  ].forEach((k) => (d[k] = document.getElementById(k).value));
  try {
    await api("/api/personas" + (id ? "/" + id : ""), {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(d),
    });
    location.reload();
  } catch (x) {
    toast(x.message);
  }
});
async function togglePerson(id, activo) {
  try {
    await api(`/api/personas/${id}/estado`, {
      method: "PATCH",
      body: JSON.stringify({ activo }),
    });
    location.reload();
  } catch (e) {
    toast(e.message);
  }
}
function filterRows() {
  let q = search.value.toLowerCase(),
    s = status.value;
  document
    .querySelectorAll("#people tbody tr")
    .forEach(
      (r) =>
        (r.hidden =
          !(r.dataset.search || "").toLowerCase().includes(q) ||
          (s && r.dataset.status !== s)),
    );
}
// Administración de eventos.
function openEvent() {
  eventForm.reset();
  eid.value = "";
  eventTitle.textContent = "Crear evento";
  eventDialog.showModal();
}
function editEvent(e) {
  openEvent();
  eid.value = e.id;
  eventTitle.textContent = "Editar evento";
  enombre.value = e.nombre;
  efecha.value = e.fecha;
  ehora.value = e.hora_inicio;
  esede.value = e.sede || "";
  edescripcion.value = e.descripcion || "";
}
$("#eventForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  let id = eid.value,
    d = {
      nombre: enombre.value,
      fecha: efecha.value,
      hora_inicio: ehora.value,
      sede: esede.value,
      descripcion: edescripcion.value,
      estado: "abierto",
    };
  try {
    await api("/api/eventos" + (id ? "/" + id : ""), {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(d),
    });
    location.reload();
  } catch (x) {
    toast(x.message);
  }
});
async function toggleEvent(id, estado) {
  try {
    await api(`/api/eventos/${id}/estado`, {
      method: "PATCH",
      body: JSON.stringify({ estado }),
    });
    location.reload();
  } catch (e) {
    toast(e.message);
  }
}
// Escáner QR y alternativa de registro manual.
let scanner,
  lastToken = "",
  lastAt = 0;
async function submitAttendance(p) {
  let eventId = $("#scanEvent")?.value;
  if (!eventId) return showResult("Selecciona un evento.", false);
  try {
    let d = await api("/api/asistencias/registrar", {
      method: "POST",
      body: JSON.stringify({ ...p, evento_id: Number(eventId) }),
    });
    showResult(
      `${d.message}: ${d.data.persona} · ${new Date(d.data.fecha_hora).toLocaleString("es")}`,
      true,
    );
  } catch (e) {
    showResult(e.message, false);
  }
}
function showResult(m, s) {
  let e = $("#scanResult");
  e.textContent = m;
  e.className = "result " + (s ? "success" : "error");
}
async function startScanner() {
  if (!window.isSecureContext)
    return showResult("La cámara requiere HTTPS o localhost.", false);
  if (!window.Html5Qrcode)
    return showResult("No se pudo cargar la librería del escáner.", false);
  try {
    scanner ||= new Html5Qrcode("reader");
    await scanner.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: { width: 220, height: 220 } },
      (t) => {
        let n = Date.now();
        if (t === lastToken && n - lastAt < 5000) return;
        lastToken = t;
        lastAt = n;
        submitAttendance({ token: t });
      },
      () => {},
    );
    startScan.disabled = true;
  } catch (e) {
    showResult(
      "No se pudo acceder a la cámara. Revisa el permiso o usa el registro manual.",
      false,
    );
  }
}
$("#manualForm")?.addEventListener("submit", (e) => {
  e.preventDefault();
  submitAttendance({ codigo: manualCode.value.trim() });
});
// Historial, filtros y exportación CSV.
function params() {
  return new URLSearchParams(new FormData($("#attendanceFilters")));
}
function esc(v) {
  let d = document.createElement("div");
  d.textContent = v ?? "";
  return d.innerHTML;
}
async function loadAttendance() {
  if (!$("#attendanceBody")) return;
  try {
    let d = await api("/api/asistencias?" + params());
    attendanceBody.innerHTML = d.data.length
      ? d.data
          .map(
            (a) =>
              `<tr><td><b>${esc(a.codigo)}</b></td><td>${esc(a.persona)}</td><td>${esc(a.evento)}</td><td>${new Date(a.fecha_hora).toLocaleString("es")}</td><td>${esc(a.metodo_registro)}</td></tr>`,
          )
          .join("")
      : '<tr><td colspan="5" class="empty">No hay resultados.</td></tr>';
  } catch (e) {
    toast(e.message);
  }
}
$("#attendanceFilters")?.addEventListener("submit", (e) => {
  e.preventDefault();
  loadAttendance();
});
function exportCsv() {
  location.href = "/api/asistencias/exportar?" + params();
}
loadAttendance();
