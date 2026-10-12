const SOURCE_URL = "https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=438c61ad-24f6-4e54-a1cc-e2cfe0e7051e";

export async function onRequestGet() {
  const [upstream, metadata] = await Promise.all([
    fetch(SOURCE_URL, {headers: {"Accept": "text/csv"}}),
    fetch("https://data.taipei/dataset/detail?id=cd050577-115f-4299-b37a-012ff490a632")
      .catch(() => null)
  ]);
  if (!upstream.ok) {
    return new Response("無法取得台北市資料大平台的最新 AED 資料。", {
      status: 502,
      headers: {"Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store"}
    });
  }

  const headers = {
    "Content-Type": "text/csv; charset=utf-8",
    "Cache-Control": "no-store"
  };
  if (metadata?.ok) {
    const html = await metadata.text();
    const cellStart = html.indexOf('data-th="更新時間"');
    const spanIndex = cellStart < 0 ? -1 : html.indexOf("<span", cellStart);
    const spanStart = spanIndex < 0 ? -1 : html.indexOf(">", spanIndex) + 1;
    const spanEnd = spanStart < 0 ? -1 : html.indexOf("</span>", spanStart);
    const updatedAt = spanEnd > spanStart ? html.slice(spanStart, spanEnd).trim() : "";
    if (updatedAt) headers["X-Data-Updated-At"] = updatedAt;
  }

  return new Response(upstream.body, {headers});
}
