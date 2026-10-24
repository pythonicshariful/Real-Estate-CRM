# Round 4 — লগইন ফিক্স ও পারফরম্যান্স রিপোর্ট

**প্রজেক্ট:** Southeast Landmark CRM v2.0
**তারিখ:** ২৪ অক্টোবর ২০২৬
**স্কোপ:** (১) "লগইন করলে সঙ্গে সঙ্গে লগআউট হয়ে যায়" — সমাধান, (২) "ওয়েবসাইট অনেক স্লো" — পারফরম্যান্স উন্নয়ন

---

## ১. সারসংক্ষেপ

| বিষয় | আগে | পরে |
|---|---|---|
| লগইন (in-app preview / sandboxed iframe) | ফর্ম সাবমিটই হতো না, ৯৭ ক্যারেক্টার রেন্ডার | লগইন সফল, সেশন টিকে থাকে, নেভিগেশনে টিকে থাকে |
| লগইন (সাধারণ ব্রাউজার) | কাজ করত, কিন্তু যেকোনো একটা 401-এ লগআউট | কাজ করে, ভুয়া 401-এ আর লগআউট হয় না |
| প্রতি পেজে ডাউনলোড | ~৭০০–৭৫০ KB (লগইন পেজে ~১ MB+) | ২৮৬–৪৪৯ KB; gzip-এর পরে তারে **৬৬–১১৯ KB** |
| dashboard.html DCL | ২৫৯ ms | **৮০ ms** |
| events.html DCL | ২৭৭ ms | **৬৫ ms** |
| নিজের সার্ভার থেকে অ্যাসেট | ২৫–৩০ KB | ২৫–৩০ KB (**কিন্তু এখন gzip**) |
| থার্ড-পার্টি CDN | Tailwind JIT ৩৯৮ KB + jsDelivr + three.js ৬০৩ KB | **০ KB** (সব self-hosted) |
| অটোমেটেড টেস্ট | ১৭০ | **১৭০ পাস** + নতুন ৬টি auth টেস্ট + ২৭ পেজ ক্রল |

---

## ২. লগইন সমস্যা — আসল কারণ

প্রথমে ভাবা হয়েছিল এটা সার্ভারের 401/টোকেন সমস্যা। কিন্তু মাপজোক করে দেখা গেল **সাধারণ ব্রাউজারে লগইন একদম ঠিকঠাক কাজ করে**:

- `repro_login.js` → `admin@southeast.com / Admin@123` দিয়ে সত্যিকারের UI লগইন → `/admin-dashboard.html`-এ পৌঁছায়, টোকেন ৪৫৩ ক্যারেক্টার, ৭টা API কল সব ২০০।
- `find401.js` → লগইন করা অ্যাডমিন হিসেবে ২৩টা পেজ + ১০ সেকেন্ড আইডল → **০টা non-2xx রেসপন্স**, লগআউটে কোনো বাউন্স নেই।

তাহলে সমস্যা কোথায়? **অ্যাপটি যে sandboxed iframe-এ চলে (in-app preview), সেখানে।** `sandbox_test.js` দিয়ে ঠিক ওই পরিবেশ বানিয়ে ধরা পড়ে **তিনটা আলাদা ব্লকার** একসাথে কাজ করছিল:

### ব্লকার ১ — `localStorage` একদম বন্ধ

```
SecurityError: Failed to read the 'localStorage' property from 'Window':
The document is sandboxed and lacks the 'allow-same-origin' flag.
```

`auth.js` লগইনের পরে `crm_token` localStorage-এ লিখত। লেখাটাই exception-এ ফেটে যেত → সেশন কখনো সেভ হতো না → পরের পেজে গিয়ে "লগইন নেই" → লগইন স্ক্রিন। **এটাই ছিল "সঙ্গে সঙ্গে লগআউট"-এর মূল কারণ।**

### ব্লকার ২ — ES module ব্লকড (CORS)

`api.js`, `app.js`, `auth.js` — সব `<script type="module">`। sandboxed iframe-এ ডকুমেন্টের origin `null` হয়ে যায়, আর `<script type="module">` সব সময় CORS-মোডে ফেচ হয়। সার্ভার `/assets/*`-এ `Access-Control-Allow-Origin` হেডার দিত না → **তিনটা মডিউলই লোডই হতো না** → কোনো JS-ই চলত না।

### ব্লকার ৩ — ফর্ম সাবমিট ইভেন্টই ফায়ার হয় না

Chrome-এর মেসেজ:
```
Blocked form submission to '' because the form's frame is sandboxed
and the 'allow-forms' permission is not set.
```
HTML স্পেক অনুযায়ী ফর্ম "navigate করতে না পারলে" **`submit` ইভেন্ট ফায়ার করার আগেই** রিটার্ন করে। তাই `form.addEventListener('submit', e => { e.preventDefault(); ... })` কখনো চলে না — লগইন বাটনে ক্লিক করলে কিছুই হয় না।

### ব্লকার ৪ (লুকানো বোমা) — যেকোনো 401 = লগআউট

`assets/js/sidebar.js`-এ একটা গ্লোবাল `window.fetch` ইন্টারসেপ্টর ছিল:

```js
if (response.status === 401) { window.doLogout(); }   // ← আগের কোড
```

একটা ব্যাকগ্রাউন্ড রিকোয়েস্ট ৪০১ ফেরালেই পুরো সেশন মুছে যেত। ধীর নেটওয়ার্ক বা একটা মিস-কনফিগার্ড কলই যথেষ্ট ছিল — ব্যবহারকারীর কাছে যেটা "হঠাৎ লগআউট" দেখাত।

---

## ৩. লগইন ফিক্স — কী বদলানো হলো

### ৩.১ `assets/js/crm-store.js` (নতুন ফাইল, ২৭টা পেজের `<head>`-এ সবার আগে)

- **Storage shim:** একবার `localStorage` টেস্ট করে। ব্লকড হলে `window.name`-ভিত্তিক একটা API-সামঞ্জস্যপূর্ণ শিম বসায় (`getItem`/`setItem`/`removeItem`/`clear`/`key`/`length`)। `window.name` বেছে নেওয়ার কারণ — এটা **একই ট্যাবে নেভিগেশনের পরও টিকে থাকে** (in-memory হলে পেজ বদলালেই সেশন হারাত)।
- **Form shim:** শুধু `window.origin === 'null'` হলে (অর্থাৎ সত্যিই sandboxed) ফর্মের সাবমিট বাটনে ক্লিক ও Enter কী ধরে **সিন্থেটিক `submit` ইভেন্ট** ডিসপ্যাচ করে, যাতে বিদ্যমান সব `addEventListener('submit', ...)` কোড অপরিবর্তিত থাকলেও চলে। সাধারণ ব্রাউজারে এই শিম **ইনস্টলই হয় না** — আচরণ আগের মতোই।

### ৩.২ `app/__init__.py` — `/assets/*`-এ CORS

```python
cors.init_app(app, resources={
    r"/api/*":   {"origins": app.config.get('CORS_ORIGINS', '*')},
    r"/assets/*": {"origins": "*"},        # নতুন — ES module লোড হওয়ার জন্য
})
```
`/assets/*` শুধু পাবলিক কোড (কোনো কুকি/টোকেন নেই), তাই `*` নিরাপদ।

### ৩.৩ `assets/js/sidebar.js` — ৪০১ হ্যান্ডলার নরম করা

```js
// আগে: যেকোনো 401 → doLogout()
// এখন: শুধু (ক) Authorization হেডারসহ আসল /api/* কল, এবং (খ) auth endpoint নয়
//       — তারপরও আগে /api/auth/me দিয়ে যাচাই, তবেই লগআউট
if (hasAuth && !isAuthEndpoint && url.indexOf('/api/') !== -1) {
  confirmAndLogout();     // একবারই চলে, নেটওয়ার্ক এরর হলে সেশন রাখে
}
```

### ৩.৪ যাচাই (`auth_401_test.js` — ৬/৬ পাস)

| টেস্ট | ফলাফল |
|---|---|
| ভুয়া টোকেন দিয়ে করা রিকোয়েস্ট কলারকে 401 দেয় | PASS |
| **ভুয়া 401-এ বৈধ সেশন টিকে থাকে** (leads পেজেই থাকে) | PASS |
| সত্যিই মৃত টোকেন হলে লগইন পেজে ফেরে | PASS |
| ভুল পাসওয়ার্ডে লগইন পেজেই থাকে | PASS |
| ভুল পাসওয়ার্ডে এরর মেসেজ দেখায় | PASS |
| ভুল পাসওয়ার্ডে টোকেন স্টোর হয় না | PASS |

### ৩.৫ Sandboxed preview-তে প্রমাণ (`sandbox_session.js`)

```
AFTER LOGIN:      path=/admin-dashboard.html  token=453 chars  role=ADMIN  mode="window.name (sandbox fallback)"
AFTER NAVIGATION: path=/leads.html            token=453 chars
CONSOLE ERRORS:   none
```

---

## ৪. পারফরম্যান্স — কোথায় কী ব্যয় হচ্ছিল

শুরুতে ব্যাকএন্ড মাপা হয়: **API ৭–১৪ ms, স্ট্যাটিক ফাইল ১.২–১.৬ ms**। অর্থাৎ সার্ভার সমস্যা ছিল না — সমস্যা ছিল ব্রাউজারে যা পাঠানো হচ্ছিল।

প্রতি পেজে ~৭০০–৭৫০ KB, তার মধ্যে:

| রিসোর্স | সাইজ | কেন খারাপ |
|---|---|---|
| `cdn.tailwindcss.com` | **৩৯৮ KB** | ব্রাউজারে Tailwind JIT কম্পাইলার চলে — প্রতিটা পেজে |
| `cdn.jsdelivr.net` (Chart.js / FullCalendar) | ২০০–২৭৫ KB | থার্ড-পার্টি DNS + TLS, render-blocking |
| `three.js` r128 (শুধু লগইন পেজে) | **৬০৩ KB** | শুধু ব্যাকগ্রাউন্ডের কণার জন্য — আর যে `<canvas>`-এ আঁকত সেই এলিমেন্টই DOM-এ ছিল না! |
| Google Fonts | ৩১–৪৭ KB | render-blocking |
| নিজের কোড | ২৫–৩০ KB | — |

---

## ৫. পারফরম্যান্স ফিক্স — ৭টা পরিবর্তন

### ৫.১ Tailwind CDN → প্রি-কম্পাইলড CSS
`cdn.tailwindcss.com` (৩৯৮ KB, প্রতিবার ব্রাউজারে কম্পাইল করে) বাদ। বদলে Tailwind 3.4.17 দিয়ে **শুধু ব্যবহৃত ক্লাসগুলো** স্ক্যান করে বিল্ড করা `assets/css/tailwind.css`:

- **৪৯ KB raw → ৯ KB gzip** (আগে ৩৯৮ KB)
- ২৭টা HTML পেজ + সব JS ফাইল স্ক্যান করা
- রিবিল্ড: `backend/tools/build-tailwind.sh` (নতুন ফাইল)

> ⚠️ **গুরুত্বপূর্ণ:** কোনো HTML/JS-এ নতুন Tailwind ক্লাস যোগ করলে `tools/build-tailwind.sh` চালাতে হবে, নইলে ওই ক্লাসের কোনো CSS থাকবে না।

### ৫.২ three.js সম্পূর্ণ বাদ (৬০৩ KB)
কোডে গার্ড ছিল `if (document.getElementById('auth-canvas') && ...)` — কিন্তু `auth-canvas` এলিমেন্টই পেজে নেই। অর্থাৎ ৬০৩ KB **সম্পূর্ণ অপচয়** ছিল। স্ক্রিপ্ট আর ডেড কোড দুটোই সরানো হয়েছে।

### ৫.৩ Chart.js / FullCalendar self-hosted + `defer`
`/assets/vendor/`-এ কপি (Chart.js ২০৫ KB → ৭২ KB gzip, FullCalendar ২৮১ KB → ৮৩ KB gzip)। jsDelivr-এ আর কোনো কল নেই। `defer` দেওয়ায় এগুলো আর ফার্স্ট পেইন্ট ব্লক করে না — যেখানে পেজের ইনলাইন কোড `Chart.defaults` ব্যবহার করত, সেগুলো `DOMContentLoaded`-এ মুড়ে দেওয়া হয়েছে (`dashboard.html`, `reports.html`, `analytics.html`)।

### ৫.৪ gzip কম্প্রেশন (নতুন)
`app/utils/compression.py` — Flask-এ ট্রান্সপারেন্ট gzip middleware, কোনো নতুন ডিপেন্ডেন্সি ছাড়া। ফাইলের mtime দিয়ে কম্প্রেসড বাইট ক্যাশ করে।

- `dashboard.html`: ২১ KB → **৫.৫ KB**
- `theme.css`: ২২ KB → **৫ KB**
- `tailwind.css`: ৪৯ KB → **৯ KB**

### ৫.৫ ক্যাশ হেডার
`/assets/*` → `public, max-age=86400, must-revalidate`; HTML → `no-cache` (নতুন অ্যাসেট রেফার করে বলে)।

### ৫.৬ Google Fonts নন-ব্লকিং
`media="print" onload="this.media='all'"` — ফন্ট লোড হতে হতে টেক্সট ফলব্যাক ফন্টে রেন্ডার হয়, LCP/First Paint ব্লক হয় না।

### ৫.৭ rate limiter আর প্রতি রিকোয়েস্টে DB ছুঁছে না
আগে `RATELIMIT_STORAGE_URI` ছিল SQLite — মানে **প্রতিটা রিকোয়েস্টে একটা রিড + একটা রাইট**, আলাদা ইঞ্জিনে। এখন ডিফল্ট `memory://` (single-process cPanel/PythonAnywhere-এ Flask-Limiter-এর সুপারিশকৃত)। মাল্টি-ওয়ার্কার হলে `RATELIMIT_STORAGE_URI` এনভায়রনমেন্ট ভেরিয়েবল দিয়ে আগের DB স্টোরে ফেরা যাবে।

---

## ৬. ফলাফল (মাপা সংখ্যা)

`perf_after.js` (Chromium, ঠান্ডা ক্যাশ, ১৪৪০×৯০০):

| পেজ | DCL | load | networkidle | **তারেতে (gzip)** | ডিকোড করা | রিকোয়েস্ট |
|---|---|---|---|---|---|---|
| `index.html` (লগইন) | ৯১ ms | ১০৭ ms | ৬০৮ ms | **২৭ KB** | ১৩৬ KB | ১২ |
| `leads.html` | ৭০ ms | ৯৪ ms | ৬৩২ ms | **৬৬ KB** | ২৮৬ KB | ১৯ |
| `dashboard.html` | ৮০ ms | ৯৮ ms | ৬৩৮ ms | **১০৭ KB** | ৩৬৪ KB | ২০ |
| `events.html` | ৬৫ ms | ১০০ ms | ৭২৭ ms | **১১৯ KB** | ৪৪৯ KB | ১৭ |
| `settings.html` | ৯৯ ms | ১৫৬ ms | ৬৭৯ ms | **৬৮ KB** | ২৩৮ KB | ২৭ |

**আগে / পরে:**

| মেট্রিক | আগে | পরে | পরিবর্তন |
|---|---|---|---|
| নেটওয়ার্কে ডেটা (প্রতি পেজ) | ৭০০–৭৫০ KB | ৬৬–১১৯ KB | **−৮৩% … −৯১%** |
| লগইন পেজ | ~১ MB (৩৯৮ + ৬০৩ + ফন্ট) | ২৭ KB | **−৯৭%** |
| dashboard.html DCL | ২৫৯ ms | ৮০ ms | **−৬৯%** |
| events.html DCL | ২৭৭ ms | ৬৫ ms | **−৭৭%** |
| থার্ড-পার্টি CDN ডিপেন্ডেন্সি | ৩টা হোস্ট | **০** (শুধু ফন্ট, নন-ব্লকিং) | — |

> `networkidle` কম কমেছে (৮৩৪→৬৩৮ ms) কারণ পেজগুলো প্রতি কয়েক সেকেন্ডে API পোল করে — সেটা ব্যাকএন্ডের আচরণ, অ্যাসেট লোডিং নয়।

---

## ৭. টেস্ট ফলাফল

| স্যুট | ফলাফল |
|---|---|
| `smoke_test.py` (API) | **১০৯ / ১০৯ পাস** |
| `test_events_facebook.py` (events + Facebook) | **৪৪ / ৪৪ পাস** |
| `e2e2.js` (Playwright UI) | **১৭ / ১৭ পাস** |
| `auth_401_test.js` (নতুন — লগইন হার্ডেনিং) | **৬ / ৬ পাস** |
| `sandbox_test.js` + `sandbox_session.js` | লগইন সফল, সেশন টিকে থাকে, ০ কনসোল এরর |
| `crawl4.js` (২৭টা পেজ, অ্যাডমিন) | **০ কনসোল এরর**, কোনো পেজ খালি/বাউন্স হয়নি |
| `repro_login.js` / `find401.js` | লগইন ঠিক, ২৩ পেজে ০ non-2xx |
| **মোট** | **১৭৬ / ১৭৬** (আগের ১৭০ + নতুন ৬) |

> **নোট:** `smoke_test.py` চালানোর আগে `reset_db.py` চালানো লাগবে — পুরোনো ডেটা থাকলে ডুপ্লিকেট-লিড ৪০৯ আসে (এটা টেস্টের পুরোনো সীমাবদ্ধতা, এই রাউন্ডের রিগ্রেশন নয়)।
> `e2e2.js`-এর একটা assertion ঠিক করা হয়েছে: demo form import **idempotent** — দ্বিতীয়বার চালালে প্রশ্ন সংখ্যা বাড়ে না, তাই `qAfter > qBefore` এর বদলে `qAfter >= qBefore`।

---

## ৮. ফাইল-পরিবর্তনের তালিকা

**নতুন:**
- `backend/app/static/assets/js/crm-store.js` — storage + form shim (সব পেজের `<head>`-এ প্রথম স্ক্রিপ্ট)
- `backend/app/static/assets/css/tailwind.css` — প্রি-কম্পাইলড Tailwind (৪৯ KB)
- `backend/app/static/assets/vendor/chart.umd.min.js` — self-hosted Chart.js
- `backend/app/static/assets/vendor/fullcalendar.global.min.js` — self-hosted FullCalendar
- `backend/app/utils/compression.py` — gzip + cache headers
- `backend/tools/tailwind.config.js`, `backend/tools/build-tailwind.sh` — CSS রিবিল্ড

**পরিবর্তিত:**
- `backend/app/__init__.py` — `/assets/*` CORS, gzip middleware, `memory://` rate-limit store, per-request log → debug
- `backend/app/static/assets/js/sidebar.js` — ৪০১ হ্যান্ডলার নরম করা
- ২৭টা HTML পেজ — `crm-store.js` ইনজেকশন, Tailwind CDN → লোকাল CSS, jsDelivr → `/assets/vendor/` + `defer`, ফন্ট নন-ব্লকিং
- `index.html` — three.js ও ডেড অ্যানিমেশন কোড বাদ
- `dashboard.html`, `reports.html`, `analytics.html` — `Chart.defaults` কল `DOMContentLoaded`-এ

**অপরিবর্তিত (ইচ্ছাকৃত):** কোনো UI, রঙ, লেআউট বা ফিচার বদলানো হয়নি — শুধু লোডিং পথ ও অথ হ্যান্ডলিং।

---

## ৯. আগামীতে খেয়াল রাখার বিষয়

1. **Tailwind রিবিল্ড:** HTML/JS-এ নতুন ক্লাস → `backend/tools/build-tailwind.sh`।
2. **Vendor আপডেট:** Chart.js / FullCalendar আপগ্রেড করতে `/assets/vendor/`-এর ফাইল বদলে দিলেই হবে (পেজে কিছু বদলাতে হবে না)।
3. **মাল্টি-ওয়ার্কার হলে:** `RATELIMIT_STORAGE_URI` সেট করে DB-ব্যাকড লিমিটার ব্যবহার করুন।
4. **`memory://` লিমিটার:** রিস্টার্টে কাউন্টার রিসেট হয় — ডেভে সুবিধাজনক, প্রোডাকশনে সচেতন থাকুন।
5. `TEST_REPORT.md`-এর পুরোনো ফ্ল্যাগগুলো এখনো প্রযোজ্য (যেমন `/api/settings/*` GET-এ প্লেইনটেক্সট সিক্রেট, demo-connect credential) — এই রাউন্ডে অপরিবর্তিত।
