# Humblebrag Dashboard

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Built with Dash](https://img.shields.io/badge/Built%20with-Dash-orange)](https://dash.plotly.com/)
[![Build Status](https://github.com/ak91hu/HumblebragDashboard/actions/workflows/daily_update.yml/badge.svg)](https://github.com/ak91hu/HumblebragDashboard/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Where Python scripts meet runner's high.**

A fully automated, interactive analytics dashboard for Strava data. It visualizes year-over-year progression, tracks gamified challenges, and scientifically calculates how many slices of pizza you've earned.

**👀 Live Demo:** [LINK TO YOUR RENDER APP HERE] *(e.g., https://humblebrag-dashboard.onrender.com)*

---

## 🚀 Key Features

### 📊 Deep Analytics
* **Year-over-Year Battle:** Cumulative distance charts to track if you are beating your previous years.
* **GitHub-Style Heatmap:** A beautiful calendar grid showing daily activity intensity.
* **Detailed Trends:** Rolling averages, weekly volume, and heart rate zone analysis.
* **Activity Log:** A filterable list of recent activities with direct links to Strava.

### 🏔️ Gamification & "Humblebrags"
* **Gastro Conversion:** Converts burned calories into **Pizza** 🍕, **Beers** 🍺, **Burgers** 🍔, and **Donuts** 🍩.
* **Elevation Challenges:** Visual progress bars tracking your ascent against **Mount Everest** and **Kékes-tető**.
* **Streak Tracker:** Calculates your longest consecutive days of activity.

### 🤖 Zero-Maintenance Automation
* **Automated Sync:** A GitHub Action robot wakes up every morning (06:00 UTC) to fetch new data.
* **Incremental Updates:** Smartly fetches only new activities to respect API limits.
* **Free Hosting:** Designed to run on the free tiers of Render (Web) and GitHub Actions (Data).

---

## 🛠️ Tech Stack

* **Frontend & Logic:** [Dash (Plotly)](https://dash.plotly.com/) + Bootstrap Components
* **Data Manipulation:** Pandas
* **API Integration:** `stravalib`
* **Automation:** GitHub Actions (Cron Job)
* **Deployment:** Gunicorn (Production WSGI)

---

## ⚙️ How to Run (Fork This Repo)

Want your own dashboard? You don't need to code. Just follow these steps:

### 1. Fork & Clone
Click the **Fork** button in the top-right corner of this page to save a copy to your GitHub account.

### 2. Get Strava API Credentials
1. Go to [Strava API Settings](https://www.strava.com/settings/api).
2. Create an app (Category: "Visualizer", Callback Domain: `localhost`).
3. Copy your `Client ID` and `Client Secret`.

### 3. Generate a Refresh Token
*Crucial Step:* You need a token with `activity:read_all` permissions.
1. Paste your Client ID into this URL and open it:
   `https://www.strava.com/oauth/authorize?client_id=[YOUR_CLIENT_ID]&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=activity:read_all`
2. Authorize the app.
3. Copy the code from the resulting URL (`code=...`).
4. Exchange this code for a Refresh Token using `curl` or a simple Python script.

### 4. Set GitHub Secrets
Go to your forked repo > **Settings** > **Secrets and variables** > **Actions** and add:
* `STRAVA_CLIENT_ID`
* `STRAVA_CLIENT_SECRET`
* `STRAVA_REFRESH_TOKEN`

### 5. Trigger the Data Sync
Go to the **Actions** tab > **Strava Daily Sync** > **Run workflow**.
*This will create the `data/activities.csv` file.*

### 6. Deploy to Render (Free)
1. Create an account on [Render.com](https://render.com).
2. Click **New +** > **Web Service**.
3. Connect your GitHub repo.
4. Settings:
   * **Runtime:** Python 3
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `gunicorn app:server`
5. **Environment Variables:** Add the same 3 secrets (ID, Secret, Token) here as well.
6. Click **Create Web Service**.

---

## 📂 Project Structure

```text
HumblebragDashboard/
├── .github/workflows/
│   └── daily_update.yml   # The daily cron job
├── data/
│   └── activities.csv     # Generated database (do not edit manually)
├── scripts/
│   └── update_data.py     # The data fetcher bot
├── app.py                 # The main Dash application
├── Procfile               # Render deployment config
└── requirements.txt       # Python dependencies
