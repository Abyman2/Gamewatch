# GameWatch Cloud Deployment Guide (100% Free Tier)

This document provides a comprehensive, step-by-step production deployment guide for **GameWatch**, targeting cloud container hosts (**Render.com**, **Koyeb**, **Railway**) with zero upfront costs and a free permanent HTTPS subdomain.

---

## 1. Cloud Architecture Overview

| Component | Cloud Implementation | Details |
|---|---|---|
| **Frontend** | Vanilla JS + HTML5 + CSS3 | Served directly via Flask [`templates/index.html`](file:///templates/index.html) and [`static/`](file:///static/) |
| **Backend** | Python 3.11 (Flask + Gunicorn) | REST API engine in [`app_server.py`](file:///app_server.py) on Port `5000` |
| **Computer Vision / AI** | OpenCV + NumPy | Headless OpenCV (`libgl1`, `libglib2.0-0`) in [`Dockerfile`](file:///Dockerfile) |
| **Database** | SQLite (`gamewatch.db`) | Local database for stations, sessions, UEFA tournaments, and ledger |
| **Domain** | Free Managed Subdomain | `https://gamewatch.onrender.com` with free automated SSL/TLS (HTTPS) |

---

## 2. Zero-Cost Domain Strategy

You **do not need to purchase a custom domain** to start operating.
- Platforms like Render provide a permanent free subdomain (e.g., `https://gamewatch.onrender.com`).
- Includes automatic SSL/TLS certificate (Green lock in browsers).
- Any customer, clerk, or owner can open it from phones, tablets, and laptops worldwide.
- When ready to connect a custom domain (e.g. `gamewatch.et` or `gamewatchlounge.com`), you can bind it in **Render Settings > Custom Domains** without changing code.

---

## 3. Step-by-Step Deployment (Render.com Free Tier)

### Step 1: Create a Render Account
1. Open [render.com](https://render.com).
2. Click **"Get Started"** or **"Sign In"**.
3. Select **"Sign in with GitHub"** to link your GitHub repository.

### Step 2: Create a New Web Service
1. In the Render Dashboard, click **"New +"** in the top-right corner.
2. Select **"Web Service"**.
3. Choose **"Build and deploy from a Git repository"** and click **Next**.
4. Click **"Connect"** next to your `GameWatch` repository.

### Step 3: Configure Web Service Parameters
Fill in the configuration fields:

| Configuration | Value | Rationale |
|---|---|---|
| **Name** | `gamewatch` | Sets URL to `https://gamewatch.onrender.com` |
| **Region** | **Frankfurt (EU Central)** | Lowest latency routes to Ethiopia / East Africa |
| **Branch** | `main` | Deploys your primary production branch |
| **Runtime / Environment** | **Docker** | Detects [`Dockerfile`](file:///Dockerfile) with all OpenCV libraries |
| **Instance Type** | **Free ($0/month)** | Free tier container allocation |

### Step 4: Configure Environment Variables
Under the **"Advanced"** section, click **"Add Environment Variable"**:

1. **`FLASK_ENV`** $\rightarrow$ `production`
2. **`PORT`** $\rightarrow$ `5000`
3. **`SECRET_KEY`** $\rightarrow$ Click **Generate** (or enter a 32-character random string)
4. **`OPENCV_FFMPEG_CAPTURE_OPTIONS`** $\rightarrow$ `rtsp_transport;tcp|fflags;nobuffer|max_delay;0`

### Step 5: Deploy the Web Service
1. Click **"Create Web Service"**.
2. Render initiates the build pipeline:
   - Pulls Docker base image (`python:3.11-slim`).
   - Installs Linux dependencies (`libgl1`, `libglib2.0-0`, `libgomp1`, `curl`).
   - Installs dependencies from [`requirements.txt`](file:///requirements.txt).
   - Starts [`app_server.py`](file:///app_server.py).
3. Within 2 to 3 minutes, the deployment log confirms:  
   `==> Your service is live at https://gamewatch.onrender.com`

---

## 4. Alternative Free Cloud Hosts

- **Koyeb ([koyeb.com](https://www.koyeb.com))**: Free Eco Nano instance with automatic Docker detection from GitHub and free `*.koyeb.app` domain. Doesn't sleep on idle.
- **Railway ([railway.app](https://railway.app))**: $5/mo free trial credit with instant `*.up.railway.app` subdomain and GitHub auto-sync.

---

## 5. Post-Deployment Verification Checklist

1. [ ] Navigate to `https://gamewatch.onrender.com` on a mobile device and PC.
2. [ ] Test **Stations Dashboard**: Verify TV 1 and TV 2 status cards and checkout flow.
3. [ ] Test **Champions League Tournament Hub**: Create 32-player tournament, run Glass Tumbler draw, review live group tables and owner profit analytics.
4. [ ] Test **Clerk Access PIN Modal**: Verify Clerk access code protects sensitive operational tools.
