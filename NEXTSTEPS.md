# GameWatch™ — Product Roadmap & Next Steps

This document outlines the complete technical, operational, and commercial strategy for finalizing GameWatch, transitioning from deployment to real-world lounge pilot testing, packaging the mobile app, streaming architecture, and launching the monetization system.

---

## 1. Offline vs. Cloud Hybrid Architecture

GameWatch is designed as an **Edge-First Hybrid System**, built specifically to withstand Ethiopian power interruptions and Ethio Telecom internet outages.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   PHYSICAL GAMING LOUNGE (LOCAL LAN)                   │
│                                                                        │
│   [Android Phone / Camera]                [PlayStation 5 TV Screen]    │
│              │                                        │                │
│              ▼ (Local Wi-Fi Stream - 0 Internet)      │                │
│     ┌──────────────────────────────────────────────┐  │                │
│     │         LOUNGE EDGE NODE (PC / LAPTOP)       │◄─┘                │
│     │  - OpenCV Computer Vision Score Engine       │                   │
│     │  - Local SQLite Database (<1ms latency)      │                   │
│     │  - Local Cash & Session Ledger               │                   │
│     └──────────────────────┬───────────────────────┘                   │
└────────────────────────────┼───────────────────────────────────────────┘
                             │
            Internet Reconnects / Periodic Sync
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 CLOUD PLATFORM (Render & Cloudflare D1)                │
│                                                                        │
│   - Global Owner Dashboard (Live Revenue, TV Status)                   │
│   - UEFA Champions League Public Tournaments & Live Standings          │
│   - Multi-Device PWA Access (Bole, 4 Kilo, Remote Monitoring)          │
└────────────────────────────────────────────────────────────────────────┘
```

### How Offline Operation Works:
1. **Zero Internet Video Processing**:
   - The camera (DroidCam, IP Webcam, or USB camera) connects directly to the local lounge PC over the local Wi-Fi router subnet (`192.168.x.x`).
   - Frame capture and score detection happen 100% locally on the PC with zero internet data usage and zero latency (< 15ms).
2. **Local Session & Cash Persistence**:
   - Matches played, game durations, clerk cash audits, and billing totals are written directly to local SQLite database tables.
   - If the internet goes down for 8 hours, the lounge clerk continues starting sessions, recording matches, and collecting cash without interruption.
3. **Automatic Cloud Synchronization**:
   - The background worker (`CloudSyncManager`) continuously monitors internet reachability.
   - Once an active connection is detected, all offline transaction batches, completed tournament fixtures, and audit logs automatically sync to Cloudflare D1 and your Render cloud dashboard.
4. **PWA Offline Screen Caching**:
   - The mobile web client caches core CSS, fonts, and interface structures in the device's service worker cache.
   - If a phone temporarily loses cellular data, the user interface remains responsive and loads without white-screen errors.

---

## 2. Camera Streaming Architecture ("The Stream We Use")

To keep hardware costs affordable for lounge owners, GameWatch uses flexible, commodity hardware streaming:

### Supported Camera Sources & Ingestion Protocols
1. **DroidCam (Recommended Mobile Camera)**:
   - **Protocol**: HTTP MJPEG video stream (`http://<phone_ip>:4747/video`).
   - **Format**: 30 FPS, resolutions up to 1920×1080.
   - **Cost**: Uses existing spare Android phones; zero extra hardware cost.
2. **IP Webcam for Android**:
   - **Protocol**: HTTP MJPEG stream (`http://<phone_ip>:8080/video`).
   - **Format**: Lightweight video feed with adjustable compression and low CPU overhead.
3. **USB Webcams & HDMI Capture Cards**:
   - **Protocol**: Direct camera hardware index (`0`, `1`, `2`) via OpenCV DirectShow / V4L2.
   - **Ideal for**: Fixed counter setups where cameras are cabled directly into the lounge computer.
4. **RTSP Security / CCTV Cameras**:
   - **Protocol**: `rtsp://<username>:<password>@<ip>:554/stream`.
   - **Ideal for**: Commercial lounges that already have overhead security dome cameras installed.

### Bandwidth & Performance Optimization
* **Local LAN Pipeline**:
  - Video streams do **not** upload to the cloud. They travel strictly over the local Wi-Fi router, consuming **0 MB of ISP internet bandwidth**.
* **Perspective Rectification (Keystone Correction)**:
  - Cameras do not need to be placed directly in front of the TV.
  - Owners can place cameras on a high corner mount and tap 4 corners on the TV screen in GameWatch to digitally unwarp the screen into a flat 16:9 rectangle.
* **Scoreboard Cropping & Glare Suppression**:
  - The vision engine crops only the upper scoreboard zone (saving 90% CPU processing power).
  - Software anti-glare filtering removes harsh window and ceiling light reflections.
* **Cloud Relay for Remote Owners**:
  - When an owner is outside the lounge and wants to see live TV previews from home, the local agent pushes low-bandwidth thumbnail snapshots (1 frame per 3 seconds) through a lightweight secure tunnel (Cloudflare Tunnel or ngrok) rather than streaming heavy high-definition video.

---

## 3. Android App Strategy & Build Pipeline

GameWatch is designed mobile-first. There are two straightforward paths to distribute the Android app to lounge owners, clerks, and players:

### Path A: Progressive Web App (PWA) — Ready Immediately
GameWatch is already configured with a PWA web manifest, service worker caching, and mobile viewport optimization.

* **How to Install**:
  1. Open the live URL (`https://gamewatch.onrender.com` or custom domain) on Google Chrome on Android.
  2. Tap the three dots menu (`⋮`) -> select **"Install App"** (or **"Add to Home Screen"**).
  3. The app installs with a branded GameWatch app icon.
* **Benefits**:
  - Full-screen immersion (removes browser URL bar and navigation buttons).
  - Instant Over-The-Air updates whenever code is pushed to GitHub.
  - No Google Play developer fees or app store review delays.

### Path B: Native Android Package (`.apk` / `.aab`) via Bubblewrap (TWA)
To distribute an official Android installation file (`.apk`) via Telegram or publish to the **Google Play Store**:

* **Technology**: Google **Bubblewrap** CLI (Trusted Web Activity).
* **Build Steps**:
  ```bash
  # 1. Install Google Bubblewrap CLI
  npm install -g @bubblewrap/cli

  # 2. Initialize project from live GameWatch URL
  bubblewrap init --manifest=https://gamewatch.onrender.com/manifest.json

  # 3. Build signed production APK and AAB
  bubblewrap build
  ```
* **Output**:
  - `app-release-signed.apk`: Direct download file to send to lounge owners.
  - `app-release-bundle.aab`: Store bundle for Google Play Store listing.
* **Future Native Extension (Hardware Thermal Printer)**:
  - If lounges require printing physical 58mm Bluetooth cash receipts, wrap the codebase in **CapacitorJS** (`@capacitor/core`) to access Bluetooth printer hardware.

---

## 4. Monetization System (Business Model & Revenue Streams)

GameWatch operates on a multi-tier SaaS and transaction-fee model tailored to the Ethiopian gaming lounge market:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        GAMEWATCH REVENUE ENGINE                        │
├───────────────────┬───────────────────┬────────────────────────────────┤
│ 1. SaaS License   │ 2. Tournament Fee │ 3. Brand Sponsorships          │
│    500–800 ETB    │    10% Pool Cut   │    Hardware & ISP Ad Banners   │
│    per TV / month │    + Loser Margins│    (ShebaTech, Fiber, Energy)  │
└───────────────────┴───────────────────┴────────────────────────────────┘
```

### Revenue Stream 1: Monthly Station SaaS Subscription
Lounge owners pay a monthly subscription fee based on the number of active PlayStation stations:
* **Starter Plan (Small Lounges, 1–4 TVs)**:
  - **Price**: **500 ETB / station / month** (e.g. 4 TVs = 2,000 ETB / month).
  - **Features**: Automatic match counting, cashier shift auditing, fraud prevention, daily revenue metrics.
* **Pro Plan (Standard Lounges, 5–10 TVs)**:
  - **Price**: **700 ETB / station / month** (e.g. 8 TVs = 5,600 ETB / month).
  - **Features**: Starter features + UEFA Champions League tournament engine, Telebirr & CBE digital settlement, remote phone monitoring.
* **Enterprise Plan (Chains & Game Arenas, 10+ TVs)**:
  - **Price**: Custom annual contract (discounted per station) with dedicated onsite hardware setup and priority support.

### Revenue Stream 2: Tournament Platform Fees
UEFA Champions League tournaments generate significant cash flow for lounges:
* **Host Commission**:
  - GameWatch takes a **10% platform fee** on total player registration pools (e.g., 32 players @ 200 ETB = 6,400 ETB pool -> 640 ETB platform fee per tournament).
* **Loser Match Fee Automated Engine**:
  - Lounges collect 25 ETB from the loser of every tournament match (125 matches in a 32-player tournament = 3,125 ETB in loser fees).
  - Automated tracking prevents clerks from pocketing match fees and ensures accurate ledger accounting.

### Revenue Stream 3: Brand Sponsorships & Digital Billboards
Built directly into the GameWatch interface are premier ad slots:
* **Premier Hero Billboard** (e.g., ShebaTech Gaming, PS5 controller repair, high-speed fiber internet).
* **Lounge Discovery Strip** (promoted energy drink partners, local snacks, hardware wholesale stores).
* **Commercial Model**: Charge gaming hardware suppliers and local telecom partners **2,500 – 5,000 ETB / month** for targeted impressions among console gamers and lounge owners.

### Revenue Stream 4: Hardware Starter Kit (One-Time Setup Fee)
* **The "Lounge Box" Kit**:
  - Sell a pre-configured hardware kit: 2 phone tripod mounts, power splitters, and software installation setup.
  - **Price**: **3,000 – 5,000 ETB one-time setup charge**.

---

## 5. Lounge Beta Testing & Product Finalization Plan

To transition smoothly from code completion to real-world adoption, execute the following 5-stage testing protocol:

### Stage 1: Feature & Role Verification (Self-Testing)
- [x] Register new Lounge Owner account (`/api/auth/register`).
- [x] Confirm unique lounge name and code display properly in drawer menu and settings.
- [x] Test Clerk workflow: Start session, record games, complete cash checkout.
- [x] Test Tournament engine: Seed 32-player roster, run 3D lottery ball draw, record scores, verify standings.
- [x] Verify role restrictions: Gamers cannot view owner revenue; clerks cannot modify hourly rates.

### Stage 2: Closed Beta in Pilot Gaming Lounge (The First Real Trial)
1. **Select Pilot Location**:
   - Partner with 1 gaming lounge in Addis Ababa (e.g. 4 Kilo or Bole).
2. **Mount Hardware**:
   - Place 2 spare Android phones on tripods pointing at 2 active PS5 stations.
3. **Execute "Shadow Testing" (3–5 Days)**:
   - The clerk continues using their normal paper notebook as usual.
   - GameWatch runs silently in parallel on the 2 stations.
   - At closing each night, reconcile the ledger:
     * *Did GameWatch match count equal the clerk's manual tally?*
     * *Were any goals or matches missed or double-counted?*
     * *Did the collected cash match the GameWatch ledger total?*

### Stage 3: Vision Engine & Environmental Stress Testing
* **Lighting Variations**: Test during sunny afternoons (window glare on screens) vs. nighttime LED lighting.
* **Obstruction Tolerance**: Verify that people walking past the TV or celebrating in front of the camera do not falsely trigger goals.
* **Camera Angles**: Validate that the keystone unwarping handles cameras mounted at up to 45-degree angles from the side or ceiling.

### Stage 4: Gamer Tournament Beta
1. Host a live 16-player mini FIFA / EA FC tournament at the pilot lounge over the weekend.
2. Place a printed QR code on the lounge wall leading to the live GameWatch web link.
3. Gamers scan the code on their smartphones to follow live fixtures, score updates, and group standings.
4. Gather direct feedback on readability, excitement, and engagement.

### Stage 5: Commercial SaaS Launch
* Once the pilot lounge achieves 100% billing accuracy over 7 continuous days with zero discrepancies, onboard the next 5 commercial lounges across Addis Ababa.

---

*Document created: October 2026 · GameWatch™ by TSEGA Labs*
