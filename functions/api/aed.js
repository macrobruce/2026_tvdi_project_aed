const SOURCE_URL = "https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=438c61ad-24f6-4e54-a1cc-e2cfe0e7051e";

export async function onRequestGet() {
  const upstream = await fetch(SOURCE_URL, {headers: {"Accept": "text/csv"}});
  if (!upstream.ok) {
    return new Response("無法取得台北市資料大平台的最新 AED 資料。", {
      status: 502,
      headers: {"Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store"}
    });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Cache-Control": "no-store"
    }
  });
}
