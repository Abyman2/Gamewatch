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

## 4. Option 1: Permanent Cloud Database on Cloudflare D1 (100% Free Forever)

While the container runs fine with embedded SQLite, free containers on Render reset their ephemeral disk on rebuilds. By connecting **Cloudflare D1** (Cloudflare's serverless edge SQLite database), your tournaments, user accounts, and financial records **never disappear** — with zero cost and zero sleeping.

### Why Cloudflare D1?
| Feature | Cloudflare D1 | Render Free Postgres | Supabase Free |
|---|---|---|---|
| **Cost** | **$0.00 / Month Forever** | Free 30 days only | Free |
| **Storage** | **10 GB (Huge for SQLite)** | 1 GB | 500 MB |
| **Read Limit** | **5,000,000 queries / day** | Connection limited | Rate limited |
| **Write Limit** | **100,000 queries / day** | Connection limited | Rate limited |
| **Sleep on Idle** | **NEVER SLEEPS (Edge)** | Sleeps / Pauses | Pauses after 7 days |
| **Compatibility** | **100% SQLite Native** | Requires Postgres SQL rewrite | Requires Postgres SQL rewrite |

---

### Step-by-Step Cloudflare D1 Setup:

#### Step 1: Create a Free Cloudflare Account
1. Visit [dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up).
2. Sign up with your email (100% free, no credit card required).

#### Step 2: Create the D1 Database
1. In the left navigation menu, click **Workers & Pages**.
2. Click the **D1 SQL Database** tab.
3. Click the blue **"Create database"** button.
4. Enter the database name: `gamewatch-db`.
5. Click **"Create"**.
6. On the overview page, copy your **Database ID** (a UUID like `a1b2c3d4-e5f6-7890-abcd-1234567890ab`).

#### Step 3: Copy Your Account ID
1. Look at your browser URL bar: `dash.cloudflare.com/<YOUR_ACCOUNT_ID>/workers-and-pages...`
2. Or on the **Workers & Pages > Overview** page, copy your **Account ID** from the right sidebar.

#### Step 4: Generate a Cloudflare API Token
1. In the top-right corner of the Cloudflare dashboard, click your **User Icon** > **My Profile**.
2. In the left sidebar, click **API Tokens**.
3. Click **"Create Token"**.
4. Scroll down to **"Custom Token"** and click **"Get started"**.
5. Configure:
   - **Token name**: `GameWatch-D1-Token`
   - **Permissions**: Select **Account** | **D1** | **Edit**
   - **Account Resources**: Select **Include** | **All accounts** (or your specific account)
6. Click **"Continue to summary"** and then **"Create Token"**.
7. Copy your secret API Token (Cloudflare only displays this once!).

---

#### Step 5: Connect Cloudflare D1 to Render (or Local)

##### In Render:
1. Open your Render Dashboard > Web Service `gamewatch`.
2. Click **Environment** in the left menu.
3. Click **"Add Environment Variable"** and enter:
   - `CLOUDFLARE_ACCOUNT_ID` = *(your Account ID)*
   - `CLOUDFLARE_D1_DATABASE_ID` = *(your Database ID)*
   - `CLOUDFLARE_API_TOKEN` = *(your API Token)*
4. Click **"Save Changes"**.

Render will automatically restart. Upon boot, GameWatch connects to Cloudflare D1, auto-provisions all 16 tables, and restores/persists all data permanently at the edge!

##### Locally (One-Click Migration CLI):
You can also provision and push your local database to Cloudflare D1 instantly from your terminal:
```bash
python deploy_d1.py --account-id <YOUR_ACCOUNT_ID> --database-id <YOUR_DB_ID> --token <YOUR_TOKEN>
```
This automatically runs the schema migration and uploads all current stations, events, registrations, and transactions to the Cloudflare edge.

---

## 5. Alternative Free Cloud Hosts

- **Koyeb ([koyeb.com](https://www.koyeb.com))**: Free Eco Nano instance with automatic Docker detection from GitHub and free `*.koyeb.app` domain. Doesn't sleep on idle.
- **Railway ([railway.app](https://railway.app))**: $5/mo free trial credit with instant `*.up.railway.app` subdomain and GitHub auto-sync.

---

## 6. Post-Deployment Verification Checklist

1. [ ] Navigate to `https://gamewatch.onrender.com` on a mobile device and PC.
2. [ ] Test **Stations Dashboard**: Verify TV 1 and TV 2 status cards and checkout flow.
3. [ ] Test **Champions League Tournament Hub**: Create 32-player tournament, run Glass Tumbler draw, review live group tables and owner profit analytics.
4. [ ] Test **Clerk Access PIN Modal**: Verify Clerk access code protects sensitive operational tools.
5. [ ] Test **Cloudflare D1 Status**: Navigate to `/api/system/d1_status` to verify edge database connectivity and table counts.
6. [ ] Test **Restart Persistence**: Trigger a manual redeploy in Render; verify all registered users and tournament data remain intact!
