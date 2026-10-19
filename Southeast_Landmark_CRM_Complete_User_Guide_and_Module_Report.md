# 📘 Southeast Landmark CRM v2.0 — Architecture Compliance Audit, Module URL Directory & Operational Manual

**System:** Southeast Landmark CRM v2.0  
**Specification:** Architecture Reference v2.0 (`Southeast_Landmark_CRM_v1_Architecture.pdf`)  
**Portal Access:** [https://southeastlandmark.pythonicshariful.tech/](https://southeastlandmark.pythonicshariful.tech/)  
**System Manual:** [https://southeastlandmark.pythonicshariful.tech/manual.html](https://southeastlandmark.pythonicshariful.tech/manual.html)

---

## 📑 সূচিপত্র (Table of Contents)

1. [মূল স্থাপত্য নীতি ও ওভারভিউ](#1-মূল-স্থাপত্য-নীতি-ও-ওভারভিউ)
2. [মাস্টার URL ও পেজ অ্যাক্সেস ডিরেক্টরি](#2-মাস্টার-url-ও-পেজ-অ্যাক্সেস-ডিরেক্টরি)
3. [Section A: ১৫টি সেলস স্টেজ ও ৫টি এক্সিট গেট](#3-section-a-১৫টি-সেলস-স্টেজ-ও-৫টি-এক্সিট-গেট)
4. [Section B: ১২টি কোর আর্কিটেকচার মডিউল (M-01 থেকে M-12)](#4-section-b-১২টি-কোর-আর্কিটেকচার-মডিউল-m-01-থেকে-m-12)
   - [M-01: Multi-Channel Lead Intake & Instant Capture](#m-01-multi-channel-lead-intake--instant-capture)
   - [M-02: Contact Identity, De-duplication & Client Pool](#m-02-contact-identity-de-duplication--client-pool)
   - [M-03: Dynamic Lead Scoring & Qualification Matrix (BANT)](#m-03-dynamic-lead-scoring--qualification-matrix-bant)
   - [M-04: Smart Lead Distribution & 15-Minute SLA Engine](#m-04-smart-lead-distribution--15-minute-sla-engine)
   - [M-05: Telephony & Multi-Channel Communications Suite](#m-05-telephony--multi-channel-communications-suite)
   - [M-06: Task & Follow-up Management Engine](#m-06-task--follow-up-management-engine)
   - [M-07: Site Visit Lifecycle & Logistics Manager (Debrief Gate)](#m-07-site-visit-lifecycle--logistics-manager-debrief-gate)
   - [M-08: Objection Intelligence & Resolution Engine](#m-08-objection-intelligence--resolution-engine)
   - [M-09: Inventory, Plot Master & Unit Reservation](#m-09-inventory-plot-master--unit-reservation)
   - [M-10: Sales Transaction, Invoicing & Collections](#m-10-sales-transaction-invoicing--collections)
   - [M-11: Reports & Analytics (Core 20-KPI Framework)](#m-11-reports--analytics-core-20-kpi-framework)
   - [M-12: Post-Handover CRM, Customer Service & Tickets](#m-12-post-handover-crm-customer-service--tickets)
5. [Section C: আর্কিটেকচারের ৫টি ক্রিটিক্যাল ডিজাইন ফিক্স](#5-section-c-আর্কিটেকচারের-৫টি-ক্রিটিক্যাল-ডিজাইন-ফিক্স)
6. [Section D: ২০টি কোর কেপিআই অ্যানালিটিক্স ম্যাট্রিক্স](#6-section-d-২০টি-কোর-কেপিআই-অ্যানালিটিক্স-ম্যাট্রিক্স)
7. [Section E: ১৭টি সিকিউরিটি ও আরবিএসি কন্ট্রোল](#7-section-e-১৭টি-সিকিউরিটি-ও-আরবিএসি-কন্ট্রোল)
8. [সার্ভার ডিপ্লয়মেন্ট প্রোটোকল](#8-সার্ভার-ডিপ্লয়মেন্ট-প্রোটোকল)

---

## 1. মূল স্থাপত্য নীতি ও ওভারভিউ

`Southeast Landmark CRM v2.0` সিস্টেমটি `Southeast_Landmark_CRM_v1_Architecture.pdf`-এর বাণিজ্যিক ও প্রযুক্তিগত শর্তাবলীর সাথে পুরোপুরি সঙ্গতিপূর্ণ রেখে প্রস্তুত করা হয়েছে:

1. **১টি কন্টাক্ট ➔ একাধিক অপরচুনিটি মডেল (1:N Architecture):**  
   একই গ্রাহকের স্থায়ী প্রোফাইল একবারই সংরক্ষিত থাকে (`Contact`), কিন্তু তার প্রতিটি পৃথক প্রজেক্ট বা প্লটের আগ্রহ আলাদা ডিল (`Opportunity`) হিসেবে ট্র্যাকিং হয়।
2. **জিরো লিড ওভাররাইট (Zero Data Loss):**  
   গ্রাহক পুনরায় ফর্ম পূরণ করলে বা যোগাযোগ করলে আগের কল, ভিজিট বা নোটের ইতিহাস মুছে যায় না।
3. **১৫ মিনিটের স্পিড-টু-লিড SLA (Strict SLA Enforcement):**  
   বিজ্ঞাপন বা ফর্ম থেকে লিড তৈরি হওয়ার সাথে সাথে ১৫ মিনিটের কাউন্টডাউন টাইমার সক্রিয় হয়।
4. **পোস্ট-ভিজিট ডিব্রিফ গেট (Fix 4 - Debrief Gate):**  
   সাইট ভিজিট সম্পন্ন হওয়ার পর কাস্টমারের ডিব্রিফ ফর্ম সাবমিট না করা পর্যন্ত পরবর্তী স্টেজ লক থাকে।
5. **বাধ্যতামূলক এক্সিট রিজন কোড (Mandatory Exit Reason Codes):**  
   কোনো লিড হাতছাড়া হলে ড্রপডাউন থেকে নির্দিষ্ট কারণ ও প্রতিযোগী কোম্পানির নাম এন্ট্রি বাধ্যতামূলক।

---

## 2. মাস্টার URL ও পেজ অ্যাক্সেস ডিরেক্টরি

| মডিউল কোড | মডিউল ও পেজের নাম | সরাসরি অ্যাক্সেস লিংক | ব্যবহারের মূল ভূমিকা |
| :--- | :--- | :--- | :--- |
| **AUTH** | **ইউজার সাইন-ইন পোর্টাল** | [/index.html](https://southeastlandmark.pythonicshariful.tech/index.html) | JWT সিকিউর লগইন |
| **M-00** | **এডমিন কমান্ড সেন্টার** | [/admin-dashboard.html](https://southeastlandmark.pythonicshariful.tech/admin-dashboard.html) | টপ-লেভেল ওভারভিউ |
| **M-00** | **সেলস এক্সিকিউটিভ ড্যাশবোর্ড**| [/dashboard.html](https://southeastlandmark.pythonicshariful.tech/dashboard.html) | প্রতিদিনের অ্যাকশন লিস্ট |
| **SEC-A**| **১৫-স্টেজ কানবান পাইপলাইন** | [/pipeline.html](https://southeastlandmark.pythonicshariful.tech/pipeline.html) | ড্র্যাগ-এন্ড-ড্রপ ফানেল |
| **M-01** | **লিডস হাব (সক্রিয় ফানেল)** | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) | লিড ম্যানেজমেন্ট ও কলিং |
| **SEC-A**| **লিড প্রোফাইল ও টাইমলাইন** | [/lead-details.html](https://southeastlandmark.pythonicshariful.tech/lead-details.html) | পূর্ণাঙ্গ অডিট হিস্ট্রি |
| **M-02** | **ভেরিফাইড ক্লায়েন্টস ডিরেক্টরি**| [/contacts.html](https://southeastlandmark.pythonicshariful.tech/contacts.html) | ১:N গ্রাহক ডাটাবেস |
| **M-02** | **প্রস্পেক্টস ডাটাবেস পুল** | [/prospects.html](https://southeastlandmark.pythonicshariful.tech/prospects.html) | প্রাথমিক আগ্রহীদের পুল |
| **M-04** | **টিম ও ক্যাপাসিটি ব্যালেন্সিং**| [/team.html](https://southeastlandmark.pythonicshariful.tech/team.html) | রাউন্ড-রবিন ও ডিউটি কন্ট্রোল |
| **M-04** | **লিড ওনার্স ও বণ্টন কন্ট্রোল** | [/lead-owners.html](https://southeastlandmark.pythonicshariful.tech/lead-owners.html) | লিড রি-অ্যাসাইন ও ফিল্টারিং |
| **M-05** | **মেসেজ ও ওমনিচ্যানেল ইনবক্স** | [/messages.html](https://southeastlandmark.pythonicshariful.tech/messages.html) | হোয়াটসঅ্যাপ ও এসএমএস |
| **M-05** | **কল হিস্ট্রি ও অ্যাক্টিভিটি লগ**| [/activities.html](https://southeastlandmark.pythonicshariful.tech/activities.html) | কল রেকর্ডিং প্লেব্যাক |
| **M-06** | **টাস্ক ও ফলো-আপ ইঞ্জিন** | [/tasks.html](https://southeastlandmark.pythonicshariful.tech/tasks.html) | নেক্সট অ্যাকশন ডেডলাইন |
| **M-07** | **সাইট ভিজিট ও ইভেন্টস ক্যালেন্ডার**| [/events.html](https://southeastlandmark.pythonicshariful.tech/events.html) | ভিজিট বুকিং ও ট্রান্সপোর্ট |
| **M-08** | **অবজেকশন ও সেলস নোটস** | [/notes.html](https://southeastlandmark.pythonicshariful.tech/notes.html) | ৮টি ক্যাটাগরির টক-ট্র্যাক |
| **M-09** | **প্রজেক্ট ও প্লট ইনভেন্টরি** | [/projects.html](https://southeastlandmark.pythonicshariful.tech/projects.html) | প্লট সাইজ ও রিজার্ভেশন |
| **M-10** | **সেলস বুকিং ও ট্রানজাকশন** | [/sales.html](https://southeastlandmark.pythonicshariful.tech/sales.html) | কিস্তি শিডিউল ও ইনভয়েস |
| **M-10** | **মার্কেটিং খরচ ও সিএসি** | [/expenses.html](https://southeastlandmark.pythonicshariful.tech/expenses.html) | বিজ্ঞাপন খরচ ও CAC ট্র্যাকিং |
| **M-11** | **রিপোর্ট ও ২০-কেপিআই ড্যাশবোর্ড**| [/reports.html](https://southeastlandmark.pythonicshariful.tech/reports.html) | Section D ২০টি কেপিআই |
| **M-12** | **কাস্টমার সাপোর্ট টিকেট** | [/tickets.html](https://southeastlandmark.pythonicshariful.tech/tickets.html) | মিউটেশন ও হ্যান্ডওভার ডেস্ক |
| **CONF** | **সিস্টেম সেটিংস ও ইন্টিগ্রেশন** | [/settings.html](https://southeastlandmark.pythonicshariful.tech/settings.html) | SLA কনফিগ ও ওয়েবহুক |
| **GUIDE**| **মেটা ফেসবুক লিড এডস গাইড** | [/meta_guide.html](https://southeastlandmark.pythonicshariful.tech/meta_guide.html) | ফেসবুক লাইভ সেটআপ গাইড |
| **GUIDE**| **ক্লাউড কল অডিও স্টোরেজ গাইড**| [/b2_guide.html](https://southeastlandmark.pythonicshariful.tech/b2_guide.html) | Backblaze B2 অডিও সেটআপ |
| **PRINT**| **প্রিন্ট উপযোগী ইউজার ম্যানুয়াল** | [/manual.html](https://southeastlandmark.pythonicshariful.tech/manual.html) | ১-ক্লিক PDF জেনারেটর |

---

## 3. Section A: ১৫টি সেলস স্টেজ ও ৫টি এক্সিট গেট

### ক) ১৫টি লিনিয়ার স্টেজ (Linear Funnel Implementation)
| # | স্টেজ কোড | স্টেজের নাম | স্থিতি | ডাটাবেস মডেল ও ফিল্ড | ইউআই লোকেশন ও ফাংশন |
| :-: | :--- | :--- | :---: | :--- | :--- |
| **1** | `NEW` | সদ্য সৃষ্ট লিড | ✅ Implemented | `Opportunity.pipeline_stage = NEW` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (New Leads Tab) |
| **2** | `ASSIGNED` | এজেন্টের নিকট বণ্টনকৃত | ✅ Implemented | `Opportunity.assigned_to_id IS NOT NULL` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (Assigned Badge) |
| **3** | `FIRST_CONTACT_PENDING` | প্রথম যোগাযোগের অপেক্ষায় | ✅ Implemented | `Opportunity.sla_status = NOTIFIED` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (15m Timer) |
| **4** | `CONTACT_ATTEMPTED` | কল চেষ্টা করা হয়েছে | ✅ Implemented | `CallLog` রেকর্ড (Busy/Ringing) | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#call-modal`) |
| **5** | `CONNECTED` | সফল যোগাযোগ সম্পন্ন | ✅ Implemented | `CallLog.connected = True` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#call-modal`) |
| **6** | `QUALIFIED` | BANT মানদণ্ডে উত্তীর্ণ | ✅ Implemented | `Opportunity.qualification_score > 50` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#qualify-modal`) |
| **7** | `DISQUALIFIED` | অনুপযুক্ত বা বাজেট মিসম্যাচ | ✅ Implemented | `Opportunity.pipeline_stage = DISQUALIFIED`| [/pipeline.html](https://southeastlandmark.pythonicshariful.tech/pipeline.html) (Kanban column) |
| **8** | `APPOINTMENT_SCHEDULED`| সাইট ভিজিট নির্ধারিত | ✅ Implemented | `Appointment` রেকর্ড সৃষ্টি | [/events.html](https://southeastlandmark.pythonicshariful.tech/events.html) (`#appointment-modal`) |
| **9** | `APPOINTMENT_CONFIRMED`| ভিজিট কনফার্মকৃত | ✅ Implemented | `AppointmentStatus.CONFIRMED` | [/events.html](https://southeastlandmark.pythonicshariful.tech/events.html) (Status badge) |
| **10**| `VISIT_COMPLETED` | প্রজেক্ট পরিদর্শন সম্পন্ন | ✅ Implemented | `AppointmentStatus.COMPLETED` | [/events.html](https://southeastlandmark.pythonicshariful.tech/events.html) & [/lead-details.html](https://southeastlandmark.pythonicshariful.tech/lead-details.html) |
| **11**| `PROPOSAL_PRESENTED` | প্লট অফার/কোটেশন হস্তান্তর | ✅ Implemented | Debrief Gate আনলক সাপেক্ষে | [/lead-details.html](https://southeastlandmark.pythonicshariful.tech/lead-details.html) (`#debrief-modal`) |
| **12**| `NEGOTIATION` | মূল্য ও কিস্তি আলোচনা | ✅ Implemented | `Opportunity.pipeline_stage = NEGOTIATION` | [/pipeline.html](https://southeastlandmark.pythonicshariful.tech/pipeline.html) (Stage selector) |
| **13**| `RESERVATION_RECEIVED`| বুকিং মানি গৃহীত | ✅ Implemented | `Reservation` রেকর্ড যুক্ত | [/sales.html](https://southeastlandmark.pythonicshariful.tech/sales.html) (`#reservation-modal`) |
| **14**| `DOCUMENTATION_IN_PROCESS`| চুক্তিপত্র প্রস্তুতকরণ | ✅ Implemented | কেওয়াইসি ও স্ট্যাম্প প্রস্তুত | [/sales.html](https://southeastlandmark.pythonicshariful.tech/sales.html) (Sales status) |
| **15**| `SOLD` | বিক্রয় চূড়ান্ত ও ভেরিফাইড | ✅ Implemented | `Sale` রেকর্ড ও ইনভয়েস পেইড | [/sales.html](https://southeastlandmark.pythonicshariful.tech/sales.html) (`#record-sale-modal`) |

### খ) ৫টি বিকল্প এক্সিট গেট (Alternative Exit Paths)
| # | এক্সিট স্টেজ | প্রযোজ্য ক্ষেত্র | স্থিতি | ডাটাবেস সংরক্ষিত ফিল্ডসমূহ | ইউআই কম্পোনেন্ট |
| :-: | :--- | :--- | :---: | :--- | :--- |
| **1** | `CLOSED_LOST` | ডিল ড্রপ বা ব্যর্থ হলে | ✅ Implemented | `exit_reason_code`, `competitor_name`, `authorising_officer` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#exit-modal`) |
| **2** | `NURTURE` | দীর্ঘমেয়াদী সম্ভাব্য ক্রেতা | ✅ Implemented | `reactivation_campaign`, `next_action_deadline` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#exit-modal`) |
| **3** | `BOUGHT_ELSEWHERE` | অন্য প্রজেক্টে কিনে ফেললে | ✅ Implemented | `competitor_project`, `competitor_price` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#exit-modal`) |
| **4** | `INVALID` | ভুল বা ভুয়া নম্বর | ✅ Implemented | `invalid_reason_details`, `Opportunity.status` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#exit-modal`) |
| **5** | `UNREACHABLE` | বারবার চেষ্টায় ব্যর্থ | ✅ Implemented | `CallLog` কাউন্ট (সর্বনিম্ন ৫ বার), `final_result` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#exit-modal`) |

---

## 4. Section B: ১২টি কোর আর্কিটেকচার মডিউল (M-01 থেকে M-12)

### M-01: Multi-Channel Lead Intake & Instant Capture
* **লাইভ অ্যাক্সেস URL:** [https://southeastlandmark.pythonicshariful.tech/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html)
* **মডিউল ডিরেক্টরি অডিট টেবিল:**

| সাব-আইটেম নাম | আর্কিটেকচার স্পেসিফিকেশন | স্থিতি | ব্যাকএন্ড মডেল / এন্ডপয়েন্ট | ফ্রন্টএন্ড পেজ ও ইউআই এলিমেন্ট | ভেরিফিকেশন ও টেস্ট করার পদ্ধতি |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **মেটা ফেসবুক লিড এডস ওয়েবহুক** | রিয়েল-টাইম মেটা ওয়েব-হুক হ্যান্ডলার ও HMAC ভ্যালিডেশন | ✅ Implemented | `POST /api/webhooks/meta`, `WebhookRetry` | [/settings.html](https://southeastlandmark.pythonicshariful.tech/settings.html) (Meta Webhook Tab) | Meta Graph API টেস্ট পেলোড পাঠালে স্বয়ংক্রিয়ভাবে ইনকোয়ারি সৃষ্টি হয়। |
| **ওয়েবসাইট পাবলিক ফর্ম ইনটেক** | ল্যান্ডিং পেজের ফর্ম থেকে লিড রিসিভ এপিআই | ✅ Implemented | `POST /api/webhooks/website` | [/settings.html](https://southeastlandmark.pythonicshariful.tech/settings.html) (Website API Info) | JSON পেলোড দিয়ে কল করলে স্বয়ংক্রিয় লিড হিসেবে এন্ট্রি হয়। |
| **বালক CSV লিড আপলোড** | শত শত লিড ড্র্যাগ-এন্ড-ড্রপ আপলোড ও প্রগ্রেস বার | ✅ Implemented | `POST /api/leads/import` (Multipart/form-data) | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#import-modal`) | `Import` বাটনে ক্লিক করে ফাইল দিলে সাথে সাথে ডাটাবেসে সেভ হয়। |
| **নমুনা CSV ডাউনলোড** | ১-ক্লিকে সঠিক হেডারের নমুনা ফাইল ডাউনলোড | ✅ Implemented | `GET /api/leads/sample-csv` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#download-sample-csv`) | ইম্পোর্ট মডালে `Download Sample CSV` চাপলে `southeast_landmark_leads_sample.csv` ডাউনলোড হয়। |
| **ম্যানুয়াল কুইক লিড এন্ট্রি** | কল বা ওয়াক-ইন ক্রেতার তাৎক্ষণিক প্রোফাইল এন্ট্রি | ✅ Implemented | `POST /api/leads/` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`+ Add Lead` Button) | নাম, ফোন ও প্রজেক্ট দিয়ে সেভ করলে সাথে সাথে পাইপলাইনে আসে। |
| **জিরো ডাটা ওভাররাইট স্থাপত্য** | একই ক্লায়েন্টের পূর্বের ডাটা অক্ষত রেখে নতুন ডিল খোলা | ✅ Implemented | `Contact` (1) ➔ `Opportunity` (N), `Inquiry` | [/lead-details.html](https://southeastlandmark.pythonicshariful.tech/lead-details.html) (Timeline) | একই নম্বরে দ্বিতীয়বার সাবমিট করলে নতুন ডিল খোলে, পুরাতন হিস্ট্রি মুছবে না। |
| **ফোন নম্বর E.164 নরমালাইজেশন** | আন্তর্জাতিক স্ট্যান্ডার্ড E.164 রূপান্তর | ✅ Implemented | `app/utils/phone.py` (`normalize_phone`) | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) | `017...` বা `88017...` লিখলে স্বয়ংক্রিয়ভাবে `+8801...` হিসেবে সেভ হয়। |

---

### M-02: Contact Identity, De-duplication & Client Pool
* **লাইভ অ্যাক্সেস URL:** [https://southeastlandmark.pythonicshariful.tech/contacts.html](https://southeastlandmark.pythonicshariful.tech/contacts.html) ও [/prospects.html](https://southeastlandmark.pythonicshariful.tech/prospects.html)
* **মডিউল ডিরেক্টরি অডিট টেবিল:**

| সাব-আইটেম নাম | আর্কিটেকচার স্পেসিফিকেশন | স্থিতি | ব্যাকএন্ড মডেল / এন্ডপয়েন্ট | ফ্রন্টএন্ড পেজ ও ইউআই এলিমেন্ট | ভেরিফিকেশন ও টেস্ট করার পদ্ধতি |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **1:N কন্টাক্ট-টু-অপরচুনিটি মডেল** | গ্রাহকের স্থায়ী কন্টাক্ট ও মাল্টিপল প্লট ডিল লিংক | ✅ Implemented | `Contact.opportunities = db.relationship()` | [/contacts.html](https://southeastlandmark.pythonicshariful.tech/contacts.html) | কন্টাক্ট প্রোফাইলে ক্লিক করলে তার সমস্ত বর্তমান ও অতীত ডিল দেখা যায়। |
| **ইনস্ট্যান্ট ডুপ্লিকেট চেকার** | নতুন লিড তৈরির সময় স্বয়ংক্রিয় ফোন/ইমেইল ম্যাচিং | ✅ Implemented | `find_existing_contact()` | [/contacts.html](https://southeastlandmark.pythonicshariful.tech/contacts.html) & `/leads.html` | ডুপ্লিকেট ফোন দিলে নতুন কন্টাক্ট তৈরি না করে বিদ্যমান কন্টাক্ট লিঙ্ক করে। |
| **ডুপ্লিকেট লিড মার্জিং ও ক্লিনআপ** | ডুপ্লিকেট লিড একত্রীকরণ এবং হিস্ট্রি মার্জ | ✅ Implemented | `POST /api/leads/clean-duplicates` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#clean-duplicates-btn`) | ক্লিন বাটনে চাপলে ডুপ্লিকেটের সমস্ত কল, ভিজিট ও নোট প্রাইমারিতে মার্জ হয়। |
| **স্থায়ী ক্লায়েন্ট প্রোফাইল** | প্রতিটি গ্রাহকের লাইফটাইম অ্যাক্টিভিটি টাইমলাইন | ✅ Implemented | `Contact`, `ActivityLog`, `Opportunity` | [/contacts.html](https://southeastlandmark.pythonicshariful.tech/contacts.html) | গ্রাহকের নামের উপর চাপলে পূর্ণাঙ্গ লাইফটাইম অ্যাক্টিভিটি স্ক্রিন আসে। |
| **প্রস্পেক্টস ডাটাবেস পুল** | কোল্ড বা র লিডদের জন্য প্রাথমিক সেন্ট্রাল পুল | ✅ Implemented | `/api/leads/prospects` | [/prospects.html](https://southeastlandmark.pythonicshariful.tech/prospects.html) | কোল্ড লিডদের আলাদা পুলে রেখে নার্চারিং ক্যাম্পেইনে যুক্ত করা যায়। |

---

### M-03: Dynamic Lead Scoring & Qualification Matrix (BANT)
* **লাইভ অ্যাক্সেস URL:** [https://southeastlandmark.pythonicshariful.tech/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html)
* **মডিউল ডিরেক্টরি অডিট টেবিল:**

| সাব-আইটেম নাম | আর্কিটেকচার স্পেসিফিকেশন | স্থিতি | ব্যাকএন্ড মডেল / এন্ডপয়েন্ট | ফ্রন্টএন্ড পেজ ও ইউআই এলিমেন্ট | ভেরিফিকেশন ও টেস্ট করার পদ্ধতি |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **BANT ফ্রেমওয়ার্ক ম্যাট্রিক্স** | Budget, Authority, Need, Timeline ইনপুট যাচাই | ✅ Implemented | `Opportunity.budget`, `authority_level`, etc. | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#qualify-modal`) | লিড কার্ডে `Qualify` চাপলে BANT ফিল্ডের ড্রপডাউন ফর্ম খোলে। |
| **০–১০০ ডায়নামিক কোয়ালিফিকেশন স্কোর** | BANT ইনপুট সাপেক্ষে স্বয়ংক্রিয় গাণিতিক স্কোর | ✅ Implemented | `Opportunity.qualification_score` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (Score Badge) | ফর্ম সাবমিট করলেই কার্ডে `Score: 85/100` লাইভ প্রদর্শিত হয়। |
| **৪-লেভেল প্রায়োরিটি ব্যাজ** | `URGENT`, `HIGH`, `MEDIUM`, `LOW` ব্যাজিং | ✅ Implemented | `LeadPriority` enum in `models.py` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) & `/pipeline.html` | প্রায়োরিটি লেভেল অনুযায়ী লাল, কমলা, হলুদ বা নীল ব্যাজ শো করে। |
| **৩-লেভেল লিড টেম্পারেচার** | `HOT`, `WARM`, `COLD` টেম্পারেচার ও ফিল্টারিং | ✅ Implemented | `LeadTemperature` enum in `models.py` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (Fire Icon Tag) | টেম্পারেচার সিলেক্ট করলে কার্ডে ফ্ল্যাশ ট্যাগ যুক্ত হয় ও ফিল্টার করা যায়। |
| **প্লট সাইজ ও দিক পছন্দ কোশ্চেনারি**| ৩/৫/১০ কাঠা, কর্নার ও উত্তর/দক্ষিণমুখী পছন্দ | ✅ Implemented | `preferred_plot_size`, `preferred_facing` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#qualify-modal`) | পছন্দের সাইজ ও দিক নির্বাচন করলে ইনভেন্টরি পেজে স্বয়ংক্রিয় সাজেস্ট করে। |

---

### M-04: Smart Lead Distribution & 15-Minute SLA Engine
* **লাইভ অ্যাক্সেস URL:** [https://southeastlandmark.pythonicshariful.tech/lead-owners.html](https://southeastlandmark.pythonicshariful.tech/lead-owners.html) ও [/team.html](https://southeastlandmark.pythonicshariful.tech/team.html)
* **মডিউল ডিরেক্টরি অডিট টেবিল:**

| সাব-আইটেম নাম | আর্কিটেকচার স্পেসিফিকেশন | স্থিতি | ব্যাকএন্ড মডেল / এন্ডপয়েন্ট | ফ্রন্টএন্ড পেজ ও ইউআই এলিমেন্ট | ভেরিফিকেশন ও টেস্ট করার পদ্ধতি |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **ক্যাপাসিটি রাউন্ড-রবিন বণ্টন** | সক্রিয় লিড ধারণক্ষমতা বিবেচনা করে লিড এসাইন | ✅ Implemented | `User.max_lead_capacity`, `assign_lead_round_robin` | [/team.html](https://southeastlandmark.pythonicshariful.tech/team.html) (Capacity Settings) | এজেন্টের বর্তমান সক্রিয় লিড কোটা পূর্ণ থাকলে পরবর্তী এজেন্টে যায়। |
| **অন-ডিউটি / অফ-ডিউটি টগল** | ছুটির দিনে এজেন্টকে রাউন্ড-রবিন থেকে বাদ রাখা | ✅ Implemented | `User.is_on_duty` | [/team.html](https://southeastlandmark.pythonicshariful.tech/team.html) (Duty Status Switch) | টগল অফ করলে নতুন কোনো লিড তার কাছে বণ্টন হবে না। |
| **১৫-মিনিট স্পিড-টু-লিড টাইমার** | নতুন লিড আসার সাথে সাথে ১৫ মিনিটের কাউন্টডাউন | ✅ Implemented | `Opportunity.sla_deadline`, `SLAStatus.NOTIFIED` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (Countdown Clock) | নতুন লিড কার্ডে লাইভ টাইমার সেকেন্ড অনুযায়ী কমতে থাকে। |
| **১০-মিনিট ওয়ার্নিং অ্যালার্ট** | সময় ফুরিয়ে যাওয়ার প্রাক্কালে হলুদ সতর্কতা | ✅ Implemented | APScheduler Job, `SLAStatus.REMINDED` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (Yellow Pulse Border) | ১০ মিনিট পার হলে কার্ডের সীমানা হলুদ হয়ে সতর্কতা দেখায়। |
| **২০-মিনিট ম্যানেজার এস্কেলেশন** | সময় অতিক্রম করলে ম্যানেজার ড্যাশবোর্ডে রেড এলার্ট | ✅ Implemented | `SLAStatus.MANAGER_ALERTED` | [/admin-dashboard.html](https://southeastlandmark.pythonicshariful.tech/admin-dashboard.html) (Red Alert) | ২০ মিনিট অতিক্রান্ত হলে ম্যানেজারের স্ক্রিনে লাল নোটিফিকেশন বাজে। |
| **ম্যানেজার লিড রি-অ্যাসাইনমেন্ট** | ১-ক্লিকে ওভারডিউ লিড অন্য অফিসারের কাছে স্থানান্তর | ✅ Implemented | `PUT /api/leads/<id>/reassign` | [/lead-owners.html](https://southeastlandmark.pythonicshariful.tech/lead-owners.html) (`Reassign Lead` Btn) | ড্রপডাউন থেকে নতুন অফিসারের নাম সিলেক্ট করলেই লিড স্থানান্তরিত হয়। |

---

### M-05: Telephony & Multi-Channel Communications Suite
* **লাইভ অ্যাক্সেস URL:** [https://southeastlandmark.pythonicshariful.tech/messages.html](https://southeastlandmark.pythonicshariful.tech/messages.html) ও [/activities.html](https://southeastlandmark.pythonicshariful.tech/activities.html)
* **মডিউল ডিরেক্টরি অডিট টেবিল:**

| সাব-আইটেম নাম | আর্কিটেকচার স্পেসিফিকেশন | স্থিতি | ব্যাকএন্ড মডেল / এন্ডপয়েন্ট | ফ্রন্টএন্ড পেজ ও ইউআই এলিমেন্ট | ভেরিফিকেশন ও টেস্ট করার পদ্ধতি |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **১-ক্লিক ব্রাউজার কল ডায়ালার** | সরাসরি ডিভাইস ডায়ালারে কল করার সুবিধা | ✅ Implemented | `tel:` URL Protocol Handler | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`Call` Button on Card) | `Call` বাটনে চাপলেই ডিভাইসের ডায়ালার চালু হয়ে যায়। |
| **কল আউটকাম ড্রপডাউন** | Connected, Busy, Switched Off, Ringing, Wrong Num | ✅ Implemented | `ActivityOutcome` enum, `CallLog` model | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#call-modal`) | কল শেষে ড্রপডাউন থেকে আউটকাম সিলেক্ট না করা পর্যন্ত ফর্ম সাবমিট হয় না। |
| **৫টি প্রমিত ডিউরেশন ব্যান্ড** | <1m, 1-3m, 3-5m, 5-10m, >10m ব্যান্ড নির্বাচন | ✅ Implemented | `DurationBand` enum in `models.py` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#call-modal`) | কলের দৈর্ঘ্য সিলেক্ট করলে অ্যানালিটিক্সে গড় কল টাইম হিসাব হয়। |
| **ক্লাউড কল অডিও রেকর্ডিং** | ক্লাউড Backblaze B2 স্টোরেজে অডিও আপলোড ও প্লেব্যাক | ✅ Implemented | `CallLog.recording_url`, `b2_storage.py` | [/activities.html](https://southeastlandmark.pythonicshariful.tech/activities.html) (Audio Player) | অডিও ফাইল আপলোড করলে ব্রাউজারেই সরাসরি প্লে করে শোনা যায়। |
| **সিকিউর অডিও ডাউনলোড প্রটেকশন**| শুধুমাত্র প্রিভিলেজড রোল এক্সেস ও অডিট ট্র্যাকিং | ✅ Implemented | `RecordingDownloadLog` model | [/activities.html](https://southeastlandmark.pythonicshariful.tech/activities.html) | ডাউনলোড বাটনে চাপ দিলে ব্যাকএন্ডে কে ডাউনলোড করল তা রেকর্ড হয়। |
| **হোয়াটসঅ্যাপ ও এসএমএস ওমনিচ্যানেল**| ১-ক্লিকে টেমপ্লেট মেসেজ হোয়াটসঅ্যাপে পাঠানো | ✅ Implemented | WhatsApp Web API Protocol | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`WhatsApp` Button) | বাটনে চাপ দিলে ক্লায়েন্টের নম্বরে প্রি-ফিল্ড মেসেজসহ চ্যাট ওপেন হয়। |

---

### M-06: Task & Follow-up Management Engine
* **লাইভ অ্যাক্সেস URL:** [https://southeastlandmark.pythonicshariful.tech/tasks.html](https://southeastlandmark.pythonicshariful.tech/tasks.html)
* **মডিউল ডিরেক্টরি অডিট টেবিল:**

| সাব-আইটেম নাম | আর্কিটেকচার স্পেসিফিকেশন | স্থিতি | ব্যাকএন্ড মডেল / এন্ডপয়েন্ট | ফ্রন্টএন্ড পেজ ও ইউআই এলিমেন্ট | ভেরিফিকেশন ও টেস্ট করার পদ্ধতি |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **নেক্সট অ্যাকশন ডেডলাইন বাধ্যবাধকতা**| প্রতিটি লিডের পরবর্তী ফলো-আপ ডেট নির্ধারণ বাধ্যতামূলক | ✅ Implemented | `Opportunity.next_action_deadline` | [/tasks.html](https://southeastlandmark.pythonicshariful.tech/tasks.html) & `/leads.html` | ডেট ও টাইম সেট না করলে সিস্টেম কোনো কল লগ সংরক্ষণ করতে দেয় না। |
| **ওভারডিউ টাস্ক রেড পালস** | সময় অতিক্রান্ত টাস্কে লাল বর্ডার ও ওয়ার্নিং এলার্ট | ✅ Implemented | `is_overdue` Dynamic Model Property | [/tasks.html](https://southeastlandmark.pythonicshariful.tech/tasks.html) (Red Pulsing Tag) | ডেডলাইন পার হলে টাস্কের পাশে লাল "OVERDUE" ট্যাগ দেখা যায়। |
| **আজকের করণীয় ফলো-আপ তালিকা**| আজকের ডেডলাইনের টাস্কগুলোর ফিল্টার্ড তালিকা | ✅ Implemented | `/api/tasks/?filter=today` | [/tasks.html](https://southeastlandmark.pythonicshariful.tech/tasks.html) (`Today's Tasks` Tab) | এক্সিকিউটিভ লগইন করে এক নজরে আজকের সব ফলো-আপ দেখতে পারেন। |
| **টাস্ক ডেলিগেশন ও অ্যাসাইনমেন্ট** | টিম মেম্বারদের মাঝে কাজের দায়িত্ব অর্পণ | ✅ Implemented | `Task.assigned_to_id`, `POST /api/tasks/` | [/tasks.html](https://southeastlandmark.pythonicshariful.tech/tasks.html) (`+ New Task` Modal) | ম্যানেজার যেকোনো এজেন্টকে সিলেক্ট করে কাজ অর্পণ করতে পারেন। |
| **অটো-কমপ্লিশন ও হিস্ট্রি ট্র্যাকার** | টিক দিলে স্বয়ংক্রিয়ভাবে অ্যাক্টিভিটিতে এন্ট্রি হওয়া | ✅ Implemented | `PUT /api/tasks/<id>/complete` | [/tasks.html](https://southeastlandmark.pythonicshariful.tech/tasks.html) (Checkbox) | চেকবক্সে টিক দিলে টাস্কটি কমপ্লিট হয়ে টাইমলাইনে রেকর্ড হয়। |

---

### M-07: Site Visit Lifecycle & Logistics Manager (Debrief Gate)
* **লাইভ অ্যাক্সেস URL:** [https://southeastlandmark.pythonicshariful.tech/events.html](https://southeastlandmark.pythonicshariful.tech/events.html) ও [/lead-details.html](https://southeastlandmark.pythonicshariful.tech/lead-details.html)
* **মডিউল ডিরেক্টরি অডিট টেবিল:**

| সাব-আইটেম নাম | আর্কিটেকচার স্পেসিফিকেশন | স্থিতি | ব্যাকএন্ড মডেল / এন্ডপয়েন্ট | ফ্রন্টএন্ড পেজ ও ইউআই এলিমেন্ট | ভেরিফিকেশন ও টেস্ট করার পদ্ধতি |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **সাইট ভিজিট বুকিং ক্যালেন্ডার** | প্রজেক্ট নাম, ক্লায়েন্টের পিকআপ ঠিকানা ও তারিখ নির্ধারণ | ✅ Implemented | `Appointment` model, `POST /api/appointments/` | [/events.html](https://southeastlandmark.pythonicshariful.tech/events.html) & `/leads.html` | লিড কার্ডে `Book Visit` চাপলে ক্যালেন্ডার বুকিং ফর্ম চালু হয়। |
| **কোম্পানি পরিবহন ও ড্রাইভার বরাদ্দ**| ভিজিটের জন্য কোম্পানির গাড়ি ও ড্রাইভার নির্বাচন | ✅ Implemented | `Appointment.vehicle_assigned`, `driver_name` | [/events.html](https://southeastlandmark.pythonicshariful.tech/events.html) (`Logistics` Tab) | বুকিং ফরমে ড্রাইভার ও গাড়ির নম্বর ট্যাগ করে দেওয়া যায়। |
| **ভিজিট স্ট্যাটাস লাইফসাইকেল** | SCHEDULED ➔ CONFIRMED ➔ COMPLETED | ✅ Implemented | `AppointmentStatus` enum in `models.py` | [/events.html](https://southeastlandmark.pythonicshariful.tech/events.html) (Status Pills) | ভিজিটের আগের দিন `Confirm` এবং ভিজিট শেষে `Complete` বাটনে চাপুন। |
| **Fix 4 Debrief Gate (লক প্রটোকল)**| ভিজিট শেষে ডিব্রিফ ছাড়া কোটেশন স্টেজ লক রাখা | ✅ Implemented | `Debrief` model, `POST /api/leads/appointments/<id>/debrief` | [/lead-details.html](https://southeastlandmark.pythonicshariful.tech/lead-details.html) (`#debrief-modal`) | ভিজিট শেষে ডিব্রিফ ফর্ম সাবমিট না করা পর্যন্ত পরবর্তী ধাপ আনলক হয় না। |
| **রিয়েল-টাইম শো-রেট অ্যানালিটিক্স** | কনফার্ম ভিজিটের বিপরীতে উপস্থিত হওয়া সাফল্য হার | ✅ Implemented | `/api/reports/kpis` (KPI #7 Show Rate) | [/reports.html](https://southeastlandmark.pythonicshariful.tech/reports.html) (`#kpi-show-rate`) | সম্পন্ন ভিজিট ভাগ কনফার্ম ভিজিট থেকে শো-রেট স্বয়ংক্রিয় হিসাব হয়। |

---

### M-08: Objection Intelligence & Resolution Engine
* **লাইভ অ্যাক্সেস URL:** [https://southeastlandmark.pythonicshariful.tech/notes.html](https://southeastlandmark.pythonicshariful.tech/notes.html) ও [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html)
* **মডিউল ডিরেক্টরি অডিট টেবিল:**

| সাব-আইটেম নাম | আর্কিটেকচার স্পেসিফিকেশন | স্থিতি | ব্যাকএন্ড মডেল / এন্ডপয়েন্ট | ফ্রন্টএন্ড পেজ ও ইউআই এলিমেন্ট | ভেরিফিকেশন ও টেস্ট করার পদ্ধতি |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **১১টি স্ট্যান্ডার্ড অবজেকশন কোড** | ১. দাম বেশি ২. লোকেশন দূরে ৩. লিগ্যাল কাগজপত্র ৪. কিস্তির মেয়াদ ৫. অন্য প্রজেক্ট তুলনা ৬. বিশ্বাস ৭. পারিবারিকভাবে সিদ্ধান্তহীনতা ৮. টাইমিং ৯. ক্যাশ ফ্লো ১০. প্রতিযোগী ১১. নো রেসপন্স | ✅ Implemented | `ObjectionCategory` enum in `models.py` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#objection-modal`) | লিড কার্ডে `Objection` বাটনে চাপলে ১১টি নির্দিষ্ট ক্যাটাগরির ড্রপডাউন খোলে। |
| **অবজেকশন ইনটেনসিটি স্লাইডার** | ১ থেকে ৫ স্কেলে আপত্তির তীব্রতা পরিমাপ | ✅ Implemented | `Objection.intensity` (1 to 5) | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`Intensity Slider`) | স্লাইডার টেনে আপত্তির তীব্রতা নির্ধারণ করা যায়। |
| **প্রিন্সিপাল ব্লকার টগল** | এই আপত্তিটিই ডিল আটকে থাকার মূল কারণ কিনা তা চিহ্নিত | ✅ Implemented | `Objection.is_principal_blocker` (Boolean) | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (Checkbox Toggle) | চেকবক্সে টিক দিলে ম্যানেজারের কাছে এটি প্রধান বাধা হিসেবে মার্ক হয়। |
| **সেলস টক-ট্র্যাক স্ক্রিপ্ট ব্যাংক**| প্রতিটি আপত্তির বিপরীতে প্রশিক্ষিত সেলস পিচ প্রদর্শন | ✅ Implemented | `/notes.html` (Objection Battlecards) | [/notes.html](https://southeastlandmark.pythonicshariful.tech/notes.html) | আপত্তির কারণ বাছাই করলেই স্ক্রিনে ক্লায়েন্টকে কী বলতে হবে তা ভেসে ওঠে। |
| **অবজেকশন ডিস্ট্রিবিউশন চার্ট** | কোন আপত্তির কারণে কত লিড আটকে আছে তার গ্রাফ | ✅ Implemented | `/api/reports/charts/objections` | [/reports.html](https://southeastlandmark.pythonicshariful.tech/reports.html) (Objection Chart) | পাই-চার্টে শীর্ষ আপত্তিগুলো রিয়েল-টাইমে গ্রাফ আকারে দেখা যায়। |

---

### M-09: Inventory, Plot Master & Unit Reservation
* **লাইভ অ্যাক্সেস URL:** [https://southeastlandmark.pythonicshariful.tech/projects.html](https://southeastlandmark.pythonicshariful.tech/projects.html)
* **মডিউল ডিরেক্টরি অডিট টেবিল:**

| সাব-আইটেম নাম | আর্কিটেকচার স্পেসিফিকেশন | স্থিতি | ব্যাকএন্ড মডেল / এন্ডপয়েন্ট | ফ্রন্টএন্ড পেজ ও ইউআই এলিমেন্ট | ভেরিফিকেশন ও টেস্ট করার পদ্ধতি |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **প্রজেক্ট ও মাস্টার লেআউট হায়ারার্কি**| Project ➔ Phase ➔ Block ➔ Road ➔ Plot লেআউট | ✅ Implemented | `Project`, `Phase`, `Block`, `Road`, `Plot` | [/projects.html](https://southeastlandmark.pythonicshariful.tech/projects.html) | প্রজেক্টে ক্লিক করলে ব্লক ও রোডভিত্তিক প্লটের তালিকা দেখা যায়। |
| **স্ট্যান্ডার্ড প্লট সাইজ ও ফেসিং**| ৩ কাঠা, ৫ কাঠা, ১০ কাঠা এবং উত্তর/দক্ষিণমুখী ট্যাগ | ✅ Implemented | `Plot.size_katha`, `Plot.facing` | [/projects.html](https://southeastlandmark.pythonicshariful.tech/projects.html) (Plot Cards) | প্রতিটি প্লটের সাইজ ও দিক ব্যাজে সুস্পষ্টভাবে লেখা থাকে। |
| **৪-লেভেল প্লট স্ট্যাটাস কালার কোডিং**| AVAILABLE (সবুজ), BLOCKED (হলুদ), RESERVED (নীল), SOLD (লাল) | ✅ Implemented | `PlotStatus` enum in `models.py` | [/projects.html](https://southeastlandmark.pythonicshariful.tech/projects.html) (Color Coded Grid) | প্লটের বর্তমান স্ট্যাটাস অনুযায়ী গ্রিডে নির্দিষ্ট রঙ দেখা যায়। |
| **ডাবল-সেলিং প্রতিরোধক লক** | একই প্লটে একাধিক অফিসার যেন বায়না না নিতে পারেন | ✅ Implemented | Database Row-Level Transaction Lock | [/projects.html](https://southeastlandmark.pythonicshariful.tech/projects.html) | একজন রিজার্ভ করলে সিস্টেমে স্বয়ংক্রিয়ভাবে অন্য সবার জন্য লক হয়ে যায়। |
| **ইউনিট রিজার্ভেশন ও টোকেন মানি** | ক্লায়েন্টের লিডের সাথে প্লট ট্যাগ করে বুকিং মানি রেকর্ড | ✅ Implemented | `Reservation` model, `POST /api/sales/reservations` | [/sales.html](https://southeastlandmark.pythonicshariful.tech/sales.html) (`#reservation-modal`) | ক্লায়েন্ট সিলেক্ট করে মানি রিসিট নম্বর ও বায়নার পরিমাণ দিয়ে সেভ করুন। |

---

### M-10: Sales Transaction, Invoicing & Collections
* **লাইভ অ্যাক্সেস URL:** [https://southeastlandmark.pythonicshariful.tech/sales.html](https://southeastlandmark.pythonicshariful.tech/sales.html) ও [/expenses.html](https://southeastlandmark.pythonicshariful.tech/expenses.html)
* **মডিউল ডিরেক্টরি অডিট টেবিল:**

| সাব-আইটেম নাম | আর্কিটেকচার স্পেসিফিকেশন | স্থিতি | ব্যাকএন্ড মডেল / এন্ডপয়েন্ট | ফ্রন্টএন্ড পেজ ও ইউআই এলিমেন্ট | ভেরিফিকেশন ও টেস্ট করার পদ্ধতি |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **ভেরিফাইড সেলস রেকর্ডার** | প্লটের চূড়ান্ত বিক্রয় মূল্য, ডাউন পেমেন্ট ও রেজিস্ট্রি ডেট এন্ট্রি | ✅ Implemented | `Sale` model, `POST /api/sales/record` | [/sales.html](https://southeastlandmark.pythonicshariful.tech/sales.html) (`#record-sale-modal`) | `Record Sale` চাপলে বিক্রয় মূল্য ও চুক্তিপত্রের তথ্য সেভ করা যায়। |
| **কিস্তি ও ইনভয়েস শিডিউল জেনারেটর**| এককালীন বা কিস্তির ইনভয়েস তৈরি (PAID, SENT, OVERDUE)| ✅ Implemented | `Invoice`, `Installment` models | [/sales.html](https://southeastlandmark.pythonicshariful.tech/sales.html) (Invoices Tab) | কিস্তি সংখ্যা দিলে স্বয়ংক্রিয়ভাবে মাসিক ইনভয়েস শিডিউল জেনারেট হয়। |
| **কালেকশন রেট ট্র্যাকিং** | মোট প্রাপ্য ইনভয়েস মূল্যের বিপরীতে আদায়কৃত টাকার হার | ✅ Implemented | `/api/reports/kpis` (KPI #16 Collection Rate) | [/reports.html](https://southeastlandmark.pythonicshariful.tech/reports.html) (`#kpi-collection-rate`) | কালেকশনকৃত টাকা ভাগ মোট ইনভয়েস ডিউ থেকে পারসেন্টেজ হিসাব হয়। |
| **মার্কেটিং খরচ অনুমোদন খাতা** | ফেসবুক ও অফলাইন মার্কেটিং খরচের ভাউচার এন্ট্রি | ✅ Implemented | `Expense` model, `POST /api/expenses/` | [/expenses.html](https://southeastlandmark.pythonicshariful.tech/expenses.html) (`+ Add Expense`) | খরচের ক্যাটাগরি ও ভাউচার দিয়ে এডমিন অনুমোদন করতে পারেন। |
| **কাস্টমার একুইজিশন কস্ট (CAC)** | মোট মার্কেটিং ব্যয় ভাগ মোট বিক্রয় সংখ্যা | ✅ Implemented | `/api/reports/kpis` (KPI #19 CAC) | [/reports.html](https://southeastlandmark.pythonicshariful.tech/reports.html) (`#kpi-cac`) | ১ জন ক্রেতা অর্জন করতে কোম্পানির গড় খরচ রিয়েল-টাইমে হিসাব হয়। |

---

### M-11: Reports & Analytics (Core 20-KPI Framework)
* **লাইভ অ্যাক্সেস URL:** [https://southeastlandmark.pythonicshariful.tech/reports.html](https://southeastlandmark.pythonicshariful.tech/reports.html)
* **মডিউল ডিরেক্টরি অডিট টেবিল:**

| সাব-আইটেম নাম | আর্কিটেকচার স্পেসিফিকেশন | স্থিতি | ব্যাকএন্ড মডেল / এন্ডপয়েন্ট | ফ্রন্টএন্ড পেজ ও ইউআই এলিমেন্ট | ভেরিফিকেশন ও টেস্ট করার পদ্ধতি |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **Section D ২০টি লাইভ কেপিআই কার্ড**| ডাটাবেস থেকে রিয়েল-টাইমে ২০টি মেট্রিক্স হিসাব | ✅ Implemented | `GET /api/reports/kpis` | [/reports.html](https://southeastlandmark.pythonicshariful.tech/reports.html) (20 KPI Cards Grid) | কোনো ডামি ডাটা ছাড়া সরাসরি এসকিউএল ডাটাবেস থেকে হিসাব হয়। |
| **৬টি ডাইনামিক ট্রেন্ড চার্ট** | Lead Outcomes, Objections, Revenue, CAC, Show Rate | ✅ Implemented | `Chart.js` Visualizations, `/api/reports/charts/...` | [/reports.html](https://southeastlandmark.pythonicshariful.tech/reports.html) (Canvas Charts) | চার্টের উপর মাউস নিলে রিয়েল-টাইম তথ্য পপআপে দেখা যায়। |
| **সুপার-ফাস্ট ইন-মেমোরি ক্যাশ** | ১৫-সেকেন্ডের মেমোরি ক্যাশ ও Stale-While-Revalidate | ✅ Implemented | In-memory cache dict in `reports/routes.py` | [/reports.html](https://southeastlandmark.pythonicshariful.tech/reports.html) | পেজ রিফ্রেশ দিলে ০ মিলি-সেকেন্ডে তাৎক্ষণিক লোড হয়ে যায়। |
| **সিএসভি ও এক্সেল ডাটা এক্সপোর্ট** | এডমিন ও ম্যানেজারের জন্য সম্পূর্ণ লিড ডাটাবেস ডাউনলোড | ✅ Implemented | `GET /api/reports/export/leads` | [/reports.html](https://southeastlandmark.pythonicshariful.tech/reports.html) (`Export Leads CSV` Btn) | বাটনে চাপ দিলে সব ফিল্টার্ড লিড সিএসভি ফাইল হিসেবে ডাউনলোড হয়। |

---

### M-12: Post-Handover CRM, Customer Service & Tickets
* **লাইভ অ্যাক্সেস URL:** [https://southeastlandmark.pythonicshariful.tech/tickets.html](https://southeastlandmark.pythonicshariful.tech/tickets.html)
* **মডিউল ডিরেক্টরি অডিট টেবিল:**

| সাব-আইটেম নাম | আর্কিটেকচার স্পেসিফিকেশন | স্থিতি | ব্যাকএন্ড মডেল / এন্ডপয়েন্ট | ফ্রন্টএন্ড পেজ ও ইউআই এলিমেন্ট | ভেরিফিকেশন ও টেস্ট করার পদ্ধতি |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **বিক্রয়োত্তর সার্ভিস টিকেট ডেস্ক** | দলিল রেজিস্ট্রি, নামজারি ও সীমানা পিলারিং সংক্রান্ত টিকেট | ✅ Implemented | `Ticket` model, `POST /api/tickets/` | [/tickets.html](https://southeastlandmark.pythonicshariful.tech/tickets.html) (`+ New Ticket` Modal) | কাস্টমার নির্বাচন করে টিকেটের ক্যাটাগরি ও বিবরণ দিয়ে সাবমিট করুন। |
| **টিকেট স্ট্যাটাস লাইফসাইকেল** | `OPEN` ➔ `IN_PROGRESS` ➔ `RESOLVED` ট্র্যাকিং | ✅ Implemented | `TicketStatus` enum in `models.py` | [/tickets.html](https://southeastlandmark.pythonicshariful.tech/tickets.html) (Status Badge) | সমস্যা সমাধান হলে রেজোলিউশন নোট লিখে স্ট্যাটাস ক্লোজ করা যায়। |
| **রেফারেল ও রিপিট বায়ার ট্র্যাকিং** | সন্তুষ্ট ক্রেতাদের রেফারেন্সে আসা নতুন লিড সনাক্তকরণ | ✅ Implemented | `Opportunity.is_referral`, `referrer_contact_id` | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (Referral Badge) | রেফারেল লিডগুলোর জন্য ভিআইপি কমিশন ও স্পেশাল কেয়ার ট্যাগ যুক্ত হয়। |

---

## 5. Section C: আর্কিটেকচারের ৫টি ক্রিটিক্যাল ডিজাইন ফিক্স অডিট

| ফিক্স আইডি | স্থাপত্যের স্পেসিফিক সমস্যা | বাস্তবায়িত কোড ও আর্কিটেকচার সমাধান | স্থিতি | ইউআই লোকেশন |
| :---: | :--- | :--- | :---: | :--- |
| **Fix 1** | **কম্পোজিট স্ট্যাটাস জটলা:** পূর্বের সিস্টেমে অ্যাক্টিভিটি, অ্যাপয়েন্টমেন্ট, অ্যাসেসমেন্ট ও রেজাল্ট একটি ফিল্ডে জট পাকানো ছিল। | `Opportunity` মডেলে ৪টি আলাদা কলামে বিভক্ত: `last_activity_type`, `last_activity_outcome`, `appointment_status`, `manager_assessment`, `final_result`। | ✅ Implemented | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (Distinct Badges) |
| **Fix 2** | **১৫-মিনিট ফার্স্ট-টাচ SLA বাস্তবায়ন:** দ্রুত যোগাযোগ না করায় লিড কোল্ড হয়ে যেত। | ব্যাকগ্রাউন্ড শিডিউলার দ্বারা ১০ মিনিটে ওয়ার্নিং, ২০ মিনিটে ম্যানেজার এস্কেলেশন এবং ৩০-৬০ মিনিটে রি-অ্যাসাইন ফ্ল্যাগিং। | ✅ Implemented | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (Live SLA Timer) |
| **Fix 3** | **সংশোধিত ১৫ স্টেজ ও ৫টি এক্সিট গেট:** ফানেল থেকে লিড হারিয়ে যাওয়ার কারণ সংরক্ষণ ছিল না। | ১৫টি লিনিয়ার স্টেজ এবং ড্রপডাউন এক্সিট রিজন কোড ও প্রতিযোগী নাম ছাড়া ডিল ক্লোজ না হওয়ার সুরক্ষা। | ✅ Implemented | [/pipeline.html](https://southeastlandmark.pythonicshariful.tech/pipeline.html) & `/leads.html` (`#exit-modal`) |
| **Fix 4** | **পোস্ট-ভিজিট ডিব্রিফ গেট (Debrief Gate):** ভিজিটের পর অফিসাররা ক্লায়েন্টের ফিডব্যাক না লিখে কোটেশন পাঠাত। | অ্যাপয়েন্টমেন্ট `COMPLETED` হওয়ার পর ডিব্রিফ ফর্ম সাবমিট না করা পর্যন্ত পরবর্তী কোটেশন স্টেজ লক রাখা। | ✅ Implemented | [/lead-details.html](https://southeastlandmark.pythonicshariful.tech/lead-details.html) (`#debrief-modal`) |
| **Fix 5** | **১১টি প্রমিত অবজেকশন কোড ট্যাক্সোনমি:** অসংলগ্ন নোটের কারণে প্যাটার্ন বোঝা যেত না। | ১১টি নির্দিষ্ট ক্যাটাগরি, ১–৫ তীব্রতা স্লাইডার এবং প্রধান বাধা (Principal Blocker) চিহ্নিতকরণ। | ✅ Implemented | [/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html) (`#objection-modal`) |

---

## 6. Section D: ২০টি কোর কেপিআই অ্যানালিটিক্স ম্যাট্রিক্স

| # | কেপিআই এর নাম | আর্কিটেকচার ফর্মুলা ও অর্থ | স্থিতি | ডাটাবেস হিসাব পদ্ধতি | ইউআই এলিমেন্ট আইডি |
| :-: | :--- | :--- | :---: | :--- | :--- |
| **1** | **Speed-to-Lead** | লিড এন্ট্রি থেকে প্রথম কলের গড় সময় (< 15m) | ✅ Implemented | `AVG(CallLog.created_at - Opportunity.created_at)` | `#kpi-speed-to-lead` |
| **2** | **SLA Compliance %** | ১৫ মিনিটের মধ্যে কল সম্পন্ন লিডের শতকরা হার | ✅ Implemented | `COUNT(On-time first calls) / COUNT(Total inquiries) * 100` | `#kpi-sla-compliance` |
| **3** | **Contact Rate** | মোট ডায়ালের বিপরীতে সফল কথা হওয়া কলের অনুপাত | ✅ Implemented | `COUNT(Connected calls) / COUNT(Total call attempts) * 100` | `#kpi-contact-rate` |
| **4** | **Qualification Rate**| সংযুক্ত গ্রাহকদের মধ্যে BANT মানদণ্ডে উত্তীর্ণ হার | ✅ Implemented | `COUNT(Qualified leads) / COUNT(Connected leads) * 100` | `#kpi-qualification-rate` |
| **5** | **Appt Booking Rate** | কোয়ালিফাইড গ্রাহকদের মধ্যে সাইট ভিজিট বুকিং হার | ✅ Implemented | `COUNT(Scheduled visits) / COUNT(Qualified leads) * 100` | `#kpi-booking-rate` |
| **6** | **Confirmation Rate** | বুক করা ভিজিটের মধ্যে আগের দিন কনফার্ম হার | ✅ Implemented | `COUNT(Confirmed visits) / COUNT(Scheduled visits) * 100` | `#kpi-confirmation-rate` |
| **7** | **Show Rate** | কনফার্ম করা গ্রাহকদের মধ্যে স্বশরীরে আসার হার | ✅ Implemented | `COUNT(Completed visits) / COUNT(Confirmed visits) * 100` | `#kpi-show-rate` |
| **8** | **Visit-to-Negotiation** | ভিজিট শেষে দরকষাকষিতে পৌঁছানোর হার | ✅ Implemented | `COUNT(Negotiation opened) / COUNT(Completed visits) * 100` | `#kpi-visit-to-neg` |
| **9** | **Visit-to-Reservation**| সাইট ভিজিট সম্পন্ন থেকে বুকিং বায়নার অনুপাত | ✅ Implemented | `COUNT(Reservations) / COUNT(Completed visits) * 100` | `#kpi-visit-to-res` |
| **10**| **Reservation-to-Sale** | বায়না থেকে চূড়ান্ত দলিল রেজিস্ট্রি বা বিক্রয় হার | ✅ Implemented | `COUNT(Verified sales) / COUNT(Reservations) * 100` | `#kpi-res-to-sale` |
| **11**| **Follow-up Compliance**| সঠিক সময়ে ফলো-আপ সম্পন্ন করার হার | ✅ Implemented | `COUNT(On-time follow-ups) / COUNT(Total scheduled) * 100` | `#kpi-followup-compliance` |
| **12**| **Lead Aging Heatmap** | ১, ৩, ৭, ১৪ ও ৩০+ দিন যোগাযোগহীন লিড সংখ্যা | ✅ Implemented | `COUNT(Opportunities grouped by DATEDIFF(NOW(), updated_at))`| `#kpi-aging-heatmap` |
| **13**| **Reactivation Rate** | নার্চার পুল থেকে পুনরায় সক্রিয় হওয়া গ্রাহকের হার | ✅ Implemented | `COUNT(Reactivated leads) / COUNT(Total nurture pool) * 100` | `#kpi-reactivation-rate` |
| **14**| **Closed-Lost Rate** | ড্রপ বা অকৃতকার্য হওয়া লিডের কারণভিত্তিক অনুপাত | ✅ Implemented | `COUNT(Closed lost leads) / COUNT(Qualified leads) * 100` | `#kpi-closed-lost-rate` |
| **15**| **Avg Sales Cycle** | লিড এন্ট্রি থেকে সেল ক্লোজ হওয়ার গড় দিন সংখ্যা | ✅ Implemented | `AVG(Sale.date - Opportunity.created_at in days)` | `#kpi-avg-sales-cycle` |
| **16**| **Collection Rate** | প্রাপ্য ইনভয়েস মূল্যের বিপরীতে আদায়কৃত টাকা % | ✅ Implemented | `SUM(Paid invoice amount) / SUM(Total invoiced due) * 100` | `#kpi-collection-rate` |
| **17**| **Source Conversion** | চ্যানেলভেদে (ফেসবুক/ওয়েবসাইট) বিক্রয় সাফল্য হার | ✅ Implemented | `COUNT(Sold by source) / COUNT(Total leads by source) * 100` | `#kpi-source-conversion` |
| **18**| **Cost / Completed Visit**| প্রতিটি সফল সাইট ভিজিটে কোম্পানির গড় ব্যয় | ✅ Implemented | `SUM(Marketing spend) / COUNT(Completed visits)` | `#kpi-cost-per-visit` |
| **19**| **CAC (Acquisition Cost)**| ১ জন ক্রেতা অর্জন করতে মোট বিপণন ও সেলস খরচ | ✅ Implemented | `SUM(Total Marketing & Sales spend) / COUNT(Verified sales)` | `#kpi-cac` |
| **20**| **Active Pipeline Value**| পাইপলাইনের সমস্ত সম্ভাব্য ডিলের মোট সম্ভাব্য মূল্য | ✅ Implemented | `SUM(Opportunity estimated value across active stages)` | `#kpi-active-pipeline` |

---

## 7. Section E: ১৭টি সিকিউরিটি ও আরবিএসি কন্ট্রোল

| # | সিকিউরিটি কন্ট্রোল | বাস্তবায়িত প্রযুক্তিগত সমাধান | স্থিতি |
| :-: | :--- | :--- | :---: |
| **1** | **৫-স্তরের রোল হায়ারার্কি** | `EXECUTIVE`, `LEAD_OWNER`, `MANAGER`, `GM`, `CEO`, `ADMIN` | ✅ Active |
| **2** | **আইসোলেটেড লিড ওনার ভিউ** | সেলস এক্সিকিউটিভ শুধুমাত্র তার নিজের লিড দেখতে পারেন | ✅ Active |
| **3** | **টিম-লেভেল ভিজিবিলিটি** | সেলস ম্যানেজার তার অধীনস্থ টিমের লিড ও পারফরম্যান্স দেখতে পারেন | ✅ Active |
| **4** | **এক্সিকিউটিভ ককপিট ওভারসাইট** | জিএম ও সিইও কোম্পানির রাজস্ব, সিএসি ও ম্যাক্রো মেট্রিক্স মনিটর করেন | ✅ Active |
| **5** | **সিস্টেম এডমিন ক্ষমতা** | সিস্টেম সেটিংস, ইউজার ম্যানেজমেন্ট ও সিস্টেম কনফিগারেশন পূর্ণ নিয়ন্ত্রণ | ✅ Active |
| **6** | **JWT অথেনটিকেশন ও টোকেন রিফ্রেশ** | ক্রিপ্টোগ্রাফিক সাইনড টোকেন ও মেয়াদোত্তীর্ণ সেশন সিকিউরিটি | ✅ Active |
| **7** | **ফিল্ড-লেভেল ডেটা মাস্কিং** | অননুমোদিত ইউজারদের নিকট থেকে ফোন নম্বর ও ব্যক্তিগত তথ্য আড়াল রাখা | ✅ Active |
| **8** | **প্রাইভেট ম্যানেজার নোট ফিল্ড প্রটেকশন** | এক্সিকিউটিভ যাতে ম্যানেজারের প্রাইভেট রেটিং বা নোট দেখতে না পায় | ✅ Active |
| **9** | **অপরিবর্তনযোগ্য অডিট লগ (AuditLog)** | প্রতিটি এন্ট্রি, পরিবর্তন, ডিলিট বা এসাইনমেন্টের অপরিবর্তনযোগ্য লগ | ✅ Active |
| **10**| **HMAC সাইনড অডিও ইউআরএল** | কল রেকর্ডিং অডিও ডাউনলোডের জন্য সময়-সীমাবদ্ধ এনক্রিপ্টেড লিংক | ✅ Active |
| **11**| **কল রেকর্ডিং ডাউনলোড অডিট লগ**| কে কখন কল রেকর্ডিং ডাউনলোড করল তা `RecordingDownloadLog`-এ ট্র্যাক | ✅ Active |
| **12**| **রোল-অ্যাওয়ার সাইডবার নেভিগেশন** | ইউজারের রোল অনুযায়ী শুধুমাত্র অনুমোদিত মেনু ও বাটন প্রদর্শিত হওয়া | ✅ Active |
| **13**| **ডাটা এক্সপোর্ট রেস্ট্রিকশন** | সাধারণ এক্সিকিউটিভ লিড ডাটাবেস এক্সপোর্ট করতে পারে না | ✅ Active |
| **14**| **এসকিউএল ইনজেকশন রোধ** | SQLAlchemy ORM প্যারামিটারাইজড কুয়েরি সুরক্ষা | ✅ Active |
| **15**| **ক্রস-সাইট স্ক্রিপ্টিং (XSS) স্যানিটাইজেশন**| সমস্ত ইনপুট ডেটায় HTML ও স্ক্রিপ্ট স্যানিটাইজার সক্রিয় | ✅ Active |
| **16**| **ব্রুট-ফোর্স রেট লিমিটিং** | বারবার ভুল পাসওয়ার্ড দিয়ে লগইন চেষ্টার বিরুদ্ধে রেট লিমিট | ✅ Active |
| **17**| **দ্বিমুখী ডাটাবেস ট্রানজাকশন সেফটি**| ডাবল-সেলিং ও ডাটা ইনকনসিস্টেন্সি রোধে ACID ট্রানজাকশন রোলব্যাক | ✅ Active |

---

## 8. সার্ভার ডিপ্লয়মেন্ট ও ভেরিফিকেশন প্রোটোকল

সর্বশেষ সমস্ত কোড লোকাল থেকে গিটহাবে পুশ করার পর আপনার উবুন্টু সার্ভারে আপডেট করার কমান্ড:

```bash
cd ~/Real-Estate-CRM
git pull
systemctl restart crm
journalctl -u crm -n 30 --no-pager
```

### ✅ ভেরিফিকেশন চেকলিস্ট:
1. **ব্রাউজারে প্রিন্ট বা PDF ডাউনলোড:**  
   [https://southeastlandmark.pythonicshariful.tech/manual.html](https://southeastlandmark.pythonicshariful.tech/manual.html) পেজে গিয়ে উপরের ডানপাশের **"Download / Print as PDF"** বাটনে চাপ দিলেই সম্পূর্ণ ডকুমেন্টটি একটি নিখুঁত অফিসিয়াল পিডিএফ রিপোর্ট হিসেবে সেভ বা প্রিন্ট হয়ে যাবে।
2. **বালক ইম্পোর্ট ও স্যাম্পল সিএসভি পরীক্ষা:**  
   [https://southeastlandmark.pythonicshariful.tech/leads.html](https://southeastlandmark.pythonicshariful.tech/leads.html)-এ গিয়ে **Import** চাপুন এবং **Download Sample CSV** দিয়ে ফাইলটি নামিয়ে চেক করুন।
3. **২০-কেপিআই রিপোর্ট স্পিড চেক:**  
   [https://southeastlandmark.pythonicshariful.tech/reports.html](https://southeastlandmark.pythonicshariful.tech/reports.html)-এ গেলে ০-মিলি-সেকেন্ডে ২০টি আর্কিটেকচারাল কার্ড লাইভ দেখতে পাবেন।
