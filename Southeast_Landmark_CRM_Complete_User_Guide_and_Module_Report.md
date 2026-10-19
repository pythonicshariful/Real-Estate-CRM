# 📘 Southeast Landmark CRM v2.0 — Architecture, Module URL Directory & Operational Manual

**Client:** Southeast Landmark Ltd.  
**System Version:** v2.0 (High-Performance Production Release)  
**Architecture Reference:** `Southeast_Landmark_CRM_v1_Architecture.pdf`  
**Live Production Host:** [https://southeastlandmark.pythonicshariful.tech/](https://southeastlandmark.pythonicshariful.tech/)  
**Local Development Host:** `http://localhost:5000/`  
**Printable Browser Manual:** [https://southeastlandmark.pythonicshariful.tech/manual.html](https://southeastlandmark.pythonicshariful.tech/manual.html)

---

## 📑 সূচিপত্র (Table of Contents)

1. [সিস্টেম পরিচিতি ও মূল স্থাপত্য নীতি (Core Architectural Principles)](#1-সিস্টেম-পরিচিতি-ও-মূল-স্থাপত্য-নীতি)
2. [মাস্টার URL ডিরেক্টরি (Quick Navigation Matrix)](#2-মাস্টার-url-ডিরেক্টরি)
3. [Section A: পাইপলাইনের ১৫টি স্টেজ ও ৫টি এক্সিট গেট](#3-section-a-পাইপলাইনের-১৫টি-স্টেজ-ও-৫টি-এক্সিট-গেট)
4. [Section B: আর্কিটেকচারের ১২টি মূল মডিউল (M-01 to M-12)](#4-section-b-আর্কিটেকচারের-১২টি-মূল-মডিউল)
   - [M-01: Multi-Channel Lead Intake & Instant Capture](#m-01-multi-channel-lead-intake--instant-capture)
   - [M-02: Contact Identity, De-duplication & Client Pool](#m-02-contact-identity-de-duplication--client-pool)
   - [M-03: Dynamic Lead Scoring & Qualification Matrix (BANT)](#m-03-dynamic-lead-scoring--qualification-matrix)
   - [M-04: Smart Lead Distribution & 15-Minute SLA Engine](#m-04-smart-lead-distribution--15-minute-sla-engine)
   - [M-05: Telephony & Multi-Channel Communications Suite](#m-05-telephony--multi-channel-communications-suite)
   - [M-06: Task & Follow-up Management Engine](#m-06-task--follow-up-management-engine)
   - [M-07: Site Visit Lifecycle & Logistics Manager (Debrief Gate)](#m-07-site-visit-lifecycle--logistics-manager)
   - [M-08: Objection Intelligence & Resolution Engine](#m-08-objection-intelligence--resolution-engine)
   - [M-09: Inventory, Plot Master & Unit Reservation](#m-09-inventory-plot-master--unit-reservation)
   - [M-10: Sales Transaction, Invoicing & Collections](#m-10-sales-transaction-invoicing--collections)
   - [M-11: Reports & Analytics (Core 20-KPI Framework)](#m-11-reports--analytics)
   - [M-12: Post-Handover CRM, Customer Service & Tickets](#m-12-post-handover-crm--customer-service)
5. [Section C: রোল ও পারমিশন ম্যাট্রিক্স (RBAC Safeguards)](#5-section-c-রোল-ও-পারমিশন-ম্যাট্রিক্স)
6. [Section D: ২০টি কোর কেপিআই অ্যানালিটিক্স ব্যাখ্যা](#6-section-d-২০টি-কোর-কেপিআই-অ্যানালিটিক্স)
7. [অপারেশনাল নির্দেশিকা ও টিপস (Best Practices)](#7-অপারেশনাল-নির্দেশিকা-ও-টিপস)

---

## 1. সিস্টেম পরিচিতি ও মূল স্থাপত্য নীতি

`Southeast Landmark CRM v2.0` রিয়েল এস্টেট ল্যান্ড ও প্লট বিক্রয়ের বিশেষ বাণিজ্যিক চাহিদার উপর ভিত্তি করে প্রস্তুত করা হয়েছে। `Southeast_Landmark_CRM_v1_Architecture.pdf` নীতিমালার আলোকে এটি নির্মিত:

1. **১টি কন্টাক্ট ➔ একাধিক অপরচুনিটি মডেল (1:N Architecture):**  
   একই গ্রাহক একাধিক প্রজেক্টে বা ভবিষ্যতে নতুন প্লট কিনতে পারেন। সিস্টেমে গ্রাহকের মূল পরিচিতি (`Contact`) একবারই সংরক্ষিত থাকে এবং প্রতিটি নতুন আগ্রহ আলাদা `Opportunity` হিসেবে ট্র্যাক করা হয়। পুরাতন ইতিহাস কখনো মুছে যায় না।
2. **জিরো লিড ওভাররাইট (Zero Data Loss):**  
   কোনো লিড ডুপ্লিকেট হলে বা পুনরায় যোগাযোগ করলে পূর্বের ডাটা কখনো ওভাররাইট হয় না; বরং নতুন সাব-ইনকোয়ারি তৈরি হয়।
3. **১৫ মিনিটের স্পিড-টু-লিড SLA (Speed-to-Lead SLA):**  
   ডিজিটাল চ্যানেল (ফেসবুক এডস, ওয়েবসাইট) থেকে লিড সিস্টেমে আসার ১৫ মিনিটের মধ্যে প্রথম কল সম্পন্ন করার স্বয়ংক্রিয় কাউন্টডাউন টাইমার ও এস্কেলেশন প্রোটোকল।
4. **পোস্ট-ভিজিট ডিব্রিফ গেট (Fix 4 - Debrief Gate):**  
   সাইট ভিজিট সম্পন্ন হওয়ার পর ক্লায়েন্টের প্রতিক্রিয়া বা মতামত (Debrief Form) সাবমিট না করা পর্যন্ত সিস্টেম প্রপোজাল তৈরি বা নেগোসিয়েশন স্টেজে লিড সরাতে দেয় না।
5. **বাধ্যতামূলক এক্সিট রিজন কোড (Mandatory Exit Reason Codes):**  
   কোনো লিড যদি হারিয়ে যায় (`CLOSED_LOST`), অন্য কোথাও কিনে নেয় (`BOUGHT_ELSEWHERE`) বা অপ্রয়োজনীয় হয় (`INVALID`), তবে ড্রপডাউন থেকে কারণ সিলেক্ট এবং কমেন্ট প্রদান বাধ্যতামূলক।

---

## 2. মাস্টার URL ডিরেক্টরি

| # | মডিউল ও পেজের নাম | সরাসরি লাইভ লিঙ্ক (Production Host) | লোকাল লিঙ্ক (Localhost) | প্রাথমিক ব্যবহারকারী |
| :- | :--- | :--- | :--- | :--- |
| **00** | **ইউজার লগইন পোর্টাল** | [index.html](https://southeastlandmark.pythonicshariful.tech/index.html) | `http://localhost:5000/index.html` | All Roles |
| **01** | **এডমিন কমান্ড সেন্টার** | [admin-dashboard.html](https://southeastlandmark.pythonicshariful.tech/admin-dashboard.html) | `http://localhost:5000/admin-dashboard.html` | Admin, CEO, GM |
| **02** | **সেলস এক্সিকিউটিভ ড্যাশবোর্ড** | [dashboard.html](https://southeastlandmark.pythonicshariful.tech/dashboard.html) | `http://localhost:5000/dashboard.html` | Sales Executive, Manager |
| **03** | **১৫-স্টেজ কানবান পাইপলাইন** | [pipeline.html](https://southeastlandmark.pythonicshariful.tech/pipeline.html) | `http://localhost:5000/pipeline.html` | Sales Executive, Manager |
| **04** | **লিডস হাব (সক্রিয় লিড তালিকা)** | [leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) | `http://localhost:5000/leads.html` | All Roles |
| **05** | **লিড ডিটেইলস ও টাইমলাইন ভিউ** | [lead-details.html](https://southeastlandmark.pythonicshariful.tech/lead-details.html) | `http://localhost:5000/lead-details.html` | All Roles |
| **06** | **ক্লায়েন্ট ও কন্টাক্ট ডিরেক্টরি** | [contacts.html](https://southeastlandmark.pythonicshariful.tech/contacts.html) | `http://localhost:5000/contacts.html` | All Roles |
| **07** | **প্রস্পেক্টস পুল (Prospects)** | [prospects.html](https://southeastlandmark.pythonicshariful.tech/prospects.html) | `http://localhost:5000/prospects.html` | Sales Team |
| **08** | **টিম ও ক্যাপাসিটি ম্যানেজমেন্ট** | [team.html](https://southeastlandmark.pythonicshariful.tech/team.html) | `http://localhost:5000/team.html` | Admin, Manager |
| **09** | **লিড ওনার্স ও বণ্টন কন্ট্রোল** | [lead-owners.html](https://southeastlandmark.pythonicshariful.tech/lead-owners.html) | `http://localhost:5000/lead-owners.html` | Admin, Manager |
| **10** | **মেসেজ ও ওমনিচ্যানেল ইনবক্স** | [messages.html](https://southeastlandmark.pythonicshariful.tech/messages.html) | `http://localhost:5000/messages.html` | Sales Team |
| **11** | **কল ও অ্যাক্টিভিটি হিস্ট্রি লগ** | [activities.html](https://southeastlandmark.pythonicshariful.tech/activities.html) | `http://localhost:5000/activities.html` | Manager, Admin |
| **12** | **টাস্ক ও ফলো-আপ ইঞ্জিন** | [tasks.html](https://southeastlandmark.pythonicshariful.tech/tasks.html) | `http://localhost:5000/tasks.html` | Sales Executive |
| **13** | **সাইট ভিজিট ও ইভেন্টস ক্যালেন্ডার** | [events.html](https://southeastlandmark.pythonicshariful.tech/events.html) | `http://localhost:5000/events.html` | All Roles |
| **14** | **অবজেকশন ও সেলস নোটস** | [notes.html](https://southeastlandmark.pythonicshariful.tech/notes.html) | `http://localhost:5000/notes.html` | Sales Team |
| **15** | **প্রজেক্ট ও প্লট ইনভেন্টরি** | [projects.html](https://southeastlandmark.pythonicshariful.tech/projects.html) | `http://localhost:5000/projects.html` | All Roles |
| **16** | **সেলস বুকিং ও ক্লোজিং ডিরেক্টরি** | [sales.html](https://southeastlandmark.pythonicshariful.tech/sales.html) | `http://localhost:5000/sales.html` | Accounts, Admin, Manager |
| **17** | **মার্কেটিং ও মিসলেনিয়াস খরচ** | [expenses.html](https://southeastlandmark.pythonicshariful.tech/expenses.html) | `http://localhost:5000/expenses.html` | Accounts, Admin |
| **18** | **রিপোর্ট ও ২০-কেপিআই অ্যানালিটিক্স** | [reports.html](https://southeastlandmark.pythonicshariful.tech/reports.html) | `http://localhost:5000/reports.html` | Admin, CEO, GM, Manager |
| **19** | **কাস্টমার সাপোর্ট টিকেট ও হ্যান্ডওভার**| [tickets.html](https://southeastlandmark.pythonicshariful.tech/tickets.html) | `http://localhost:5000/tickets.html` | Support, Operations |
| **20** | **সিস্টেম সেটিংস ও ইন্টিগ্রেশন** | [settings.html](https://southeastlandmark.pythonicshariful.tech/settings.html) | `http://localhost:5000/settings.html` | Admin Only |
| **21** | **মেটা ফেসবুক লিড এডস গাইড** | [meta_guide.html](https://southeastlandmark.pythonicshariful.tech/meta_guide.html) | `http://localhost:5000/meta_guide.html` | Admin, Marketing |
| **22** | **ক্লাউড কল অডিও স্টোরেজ গাইড** | [b2_guide.html](https://southeastlandmark.pythonicshariful.tech/b2_guide.html) | `http://localhost:5000/b2_guide.html` | Admin, IT |
| **23** | **প্রিন্ট উপযোগী ইউজার ম্যানুয়াল** | [manual.html](https://southeastlandmark.pythonicshariful.tech/manual.html) | `http://localhost:5000/manual.html` | All Roles |

---

## 3. Section A: পাইপলাইনের ১৫টি স্টেজ ও ৫টি এক্সিট গেট

### ক) ১৫টি লিনিয়ার সেলস স্টেজ (Linear Funnel):
1. `NEW` — ডিজিটাল বিজ্ঞাপন বা ফর্ম থেকে সদ্য আসা নতুন লিড।
2. `ASSIGNED` — রাউন্ড-রবিন ইঞ্জিনের মাধ্যমে নির্দিষ্ট সেলস এক্সিকিউটিভকে বণ্টনকৃত।
3. `FIRST_CONTACT_PENDING` — ১৫ মিনিটের টাইমার সক্রিয়, প্রথম যোগাযোগের অপেক্ষায়।
4. `CONTACT_ATTEMPTED` — কল করা হয়েছে কিন্তু গ্রাহক রিসিভ করেননি (Busy/Ringing)।
5. `CONNECTED` — গ্রাহকের সাথে সফল কথা হয়েছে।
6. `QUALIFIED` — BANT মানদণ্ডে বাজেট, আগ্রহ এবং অথরিটি নিশ্চিত হয়েছে।
7. `APPOINTMENT_SCHEDULED` — প্রজেক্ট সাইট ভিজিট বা মিটিং নির্ধারণ করা হয়েছে।
8. `APPOINTMENT_CONFIRMED` — ভিজিটের আগের দিন বা সকালে গ্রাহক কনফার্ম করেছেন।
9. `VISIT_COMPLETED` — প্রজেক্ট পরিদর্শনে গ্রাহক উপস্থিত হয়েছেন (Debrief Pending)।
10. `PROPOSAL_PRESENTED` — পোস্ট-ভিজিট ডিব্রিফ শেষে আনুষ্ঠানিক কোটেশন/প্লট অফার হস্তান্তর।
11. `NEGOTIATION` — দাম, কিস্তি প্ল্যান ও ডাউন পেমেন্ট নিয়ে দরকষাকষি।
12. `RESERVATION_RECEIVED` — বুকিং মানি বা টোকেন বায়না জমা হয়েছে।
13. `DOCUMENTATION_IN_PROCESS` — এগ্রিমেন্ট ডিড, কেওয়াইসি ও স্ট্যাম্প প্রস্তুতকরণ।
14. `LEGAL_VERIFICATION` — খতিয়ান, নামজারি ও দলিলপত্র আইনগত যাচাই।
15. `SOLD` — দলিল রেজিস্ট্রি বা প্রথম বড় কিস্তি পেয়ে সেল চূড়ান্তভাবে ভেরিফাইড।

### খ) ৫টি বিকল্প এক্সিট গেট (Alternative Exit Paths):
- `CLOSED_LOST` — ডিল বাতিল হয়েছে (বাধ্যতামূলক রিজন কোড: দাম বেশি, বাজেট সংকট, ফ্যামিলি অমত ইত্যাদি)।
- `NURTURE` — দীর্ঘমেয়াদী নার্চারিং পুল (ভবিষ্যতে কেনার সম্ভাবনা আছে, কিন্তু এখন নয়)।
- `BOUGHT_ELSEWHERE` — প্রতিদ্বন্দ্বী অন্য কোনো হাউজিং কোম্পানিতে প্লট কিনে ফেলেছেন।
- `INVALID` — ভুয়া নাম্বার, রং নাম্বার বা অসম্পূর্ণ তথ্য।
- `UNREACHABLE` — বারবার চেষ্টা করার পরও কোনোভাবেই যোগাযোগ সম্ভব হয়নি।

---

## 4. Section B: আর্কিটেকচারের ১২টি মূল মডিউল

### M-01: Multi-Channel Lead Intake & Instant Capture
* **লাইভ URL:** [https://southeastlandmark.pythonicshariful.tech/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html)
* **ইন্টিগ্রেশন গাইড:** [https://southeastlandmark.pythonicshariful.tech/meta_guide.html](https://southeastlandmark.pythonicshariful.tech/meta_guide.html)
* **মূল ফিচারসমূহ:**
  - মেটা ফেসবুক লিড এডস রিয়েল-টাইম ওয়েবহুক (`/api/webhooks/meta`)
  - ওয়েবসাইট ল্যান্ডিং পেজ ফর্ম ইনটেক (`/api/webhooks/website`)
  - এক্সেল/সিএসভি বালক ইম্পোর্ট পোর্টাল
  - ম্যানুয়াল কুইক লিড এন্ট্রি বাটন
* **কিভাবে ব্যবহার করবেন:**
  1. `Leads Hub` পেজে গিয়ে উপরে ডানে **+ Add Lead** বাটনে ক্লিক করুন।
  2. ক্লায়েন্টের নাম, মোবাইল নাম্বার, পেশা, পছন্দের প্রজেক্ট ও সম্ভাব্য বাজেট ইনপুট দিয়ে সেভ করুন।
  3. একাধিক লিড একসাথে আপলোড করতে **Import CSV** বাটনে ক্লিক করে ফাইলটি সিলেক্ট করুন।

---

### M-02: Contact Identity, De-duplication & Client Pool
* **লাইভ URL:** [https://southeastlandmark.pythonicshariful.tech/contacts.html](https://southeastlandmark.pythonicshariful.tech/contacts.html)
* **মূল ফিচারসমূহ:**
  - ফোন নাম্বার ও ইমেইল দিয়ে ইনস্ট্যান্ট অটো-মার্জিং ও ডুপ্লিকেট চেকার।
  - ১ জন গ্রাহকের আন্ডারে তার অতীতের সমস্ত ভিজিট, কল ও বুকিং হিস্ট্রি সংরক্ষণ।
* **কিভাবে ব্যবহার করবেন:**
  1. বাম পাশের সাইডবার থেকে **Contacts** মেনুতে ক্লিক করুন।
  2. সার্চ বারে গ্রাহকের ফোন নাম্বার লিখুন। সিস্টেমে গ্রাহক পূর্বে উপস্থিত থাকলে তার পুরো হিস্ট্রি প্রোফাইল ওপেন হবে।

---

### M-03: Dynamic Lead Scoring & Qualification Matrix (BANT)
* **লাইভ URL:** [https://southeastlandmark.pythonicshariful.tech/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html)
* **মূল ফিচারসমূহ:**
  - BANT (Budget, Authority, Need, Timeline) ফ্রেমওয়ার্ক।
  - ৪টি অটোমেটেড প্রায়োরিটি লেভেল: `URGENT`, `HIGH`, `MEDIUM`, `LOW`।
  - লিড টেম্পারেচার: `HOT`, `WARM`, `COLD`।
* **কিভাবে ব্যবহার করবেন:**
  1. লিড কার্ডের **Qualify** বাটনে ক্লিক করুন।
  2. বাজেটের উৎস, সিদ্ধান্ত গ্রহণকারী কে, প্লট কেনার নির্দিষ্ট সময়সীমা সিলেক্ট করুন।
  3. সিস্টেম স্বয়ংক্রিয়ভাবে ১০০-তে স্কোর হিসাব করবে এবং লিডটি হাই প্রায়োরিটিতে চলে যাবে।

---

### M-04: Smart Lead Distribution & 15-Minute SLA Engine
* **লাইভ URL:** [https://southeastlandmark.pythonicshariful.tech/lead-owners.html](https://southeastlandmark.pythonicshariful.tech/lead-owners.html) ও [team.html](https://southeastlandmark.pythonicshariful.tech/team.html)
* **মূল ফিচারসমূহ:**
  - ক্যাপাসিটি ব্যালেন্সড রাউন্ড-রবিন অ্যালগরিদম।
  - ১৫ মিনিটের কাউন্টডাউন টাইমার (১০ মিনিটে হলুদ ওয়ার্নিং, ১৫ মিনিটে লাল ব্রিচ, ২০ মিনিটে ম্যানেজার এস্কেলেশন)।
  - অন-ডিউটি / অফ-ডিউটি সেলস রিপ্রেজেন্টেটিভ টগল।
* **কিভাবে ব্যবহার করবেন:**
  1. নতুন লিড আসলে সেলস এক্সিকিউটিভের স্ক্রিনে ১৫ মিনিটের লাল/সবুজ টাইমার চালু হবে।
  2. ১৫ মিনিট পার হওয়ার পূর্বে গ্রাহককে কল করে আউটকাম লগ করলেই SLA Compliant হিসেবে মার্ক হয়ে যাবে।

---

### M-05: Telephony & Multi-Channel Communications Suite
* **লাইভ URL:** [https://southeastlandmark.pythonicshariful.tech/messages.html](https://southeastlandmark.pythonicshariful.tech/messages.html) ও [activities.html](https://southeastlandmark.pythonicshariful.tech/activities.html)
* **মূল ফিচারসমূহ:**
  - ১-ক্লিক কল ডায়ালার (`tel:` প্রোটোকল)।
  - কল রেজাল্ট লগিং (Connected, Busy, Switched Off, Ringing, Wrong Number)।
  - কল রেকর্ডিং অডিও প্লেয়ার ও ক্লাউড স্টোরেজ সাপোর্ট।
  - হোয়াটসঅ্যাপ মেসেজ টেমপ্লেট।
* **কিভাবে ব্যবহার করবেন:**
  1. যেকোনো লিড কার্ডের **Call** আইকনে চাপ দিন।
  2. কথা বলা শেষ হলে পপআপ বক্সে `Connected` সিলেক্ট করে আলোচনার সারসংক্ষেপ ২ লাইনে লিখে সেভ করুন।

---

### M-06: Task & Follow-up Management Engine
* **লাইভ URL:** [https://southeastlandmark.pythonicshariful.tech/tasks.html](https://southeastlandmark.pythonicshariful.tech/tasks.html)
* **মূল ফিচারসমূহ:**
  - নেক্সট অ্যাকশন ডেডলাইন (Next Action Deadline) ট্র্যাকার।
  - Overdue (সময় পার হয়ে যাওয়া) লাল এলার্ট।
  - আজকের করণীয় কাজের তালিকা।
* **কিভাবে ব্যবহার করবেন:**
  1. **Tasks** পেজে প্রবেশ করুন। 
  2. `Today's Follow-ups` ট্যাব থেকে নির্ধারিত গ্রাহকদের ফোন দিন এবং সম্পন্ন হলে চেকবক্সে টিক দিন।

---

### M-07: Site Visit Lifecycle & Logistics Manager (Debrief Gate)
* **লাইভ URL:** [https://southeastlandmark.pythonicshariful.tech/events.html](https://southeastlandmark.pythonicshariful.tech/events.html) ও [lead-details.html](https://southeastlandmark.pythonicshariful.tech/lead-details.html)
* **মূল ফিচারসমূহ:**
  - প্রজেক্ট সাইট ভিজিট শিডিউলিং।
  - পরিবহন ও ড্রাইভার নির্ধারণ।
  - **Debrief Gate:** গ্রাহক ভিজিট শেষ করলে ডিব্রিফ ফর্ম পূরণ করা ছাড়া ডিল পরবর্তী স্টেজে যাবে না।
* **কিভাবে ব্যবহার করবেন:**
  1. লিড কার্ডে **Book Visit** চাপুন। প্রজেক্ট ও তারিখ সিলেক্ট করে পিকআপ পয়েন্ট দিন।
  2. ভিজিট শেষ হলে লিডের ডিটেইলস পেজে গিয়ে **Post-Visit Debrief** বাটনে ক্লিক করে ক্লায়েন্টের মতামত লিখে সেভ করুন।

---

### M-08: Objection Intelligence & Resolution Engine
* **লাইভ URL:** [https://southeastlandmark.pythonicshariful.tech/notes.html](https://southeastlandmark.pythonicshariful.tech/notes.html)
* **মূল ফিচারসমূহ:**
  - ৮টি অবজেকশন ক্যাটাগরি (Price, Location, Legality/Documents, Installment, Comparison, Trust, Family, Timeline)।
  - প্রতিটি ক্যাটাগরির জন্য প্রশিক্ষিত সেলস কাউন্টার আর্গুমেন্ট ও টিপস।
* **কিভাবে ব্যবহার করবেন:**
  1. গ্রাহক কোনো আপত্তি জানালে **Log Objection** বাটনে ক্লিক করুন।
  2. স্ক্রিনে আসা সেলস টক-ট্র্যাক দেখে গ্রাহককে আশ্বস্ত করার পয়েন্টগুলো মিলিয়ে কথা বলুন।

---

### M-09: Inventory, Plot Master & Unit Reservation
* **লাইভ URL:** [https://southeastlandmark.pythonicshariful.tech/projects.html](https://southeastlandmark.pythonicshariful.tech/projects.html)
* **মূল ফিচারসমূহ:**
  - প্রজেক্টের ব্লক, সেক্টর ও প্লট সাইজ (৩ কাঠা, ৫ কাঠা, ১০ কাঠা)।
  - প্লট স্ট্যাটাস: `AVAILABLE`, `BLOCKED`, `RESERVED`, `SOLD`।
  - ডাবল-সেল রোধে ইনস্ট্যান্ট ব্লক প্রটেকশন।
* **কিভাবে ব্যবহার করবেন:**
  1. **Projects** পেজে গিয়ে নির্দিষ্ট প্রজেক্টে ক্লিক করুন।
  2. খালি (সবুজ চিহ্নিত) প্লট সিলেক্ট করে গ্রাহকের লিডের সাথে লিঙ্ক করে **Reserve Unit** করুন।

---

### M-10: Sales Transaction, Invoicing & Collections
* **লাইভ URL:** [https://southeastlandmark.pythonicshariful.tech/sales.html](https://southeastlandmark.pythonicshariful.tech/sales.html) ও [expenses.html](https://southeastlandmark.pythonicshariful.tech/expenses.html)
* **মূল ফিচারসমূহ:**
  - ডিল ক্লোজিং ভ্যালু ও পেমেন্ট শিডিউল জেনারেটর (এককালীন ও কিস্তি)।
  - মানি রিসিট ও ইনভয়েস স্ট্যাটাস (`PAID`, `SENT`, `OVERDUE`)।
  - মার্কেটিং খরচের অনুমোদন ও সিএসি (CAC) হিসাব।
* **কিভাবে ব্যবহার করবেন:**
  1. ডিল ফাইনাল হলে **Record Sale** বাটনে ক্লিক করুন।
  2. মোট বিক্রয় মূল্য, বুকিং মানি এবং কিস্তির সংখ্যা দিয়ে ইনভয়েস ইস্যু করুন।

---

### M-11: Reports & Analytics (Core 20-KPI Framework)
* **লাইভ URL:** [https://southeastlandmark.pythonicshariful.tech/reports.html](https://southeastlandmark.pythonicshariful.tech/reports.html)
* **মূল ফিচারসমূহ:**
  - ২০টি লাইভ কেপিআই কার্ড (স্পিড, কন্টাক্ট রেট, শো-রেট, কনভার্সন, সিএসি)।
  - ৬টি ট্রেন্ড ও ডিস্ট্রিবিউশন চার্ট।
  - ০-মিলি-সেকেন্ড ইনস্ট্যান্ট পেজ রেন্ডারিং ও ব্যাকএন্ড মেমোরি ক্যাশ।
* **কিভাবে ব্যবহার করবেন:**
  1. **Reports** মেনুতে ক্লিক করুন। পুরো কোম্পানির রিয়েল-টাইম পারফরম্যান্স কার্ড ও গ্রাফে দেখতে পাবেন।
  2. নির্দিষ্ট সময়সীমার ডাটা দেখতে চাইলে উপরে ডেট ফিল্টার ব্যবহার করুন।

---

### M-12: Post-Handover CRM, Customer Service & Tickets
* **লাইভ URL:** [https://southeastlandmark.pythonicshariful.tech/tickets.html](https://southeastlandmark.pythonicshariful.tech/tickets.html)
* **মূল ফিচারসমূহ:**
  - দলিল হস্তান্তর, সীমানা নির্ধারণ ও নামজারি বিষয়ক কাস্টমার সাপোর্ট টিকেট।
  - টিকেট স্ট্যাটাস: `OPEN`, `IN_PROGRESS`, `RESOLVED`।
* **কিভাবে ব্যবহার করবেন:**
  1. গ্রাহক কোনো সার্ভিসের জন্য যোগাযোগ করলে **+ New Ticket** চাপুন।
  2. সমস্যার ধরন লিখে সংশ্লিষ্ট অফিসারকে এসাইন করুন।

---

## 5. Section C: রোল ও পারমিশন ম্যাট্রিক্স (RBAC Safeguards)

| মেনু / ফিচার | Sales Executive | Sales Manager | General Manager / CEO | System Admin |
| :--- | :---: | :---: | :---: | :---: |
| **নিজের এসাইনকৃত লিড দেখা ও কল করা** |  Full |  Full |  Full |  Full |
| **অন্য এক্সিকিউটিভের লিড দেখা** |  Blocked |  Full (Team) |  Full |  Full |
| **লিড নতুন এক্সিকিউটিভকে রি-এসাইন করা**|  Blocked |  Allowed |  Allowed |  Allowed |
| **কোম্পানির মোট সেলস ও সিএসি রিপোর্ট দেখা**|  Limited |  Team Only |  Full |  Full |
| **লিড ডাটা এক্সেল/CSV এক্সপোর্ট** |  Blocked |  Blocked |  Allowed |  Allowed |
| **সিস্টেম সেটিংস ও SLA রুলস পরিবর্তন**|  Blocked |  Blocked |  Blocked |  Full |

---

## 6. Section D: ২০টি কোর কেপিআই অ্যানালিটিক্স ব্যাখ্যা

1. **Speed-to-Lead:** নতুন লিড সৃষ্টি থেকে প্রথম কলের গড় সময় (আদর্শ: ১৫ মিনিটের নিচে)।
2. **SLA Compliance:** নির্ধারিত সময়ের মধ্যে প্রথম কল হওয়া লিডের শতকরা হার।
3. **Contact Rate:** মোট কল চেষ্টার মধ্যে সফলভাবে সংযুক্ত হওয়ার হার।
4. **Qualification Rate:** সংযুক্ত গ্রাহকদের মধ্যে বাজেট ও আগ্রহ যাচাইকৃত হার।
5. **Appointment Booking Rate:** কোয়ালিফাইড লিডদের মধ্যে সাইট ভিজিট বুকিংয়ের হার।
6. **Confirmation Rate:** বুককৃত ভিজিটের মধ্যে চূড়ান্তভাবে কনফার্ম হওয়া হার।
7. **Show Rate:** কনফার্মকৃত ভিজিটের মধ্যে স্বশরীরে উপস্থিতির হার।
8. **Visit-to-Negotiation Rate:** সাইট ভিজিটের পর দরকষাকষিতে পৌঁছানোর হার।
9. **Visit-to-Reservation Rate:** সাইট ভিজিট থেকে টোকেন বায়না পাওয়ার অনুপাত।
10. **Reservation-to-Sale Rate:** বায়না থেকে পূর্ণাঙ্গ দলিল রেজিস্ট্রির সাফল্য হার।
11. **Follow-Up Compliance:** সঠিক সময়ে নিয়মিত ফলো-আপ নিষ্পত্তির হার।
12. **Lead Aging Heatmap:** ১, ৩, ৭, ১৪ ও ৩০+ দিন অপরিবর্তিত পড়ে থাকা লিড সংখ্যা।
13. **Reactivation Rate:** দীর্ঘদিনের নার্চার পুল থেকে পুনরায় সক্রিয় হওয়া লিডের হার।
14. **Closed-Lost Rate:** অকৃতকার্য হওয়া লিডের কারণভিত্তিক শতকরা হার।
15. **Average Sales Cycle:** প্রথম ইনকোয়ারি থেকে রেজিস্ট্রেশন পর্যন্ত গড় দিন সংখ্যা।
16. **Revenue per 100 Leads:** প্রতি ১০০টি লিড জেনারেশন বাবদ অর্জিত মোট বিক্রয় মূল্য।
17. **Collection Rate:** মোট ডিউ ইনভয়েস মূল্যের বিপরীতে আদায়কৃত টাকার হার।
18. **Source Conversion Rate:** বিজ্ঞাপন চ্যানেলভেদে বিক্রয়ের সাফল্য অনুপাত।
19. **Cost per Completed Visit:** সম্পন্ন প্রতিটি সাইট ভিজিটে কোম্পানির গড় মার্কেটিং ব্যয়।
20. **Customer Acquisition Cost (CAC):** প্রতি গ্রাহক আনতে মোট বিপণন ও বিক্রয় ব্যয়।

---

## 7. অপারেশনাল নির্দেশিকা ও টিপস

* **প্রতিদিন সকালে:** সেলস এক্সিকিউটিভরা তাদের [Workspace Dashboard](https://southeastlandmark.pythonicshariful.tech/dashboard.html) ওপেন করে `Today's Follow-ups` দেখে কাজ শুরু করবেন।
* **কল করার পরপরই:** কল ব্যাক করার কথা থাকলে সাথে সাথে [Next Action Deadline](https://southeastlandmark.pythonicshariful.tech/tasks.html) সেট করবেন, যাতে সিস্টেম অটোমেটিক রিমাইন্ডার দেয়।
* **সাইট ভিজিটের পর:** ক্লায়েন্টকে গাড়ি থেকে বিদায় দিয়ে অফিসে ফিরেই [Post-Visit Debrief](https://southeastlandmark.pythonicshariful.tech/lead-details.html) পূরণ করবেন, যাতে কোটেশন তৈরি লক না হয়ে থাকে।
* **ম্যানেজারদের জন্য:** প্রতিদিন বিকেলে [Lead Owners Page](https://southeastlandmark.pythonicshariful.tech/lead-owners.html) থেকে টিমের লিড ক্যাপাসিটি চেক করে প্রয়োজন অনুযায়ী লিড পুনর্বণ্টন করবেন।
