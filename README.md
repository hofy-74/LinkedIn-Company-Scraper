# LinkedIn Company Scraper

**Streamlit + Selenium tool that looks up a company on LinkedIn and turns its
public profile into a structured, ever-growing Excel dataset — no manual
copy-pasting.**

`Python` · `Streamlit` · `Selenium` · `Pandas` · `OpenPyXL`

## Highlights
- **Search-then-confirm flow** — searches LinkedIn for close name matches
  and lets you pick the right company before scraping, instead of guessing
  a single URL.
- **Session validation, not blind scraping** — checks the cookie file is
  well-formed and actually authenticated before touching a company page, so
  a stale session fails fast with a clear message instead of quietly
  scraping a login wall.
- **Modular codebase** — UI (`app.py`), Selenium logic (`scraper.py`), and
  cookie/session handling (`cookies_utils.py`) are separated behind a single
  `config.py`, not one monolithic script.
- **Idempotent by design** — writes to the Excel dataset only on an actual
  scrape, deduplicates rows, and never double-writes on a Streamlit rerun.

## Project structure
```
linkedin-company-scraper/
├── app.py              # Streamlit UI
├── config.py            # settings: cookie path, Excel path, timeouts
├── cookies_utils.py      # cookie loading, validation, login-state checks
├── scraper.py             # Selenium: browser setup, search, field extraction
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

---

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
