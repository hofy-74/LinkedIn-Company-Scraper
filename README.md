# LinkedIn Company Scraper (Streamlit)

A small Streamlit tool that searches for a company on LinkedIn, opens its
About page, and extracts: name, overview, industry, company size, type,
headquarters, founding year, location, and associated member count. Each
result is appended to a running Excel dataset (`linkedin_company_data.xlsx`)
that can be downloaded from the app itself.

## Project structure
```
config.py          # all settings in one place (cookie path, Excel path, timeouts)
cookies_utils.py    # cookie loading/validation and login-state checks
scraper.py           # Selenium logic: browser setup, search, page extraction
app.py                # Streamlit UI only
requirements.txt
packages.txt          # system packages (Chromium) for Streamlit Community Cloud
```

## Running locally
Requires Chrome + a matching chromedriver on the machine.

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Session cookies
The app reads LinkedIn session cookies from a fixed path instead of an
upload widget:

- By default it looks for `linkedin_cookies.pkl` next to `app.py`.
- The path can be overridden with an environment variable:
  ```bash
  export LINKEDIN_COOKIES_PATH=/path/to/linkedin_cookies.pkl
  ```

If you don't have that file yet, run a separate script once to log in
normally through a real browser and save the cookies:
```python
pickle.dump(driver.get_cookies(), open("linkedin_cookies.pkl", "wb"))
```

Before using the file, the app checks that it exists, is valid pickle data,
and contains an `li_at` cookie (the session cookie for an authenticated
account). If the session has expired, the app fails with a clear message
instead of silently scraping an empty login page.

**This file represents a live login session for your account — never commit
it, add it to `.gitignore`, and treat it like a password, not sample data.**

## Headless mode
The browser always runs headless — there's no toggle for it anymore, so
behavior stays identical whether you run this locally or on a server.

## Deploying on Streamlit Community Cloud
Streamlit Cloud's containers don't ship a real browser, so `packages.txt`
(included in this repo) tells it to install Chromium + chromedriver via
apt:
```
chromium
chromium-driver
```
`scraper.py` auto-detects the installed binaries; no extra config is
needed. If it still can't find them, set `CHROME_BINARY_PATH` and
`CHROMEDRIVER_PATH` in the app's secrets/environment to their installed
paths (typically `/usr/bin/chromium` and `/usr/bin/chromedriver`).

Two caveats worth knowing before relying on this in production:
- Streamlit Cloud's shared IPs are more likely to trigger LinkedIn's
  checkpoint/verification pages than a residential IP, independent of
  anything in this code.
- You'll also need to get `linkedin_cookies.pkl` onto the deployed
  container — Streamlit Cloud's filesystem resets on redeploy, so this is
  really only practical for local or self-hosted (e.g. a VPS) use rather
  than a long-running cloud deployment.

## Notes
- Automated scraping of LinkedIn **violates its Terms of Service** and can
  put the account behind the cookies at risk of restriction or a ban. The
  app adds a randomized delay between steps (search → open page → read data)
  so requests don't fire in an obviously mechanical pattern, but that's not
  a guarantee against detection — use this sparingly, in small volumes, and
  avoid running it repeatedly on the same account.
- The app is built on `Selenium`, so it needs a real Chrome browser +
  chromedriver on the machine it runs on. That makes it awkward to host on
  Streamlit Community Cloud (no real browser there); running it locally or
  on a server you control (e.g. a VPS) is the better fit.
- The selectors (regex and DOM lookups in `scraper.py`) depend on LinkedIn's
  current page layout. If LinkedIn changes its design, those may need
  updating.
