const $ = (id) => document.getElementById(id);
const number = (value) => value == null ? "—" : Number(value).toFixed(2);
const pressureBar = (valueKpa) => valueKpa == null ? "—" : (Number(valueKpa) / 100).toFixed(3);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[char]);

function showDoor(id, closed) {
  const node = $(id);
  if (closed === true) { node.textContent = "Закрыта"; node.className = "door closed"; }
  else if (closed === false) { node.textContent = "Открыта"; node.className = "door open"; }
  else { node.textContent = "Нет данных"; node.className = "door unknown"; }
}

function drawChart(items) {
  const canvas = $("chart"), context = canvas.getContext("2d"), ratio = devicePixelRatio || 1;
  const width = canvas.clientWidth, height = 300, sensors = ["t0", "t1", "t2", "t3"];
  canvas.width = width * ratio; canvas.height = height * ratio; context.scale(ratio, ratio); context.clearRect(0, 0, width, height);
  const points = items.map((item) => {
    const values = sensors.map((key) => item.temperatures_c?.[key]).filter(Number.isFinite);
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
  });
  const values = points.filter(Number.isFinite);
  if (!values.length) { context.fillStyle = "#94a3b8"; context.fillText("История средней температуры появится после первого измерения", 20, 40); return; }
  const min = Math.min(...values) - 1, max = Math.max(...values) + 1, pad = 28;
  context.strokeStyle = "#818cf8"; context.lineWidth = 3; context.beginPath(); let started = false;
  points.forEach((value, index) => { if (!Number.isFinite(value)) { started = false; return; }
    const x = pad + index * (width - pad * 2) / Math.max(1, points.length - 1); const y = height - pad - (value - min) * (height - pad * 2) / (max - min);
    started ? context.lineTo(x, y) : context.moveTo(x, y); started = true; });
  context.stroke();
}

async function getJson(url) { const response = await fetch(url); if (!response.ok) throw new Error(`${url}: ${response.status}`); return response.json(); }

async function refresh() {
  try {
    const [latest, history, journal] = await Promise.all([getJson("/api/v1/latest"), getJson("/api/v1/history?limit=1440"), getJson("/api/v1/events")]);
    const measurement = latest.measurement;
    if (measurement) {
      $("status").textContent = measurement.status === "online" ? "● Устройство онлайн" : "● Устройство офлайн";
      $("status").className = `status ${measurement.status}`;
      $("pressure").textContent = pressureBar(measurement.absolute_pressure_kpa);
      showDoor("door-1", measurement.doors_closed?.door_1);
      showDoor("door-2", measurement.doors_closed?.door_2);
      $("updated").textContent = new Date(measurement.timestamp).toLocaleString("ru-RU");
      $("device").textContent = measurement.device_id;
      $("temperatures").innerHTML = ["t0", "t1", "t2", "t3"].map((key) => `<div class="temp"><span>${key.toUpperCase()}</span><b>${number(measurement.temperatures_c[key])} °C</b></div>`).join("");
    }
    drawChart(history.measurements);
    $("events").innerHTML = journal.events.length ? journal.events.map((event) => `<div class="event"><time>${new Date(event.timestamp).toLocaleString("ru-RU")}</time><b>${escapeHtml(event.action)}</b><span>${escapeHtml(event.program)}${event.details ? ` · ${escapeHtml(event.details)}` : ""}</span></div>`).join("") : '<p class="muted">Событий пока нет</p>';
  } catch (error) { $("status").textContent = "Ошибка связи с сервером"; $("status").className = "status offline"; console.error(error); }
}

refresh();
setInterval(refresh, 10000);
