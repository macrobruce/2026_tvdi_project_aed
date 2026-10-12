const DISTRICTS = new Map([
  ["63000010", "松山區"], ["63000020", "信義區"], ["63000030", "大安區"], ["63000040", "中山區"],
  ["63000050", "中正區"], ["63000060", "大同區"], ["63000070", "萬華區"], ["63000080", "文山區"],
  ["63000090", "南港區"], ["63000100", "內湖區"], ["63000110", "士林區"], ["63000120", "北投區"]
]);
const HOSPITALS = [
  ["國立臺灣大學醫學院附設醫院",25.0413,121.5195],["臺北市立聯合醫院（和平院區）",25.0354,121.5053],["西園醫院",25.0271,121.4986],
  ["臺北市立聯合醫院（中興院區）",25.05,121.5093],["振興醫療財團法人振興醫院",25.1167,121.5245],["臺北榮民總醫院",25.1208,121.5202],
  ["博仁綜合醫院",25.0514,121.5574],["三軍總醫院松山分院",25.0543,121.562],["基督復臨安息日會醫療財團法人臺安醫院",25.0485,121.5478],
  ["臺北醫學大學附設醫院",25.0261,121.5613],["馬偕紀念醫院（台北院區）",25.0581,121.5224],["萬芳醫院",24.9988,121.5578],
  ["臺北市立聯合醫院（忠孝院區）",25.0425,121.5866],["臺北市立聯合醫院（仁愛院區）",25.0378,121.5441],["國泰綜合醫院",25.0372,121.5517],
  ["新光醫療財團法人新光醫院",25.0934,121.5173],["臺北市立聯合醫院（陽明院區）",25.1051,121.5322],["三軍總醫院（內湖總院）",25.0682,121.5932]
];
const COLORS = {hot:"#df594f",cold:"#3987c6",normal:"#8291a0"};
const LABELS = {hot:"🔥 高密度熱區",cold:"❄️ 高風險冷區 (醫療孤島)",normal:"🔹 一般單點涵蓋"};
const PAGE_SIZE = 50;
const $ = (id) => document.getElementById(id);
let allRows = [];
let displayedRows = [];
let selectedHospitals = new Set();
let currentPage = 0;
let map;
let mapLayers;
let chartColors = [];

function parseCSV(text) {
  const rows = [];
  let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(field); field = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(field); if (row.some((value) => value !== "")) rows.push(row);
      row = []; field = "";
    } else field += ch;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  const headers = (rows.shift() || []).map((name) => name.replace(/^\uFEFF/, "").trim());
  return rows.map((values) => Object.fromEntries(headers.map((key, i) => [key, values[i] ?? ""])))
    .map((item) => {
      const latitude = Number(item["緯度"]), longitude = Number(item["經度"]);
      const nearest = HOSPITALS.map(([name, lat, lon]) => ({
        name,
        distance: 6371000 * 2 * Math.asin(Math.sqrt(
          Math.sin((latitude - lat) * Math.PI / 360) ** 2 +
          Math.cos(latitude * Math.PI / 180) * Math.cos(lat * Math.PI / 180) *
          Math.sin((longitude - lon) * Math.PI / 360) ** 2
        ))
      })).sort((a, b) => a.distance - b.distance)[0];
      return {...item,
        "行政區": DISTRICTS.get(String(item["區域代碼"]).trim()) || "其他/未知",
        "緯度": latitude, "經度": longitude,
        "最近急救醫院": nearest.name,
        "至最近醫院距離_公尺": nearest.distance
      };
    }).filter((item) => Number.isFinite(item["緯度"]) && Number.isFinite(item["經度"]));
}

function dbscan(rows, radius, minSamples) {
  const earth = 6371000, cosine = Math.cos(25.05 * Math.PI / 180), cellSize = radius;
  const coords = rows.map((row) => ({
    x: earth * cosine * row["經度"] * Math.PI / 180,
    y: earth * row["緯度"] * Math.PI / 180
  }));
  const grid = new Map();
  coords.forEach((point, i) => {
    const key = `${Math.floor(point.x / cellSize)}:${Math.floor(point.y / cellSize)}`;
    if (!grid.has(key)) grid.set(key, []);
    grid.get(key).push(i);
  });
  const neighbors = (index) => {
    const point = coords[index], gx = Math.floor(point.x / cellSize), gy = Math.floor(point.y / cellSize), found = [];
    for (let x = gx - 1; x <= gx + 1; x++) for (let y = gy - 1; y <= gy + 1; y++) {
      for (const candidate of grid.get(`${x}:${y}`) || []) {
        const dx = point.x - coords[candidate].x, dy = point.y - coords[candidate].y;
        if (dx * dx + dy * dy <= radius * radius) found.push(candidate);
      }
    }
    return found;
  };
  const labels = Array(rows.length).fill(null);
  let cluster = 0;
  for (let i = 0; i < rows.length; i++) {
    if (labels[i] !== null) continue;
    const near = neighbors(i);
    if (near.length < minSamples) { labels[i] = -1; continue; }
    labels[i] = cluster;
    const queue = near.filter((index) => index !== i), queued = new Set(queue);
    for (let cursor = 0; cursor < queue.length; cursor++) {
      const candidate = queue[cursor];
      if (labels[candidate] === -1) labels[candidate] = cluster;
      if (labels[candidate] !== null) continue;
      labels[candidate] = cluster;
      const expanded = neighbors(candidate);
      if (expanded.length >= minSamples) for (const neighbor of expanded) {
        if (!queued.has(neighbor)) { queued.add(neighbor); queue.push(neighbor); }
      }
    }
    cluster++;
  }
  return labels;
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
}
function fmt(value, digits = 0) { return Number(value).toLocaleString("zh-TW", {minimumFractionDigits:digits, maximumFractionDigits:digits}); }

function initControls() {
  const district = $("district");
  district.innerHTML = `<option value="all">全台北市</option>` + [...DISTRICTS.values()].map((name) => `<option value="${name}">${name}</option>`).join("");
  district.addEventListener("change", () => {
    selectedHospitals = new Set(availableHospitals().map((row) => row["最近急救醫院"]));
    updateHospitalOptions(); render();
  });
  $("hospital-search").addEventListener("input", updateHospitalOptions);
  $("hospital-all").addEventListener("click", () => {
    const names = availableHospitals().map((row) => row["最近急救醫院"]);
    const visible = names.filter((name) => name.toLocaleLowerCase().includes($("hospital-search").value.trim().toLocaleLowerCase()));
    if (visible.every((name) => selectedHospitals.has(name))) visible.forEach((name) => selectedHospitals.delete(name));
    else visible.forEach((name) => selectedHospitals.add(name));
    updateHospitalOptions(); render();
  });
  ["radius","min-samples","cold-distance"].forEach((id) => $(id).addEventListener("input", () => {
    $("radius-value").textContent = `${fmt($("radius").value)} 公尺`;
    $("min-samples-value").textContent = `${fmt($("min-samples").value)} 台`;
    $("cold-distance-value").textContent = `${fmt($("cold-distance").value)} 公尺`;
    render();
  }));
  $("page-prev").addEventListener("click", () => { currentPage--; renderTable(); });
  $("page-next").addEventListener("click", () => { currentPage++; renderTable(); });
}

function availableHospitals() {
  const district = $("district").value;
  return allRows.filter((row) => district === "all" || row["行政區"] === district);
}
function updateHospitalOptions() {
  const rows = availableHospitals(), names = [...new Set(rows.map((row) => row["最近急救醫院"]).filter(Boolean))].sort();
  if (!selectedHospitals.size && !rows.length) return;
  const query = $("hospital-search").value.trim().toLocaleLowerCase();
  const filtered = names.filter((name) => name.toLocaleLowerCase().includes(query));
  $("hospital-options").innerHTML = filtered.length ? filtered.map((name) => `<label class="hospital-option"><input type="checkbox" value="${escapeHTML(name)}" ${selectedHospitals.has(name) ? "checked" : ""}><span>${escapeHTML(name)}</span></label>`).join("") : `<p class="empty-state">沒有符合的醫院</p>`;
  $("hospital-options").querySelectorAll("input").forEach((input) => input.addEventListener("change", () => {
    if (input.checked) selectedHospitals.add(input.value); else selectedHospitals.delete(input.value);
    render();
  }));
}

function initMap() {
  map = L.map("map", {scrollWheelZoom:true}).setView([25.055,121.55],12);
  L.tileLayer("https://wmts.nlsc.gov.tw/wmts/EMAP/default/GoogleMapsCompatible/{z}/{y}/{x}", {
    maxZoom:19,
    attribution:"&copy; <a href=\"https://maps.nlsc.gov.tw/\">內政部國土測繪中心</a>"
  }).addTo(map);
  mapLayers = {clusters:L.layerGroup().addTo(map), hospitals:L.layerGroup().addTo(map), hot:L.layerGroup().addTo(map)};
}
function zoneKey(row) { return row.cluster >= 0 ? "hot" : row["至最近醫院距離_公尺"] >= Number($("cold-distance").value) ? "cold" : "normal"; }
function renderMap(rows) {
  Object.values(mapLayers).forEach((layer) => layer.clearLayers());
  if (!rows.length) return;
  const clusters = new Map();
  rows.forEach((row) => { if (row.cluster >= 0) { if (!clusters.has(row.cluster)) clusters.set(row.cluster, []); clusters.get(row.cluster).push(row); } });
  clusters.forEach((members, id) => {
    const center = [members.reduce((sum, row) => sum + row["緯度"],0)/members.length, members.reduce((sum, row) => sum + row["經度"],0)/members.length];
    L.circle(center, {radius:Number($("radius").value),color:COLORS.hot,fillColor:COLORS.hot,fillOpacity:.22,weight:1}).bindPopup(`🔥 高密度熱區 #${id+1}<br>包含 ${members.length} 台 AED`).addTo(mapLayers.hot);
  });
  const markers = L.markerClusterGroup({showCoverageOnHover:false, spiderfyOnMaxZoom:true});
  rows.forEach((row) => {
    const key = zoneKey(row), type = LABELS[key];
    const popup = `<b>${escapeHTML(row["場所名稱"])}</b><br>區域分類：${type}<br>地址：${escapeHTML(row["場所地址"] || "無")}<br>最近急救醫院：${escapeHTML(row["最近急救醫院"])}<br>送醫距離：${fmt(row["至最近醫院距離_公尺"],1)} 公尺`;
    L.circleMarker([row["緯度"],row["經度"]], {radius:5,color:"#fff",weight:1,fillColor:COLORS[key],fillOpacity:.94}).bindPopup(popup).bindTooltip(`${escapeHTML(row["場所名稱"])} (${type})`).addTo(markers);
  });
  mapLayers.clusters.addLayer(markers);
  const enabledHospitals = new Set(rows.map((row) => row["最近急救醫院"]));
  HOSPITALS.filter(([name]) => enabledHospitals.has(name) && selectedHospitals.has(name)).forEach(([name,lat,lon]) => {
    L.marker([lat,lon], {icon:L.divIcon({className:"hospital-marker",html:"✚",iconSize:[24,24],iconAnchor:[12,12]})})
      .bindPopup(`<b>🏥 急救責任醫院：${escapeHTML(name)}</b>`).bindTooltip(`🏥 ${escapeHTML(name)}`).addTo(mapLayers.hospitals);
  });
  const bounds = L.latLngBounds(rows.map((row) => [row["緯度"],row["經度"]]));
  map.fitBounds(bounds.pad(.08), {maxZoom:$("district").value === "all" ? 12 : 14});
}

function renderCharts(rows) {
  const counts = {hot:0,cold:0,normal:0}, hospitals = new Map();
  rows.forEach((row) => {
    const zone = zoneKey(row); counts[zone]++;
    const name = row["最近急救醫院"] || "未分類";
    if (!hospitals.has(name)) hospitals.set(name,{hot:0,cold:0,normal:0});
    hospitals.get(name)[zone]++;
  });
  const total = rows.length || 1, degrees = counts.hot/total*360, degrees2 = degrees+counts.cold/total*360;
  $("zone-donut").style.background = rows.length ? `conic-gradient(${COLORS.hot} 0deg ${degrees}deg,${COLORS.cold} ${degrees}deg ${degrees2}deg,${COLORS.normal} ${degrees2}deg 360deg)` : "#e8edf1";
  $("donut-total").textContent = fmt(rows.length);
  $("zone-legend").innerHTML = [["hot",counts.hot],["cold",counts.cold],["normal",counts.normal]].map(([key,count]) => `<div><i style="background:${COLORS[key]}"></i><span>${LABELS[key]}</span><small>${fmt(count)} · ${fmt(rows.length ? count/rows.length*100 : 0,1)}%</small></div>`).join("");
  const sorted = [...hospitals.entries()].sort((a,b) => (b[1].hot+b[1].cold+b[1].normal)-(a[1].hot+a[1].cold+a[1].normal));
  $("hospital-chart").innerHTML = sorted.length ? sorted.map(([name,values]) => {
    const sum = values.hot+values.cold+values.normal || 1;
    return `<div class="bar-row"><span class="bar-label" title="${escapeHTML(name)}">${escapeHTML(name)}</span><div class="bar-stack"><span style="width:${values.hot/sum*100}%;background:${COLORS.hot}"></span><span style="width:${values.cold/sum*100}%;background:${COLORS.cold}"></span><span style="width:${values.normal/sum*100}%;background:${COLORS.normal}"></span></div><span class="bar-total">${fmt(sum)}</span></div>`;
  }).join("") : `<div class="empty-state">目前條件下沒有資料</div>`;
}

function renderInsights(rows) {
  const host = $("insight-body");
  if (!rows.length) { host.innerHTML = `<div class="empty-state">目前選擇的條件下無資料，無法提供系統建議。</div>`; return; }
  const total = rows.length, hot = rows.filter((row) => zoneKey(row)==="hot").length, cold = rows.filter((row) => zoneKey(row)==="cold").length;
  const avg = rows.reduce((sum,row) => sum+row["至最近醫院距離_公尺"],0)/total;
  const farthest = rows.reduce((a,b) => a["至最近醫院距離_公尺"] > b["至最近醫院距離_公尺"] ? a : b);
  const load = new Map(); rows.forEach((row) => load.set(row["最近急救醫院"],(load.get(row["最近急救醫院"])||0)+1));
  const [topName,topCount] = [...load.entries()].sort((a,b)=>b[1]-a[1])[0] || ["無",0];
  const district = $("district").value === "all" ? "全台北市" : $("district").value;
  const radius = Number($("radius").value), threshold = Number($("cold-distance").value);
  host.innerHTML = `
    <div class="insight-callouts"><div class="callout hot"><strong>資源重複配置率　${fmt(hot/total*100,1)}%</strong><span>${fmt(hot)} / ${fmt(total)} 處位於高度密集聚落</span></div><div class="callout cold"><strong>醫療冷區占比　${fmt(cold/total*100,1)}%</strong><span>${fmt(cold)} 處超過 ${fmt(threshold)} 公尺門檻</span></div><div class="callout average"><strong>平均送醫直線距離　${fmt(avg,1)} 公尺</strong><span>依每處 AED 到最近急救責任醫院計算</span></div></div>
    <h3>空間結構診斷</h3>
    <p><b>熱區集中：</b>${escapeHTML(district)} 在 ${fmt(radius)} 公尺搜尋半徑下，有 ${fmt(hot)} 處 AED 落在高度密集聚落（${fmt(hot/total*100,1)}%）。可優先盤點捷運站、商場或行政中心周邊設備的實際使用率。</p>
    <p><b>醫療涵蓋盲區：</b>${escapeHTML(district)} 有 ${fmt(cold)} 處 AED（${fmt(cold/total*100,1)}%）距最近急救責任醫院超過 ${fmt(threshold)} 公尺。最遠點位為「${escapeHTML(farthest["場所名稱"])}」，距 ${escapeHTML(farthest["最近急救醫院"])} ${fmt(farthest["至最近醫院距離_公尺"],1)} 公尺。</p>
    <p><b>後送負載：</b>${fmt(topCount)} 處（${fmt(topCount/total*100,1)}%）AED 點位最鄰近 ${escapeHTML(topName)}，可持續關注院區急診量能和責任區域分流。</p>
    <h3>管理行動建議</h3>
    <ol><li><b>盤點熱區：</b>針對 ${fmt(hot)} 處熱區進行使用率及設置條件盤點，評估移設至周邊住宅區、老舊社區或公園。</li><li><b>補強冷區：</b>將「${escapeHTML(farthest["場所名稱"])}」等冷區列入優先輔導名單，鼓勵大樓、商店及加油站增設公眾 AED。</li><li><b>強化社區急救：</b>為遠離醫院的場址管理人員、志工及巡守隊安排 CPR+AED 培訓，提升救護車抵達前的應變能力。</li><li><b>維持資料更新：</b>定期複查座標、設備可用性與開放時間，並同步公開於急救資訊服務。</li></ol>
    <p class="muted-note">此為依目前 CSV 欄位及篩選條件產生的空間統計，醫院距離為直線距離。</p>`;
}

function renderTable() {
  const pages = Math.max(1,Math.ceil(displayedRows.length/PAGE_SIZE));
  currentPage = Math.min(Math.max(0,currentPage),pages-1);
  const start = currentPage*PAGE_SIZE, shown = displayedRows.slice(start,start+PAGE_SIZE);
  $("table-title").textContent = `詳細熱冷區分類數據 (${$("district").value === "all" ? "全台北市" : $("district").value})`;
  $("table-count").textContent = `${fmt(displayedRows.length)} 筆資料`;
  $("page-label").textContent = displayedRows.length ? `第 ${fmt(currentPage+1)} / ${fmt(pages)} 頁 · 顯示 ${fmt(start+1)}–${fmt(Math.min(start+PAGE_SIZE,displayedRows.length))} 筆` : "無資料";
  $("page-prev").disabled = currentPage === 0; $("page-next").disabled = currentPage >= pages-1;
  $("data-rows").innerHTML = shown.length ? shown.map((row) => {
    const key = zoneKey(row), zoneClass = key === "hot" ? "zone-hot" : key === "cold" ? "zone-cold" : "";
    return `<tr><td>${escapeHTML(row["行政區"])}</td><td>${escapeHTML(row["場所名稱"])}</td><td class="${zoneClass}">${LABELS[key]}</td><td>${escapeHTML(row["最近急救醫院"])}</td><td class="numeric">${fmt(row["至最近醫院距離_公尺"],1)} m</td></tr>`;
  }).join("") : `<tr><td class="empty-state" colspan="5">目前條件下沒有資料</td></tr>`;
}

function render() {
  const district = $("district").value, radius = Number($("radius").value), minimum = Number($("min-samples").value);
  let rows = availableHospitals().filter((row) => selectedHospitals.has(row["最近急救醫院"]));
  const labels = dbscan(rows,radius,minimum);
  displayedRows = rows.map((row,index) => ({...row,cluster:labels[index]}));
  const hot = displayedRows.filter((row) => zoneKey(row)==="hot").length;
  const cold = displayedRows.filter((row) => zoneKey(row)==="cold").length;
  const farthest = displayedRows.reduce((max,row) => !max || row["至最近醫院距離_公尺"] > max["至最近醫院距離_公尺"] ? row : max,null);
  $("kpi-title").textContent = `核心數據指標 (${district === "all" ? "全台北市" : district})`;
  $("insight-title").textContent = `空間決策與資源優化建議 (${district === "all" ? "全台北市" : district})`;
  $("record-count").textContent = `符合篩選條件 ${fmt(displayedRows.length)} 處 AED`;
  $("kpi-total").textContent = fmt(displayedRows.length); $("kpi-area").textContent = "處分析地點";
  $("kpi-hot").textContent = fmt(hot); $("kpi-hot-ratio").textContent = `占目前點位 ${fmt(displayedRows.length ? hot/displayedRows.length*100 : 0,1)}%`;
  $("kpi-cold").textContent = fmt(cold); $("kpi-cold-ratio").textContent = `占目前點位 ${fmt(displayedRows.length ? cold/displayedRows.length*100 : 0,1)}%`;
  $("kpi-farthest").textContent = farthest ? `${fmt(farthest["至最近醫院距離_公尺"],1)} m` : "N/A";
  $("kpi-farthest-name").textContent = farthest ? farthest["場所名稱"] : "最近急救責任醫院";
  renderMap(displayedRows); renderCharts(displayedRows); renderInsights(displayedRows); renderTable();
}

function formatTimestamp(value) {
  const timestamp = value.includes(" ") ? value.replace(" ", "T") + "+08:00" : value;
  const date = new Date(timestamp);
  if (!Number.isFinite(date.getTime())) return "來源未提供，請查看資料平台";
  return new Intl.DateTimeFormat("zh-TW", {
    year:"numeric", month:"2-digit", day:"2-digit",
    hour:"2-digit", minute:"2-digit", second:"2-digit",
    hour12:false, timeZone:"Asia/Taipei"
  }).format(date);
}

async function loadData() {
  const button = $("reload-data"), status = $("data-status");
  button.disabled = true;
  status.classList.remove("ready", "error");
  status.textContent = "正在讀取資料…";
  try {
    const response = await fetch("/api/aed", {cache:"no-store"});
    if (!response.ok) throw new Error("HTTP " + response.status);
    const rows = parseCSV(await response.text());
    if (!rows.length) throw new Error("CSV 中沒有有效的座標資料");

    const isFirstLoad = !allRows.length;
    allRows = rows;
    const hospitals = availableHospitals().map((row) => row["最近急救醫院"]);
    if (isFirstLoad) selectedHospitals = new Set(hospitals);
    else selectedHospitals = new Set(hospitals.filter((name) => selectedHospitals.has(name)));

    updateHospitalOptions();
    render();
    const updatedAt = response.headers.get("X-Data-Updated-At");
    $("data-updated").textContent = updatedAt
      ? formatTimestamp(updatedAt)
      : "來源未提供，請查看資料平台";
    $("data-fetched").textContent = formatTimestamp(new Date().toISOString());
    status.textContent = "已載入資料 · " + fmt(allRows.length) + " 處";
    status.classList.add("ready");
  } catch (error) {
    console.error(error);
    status.textContent = allRows.length ? "更新失敗，保留目前資料；請重試" : "資料載入失敗，請檢查連線後重試";
    status.classList.add("error");
  } finally {
    button.disabled = false;
  }
}

function start() {
  initControls();
  $("reload-data").addEventListener("click", () => typeof L === "undefined" ? location.reload() : loadData());
  if (typeof L === "undefined") {
    $("data-status").textContent = "地圖套件載入失敗，請重新整理頁面";
    $("data-status").classList.add("error");
    return;
  }
  initMap();
  loadData();
}
start();
