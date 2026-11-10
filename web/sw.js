/* ทำให้เว็บใช้ได้ตอนไม่มีอินเทอร์เน็ต
 * - หน้าเว็บและไฟล์ข้อมูล: ขอจากเน็ตก่อน ถ้าไม่มีเน็ตใช้ฉบับที่เก็บไว้ (เนื้อหาจึงใหม่เสมอเมื่อออนไลน์)
 * - ไฟล์โปรแกรมและสไตล์ที่มีเลขรุ่นใน URL: ใช้ฉบับที่เก็บไว้ได้ทันที และอัปเดตเบื้องหลัง
 * - ไลบรารีและฟอนต์จากภายนอก: เก็บไว้หลังโหลดครั้งแรก
 * ทุกหน้าที่เคยเปิดจะถูกเก็บอัตโนมัติ และหน้า "ใช้แบบไม่มีเน็ต" สั่งดาวน์โหลดทั้งหมดได้ */
const CACHE = "tgat-tutor-v1";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon-192.png", "icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function networkFirst(req) {
  const cache = await caches.open(CACHE);
  try {
    const res = await fetch(req, { cache: "no-cache" });
    if (res.ok) cache.put(req, res.clone());
    return res;
  } catch {
    const hit = await cache.match(req, { ignoreSearch: req.mode === "navigate" });
    if (hit) return hit;
    if (req.mode === "navigate") return cache.match("index.html");
    throw new Error("offline");
  }
}

async function staleWhileRevalidate(req) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(req);
  const net = fetch(req).then((res) => {
    if (res.ok || res.type === "opaque") cache.put(req, res.clone());
    return res;
  }).catch(() => null);
  return hit || (await net) || new Response("", { status: 504 });
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) {
    // ไลบรารีแสดงสูตร ตัวแปลงมาร์กดาวน์ และฟอนต์
    if (/cdn\.jsdelivr\.net|fonts\.(googleapis|gstatic)\.com/.test(url.host)) e.respondWith(staleWhileRevalidate(req));
    return;
  }
  if (req.mode === "navigate" || url.pathname.includes("/data/")) e.respondWith(networkFirst(req));
  else e.respondWith(staleWhileRevalidate(req));
});

/* หน้า "ใช้แบบไม่มีเน็ต" ส่งรายการไฟล์มาให้ดาวน์โหลดเก็บ แล้วรายงานความคืบหน้ากลับ */
self.addEventListener("message", (e) => {
  const msg = e.data || {};
  if (msg.type !== "download-all") return;
  e.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    const urls = msg.urls || [];
    let done = 0, failed = 0;
    const report = () => e.source && e.source.postMessage({ type: "download-progress", done, failed, total: urls.length });
    const queue = urls.slice();
    async function worker() {
      while (queue.length) {
        const u = queue.shift();
        try {
          const res = await fetch(u, { cache: "no-cache", mode: u.startsWith(location.origin) ? "same-origin" : "cors" });
          if (res.ok || res.type === "opaque") await cache.put(u, res);
          else failed += 1;
        } catch { failed += 1; }
        done += 1;
        if (done % 10 === 0 || done === urls.length) report();
      }
    }
    await Promise.all([worker(), worker(), worker(), worker()]);
    report();
  })());
});
