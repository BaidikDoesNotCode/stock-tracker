# Diecast Stock Tracker 

A **100% free, automated new-product detector** , watches e-commerce listing pages using github cron and emails you the moment anything new is added.

---

## How It Works

```
GitHub Actions (cron every 30 min)
        │
        ▼
   main.py loads watchlist.yaml
        │
        ▼
   Scrapes each listing page → extracts ALL product names + URLs
   ┌──────────────┬──────────────┬──────────────────┐
   │ Shopify JSON │  requests +  │    Playwright     │
   │  API (fast)  │  BS4 (SSR)   │ (JS-rendered SPAs)│
   │ giftgalaxy   │ kolkatakomics│ karzanddolls      │
   │ 1isto64      │              │ keraladiecastcars  │
   └──────────────┴──────────────┴──────────────────┘
        │
        ▼
   checker.py compares against snapshot.json
   (what was there last time?)
        │
        ▼
   New items? → notifier.py → Gmail SMTP → Your inbox 📧
        │
        ▼
   Saves updated snapshot.json → git push
```

### First-Run Behavior

On the **very first run**, the scraper saves all existing products as a baseline — **no email is sent**. Starting from the **second run**, only truly NEW additions trigger an alert. This prevents a flood of hundreds of "new" items on initial deployment.

---

## Sites Monitored

| Site | Scraper | Strategy | Speed |
|---|---|---|---|
| **karzanddolls.com** | `karzanddolls` | Playwright (Angular SPA) | ~10s |
| **giftgalaxy.in** | `giftgalaxy` | Shopify JSON API | ~1s |
| **1isto64.com** | `1isto64` | Shopify Collection JSON API | ~1s |
| **keraladiecastcars.com** | `keraladiecastcars` | Playwright (Wix) | ~10s |
| **kolkatakomics.com** | `kolkatakomics` | requests + BS4 (Wix SSR) | ~2s |
| **notatoy.com** | `notatoy` | Stub (DNS dead) | instant |

---

## File Structure

```
stock-tracker/
├── .github/workflows/scrape.yml    # Cron + snapshot git push
├── scrapers/
│   ├── __init__.py                 # Scraper registry
│   ├── base.py                     # ProductEntry, ListingResult, BaseScraper
│   ├── karzanddolls.py             # Playwright (Angular SPA)
│   ├── giftgalaxy.py               # Shopify JSON API
│   ├── isto64.py                   # Shopify Collection JSON API
│   ├── keraladiecastcars.py        # Playwright (Wix)
│   ├── kolkatakomics.py            # requests + BS4 (Wix SSR)
│   └── notatoy.py                  # Stub
├── watchlist.yaml                  # Listing pages to watch
├── snapshot.json                   # Auto-generated: known products (do not edit)
├── main.py                         # Entry point
├── checker.py                      # Snapshot comparison logic
├── notifier.py                     # Gmail email sender
├── requirements.txt
└── README.md
```

---

## Setup (5 steps)

### 1 — Push to GitHub

### 2 — Add listing pages
Edit `watchlist.yaml`. Each entry:

| Field | Description |
|---|---|
| `name` | Human-readable label (shown in email) |
| `url` | Listing/collection page URL |
| `scraper` | One of: `karzanddolls`, `giftgalaxy`, `1isto64`, `keraladiecastcars`, `kolkatakomics` |

### 3 — Create a Gmail App Password
1. [myaccount.google.com/security](https://myaccount.google.com/security) → enable **2-Step Verification**
2. **App Passwords** → select "Mail" → **Generate**
3. Copy the 16-character password

### 4 — Add GitHub Secrets
**Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `GMAIL_USER` | Your Gmail address |
| `GMAIL_PASS` | 16-char App Password |
| `NOTIFY_EMAIL` | Recipient email (optional; defaults to `GMAIL_USER`) |

### 5 — Enable GitHub Actions
**Actions tab** → enable workflows. It will run every 5 minutes automatically.

---

## Local Testing

```bash
pip install -r requirements.txt
playwright install chromium

# First run — saves baseline, no email
python main.py --dry-run

# Second run — detects new items
python main.py --dry-run

# Test only one page
python main.py --dry-run --page "Mini GT"

# Reset snapshot (start over)
python main.py --reset

# Full run with email
GMAIL_USER=you@gmail.com GMAIL_PASS=xxxx python main.py
```

---

## Adding a New Site

1. Create `scrapers/newsite.py` — implement `scrape_listing(page) → ListingResult`
2. Register in `scrapers/__init__.py`
3. Add listing pages in `watchlist.yaml` with `scraper: newsite`

### Choosing the right strategy

| Strategy | When to use |
|---|---|
| Shopify JSON API | Site is Shopify (check footer for "Powered by Shopify") |
| requests + BS4 | Product names appear in `View Source` / `curl` output |
| Playwright | Products only appear after JavaScript runs |


