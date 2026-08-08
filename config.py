"""
Central configuration for the LinkedIn Company Scraper.

Keeping these in one place means app.py, scraper.py, and cookies_utils.py
never disagree about paths/timeouts, and you only edit one file to change
behavior instead of hunting through the Streamlit script.
"""
import os

# Fixed path to the pickled LinkedIn session cookies (li_at, JSESSIONID, ...).
# No more upload widget - drop the file next to app.py (or point the env var
# at it) and every run picks it up automatically.
# IMPORTANT: this file is equivalent to a live login session for whichever
# account it was exported from. Never commit it, never share it - add it to
# .gitignore. Treat it like a password, not like sample data.
COOKIES_PATH = os.environ.get("LINKEDIN_COOKIES_PATH", "linkedin_cookies.pkl")

# Headless is no longer a checkbox - it's always on. A visible Chrome window
# adds nothing here and just makes the tool harder to run on a server.
HEADLESS = True

EXCEL_PATH = os.environ.get("LINKEDIN_EXCEL_PATH", "linkedin_company_data.xlsx")

MAX_SEARCH_RESULTS = 6
ELEMENT_WAIT_TIMEOUT = 25        # seconds - ceiling for explicit WebDriverWait calls
LOGIN_CHECK_TIMEOUT = 15         # seconds - how long to wait for a redirect off /login or /checkpoint

# Randomized pause between page actions (search -> open page -> read DOM).
# This is about not hammering the site with back-to-back requests, not a
# claim that it defeats LinkedIn's bot detection - it doesn't, and scraping
# with a personal session cookie still breaks LinkedIn's Terms of Service
# regardless of timing. Use this tool sparingly on your own account's risk.
MIN_ACTION_DELAY = 2.0
MAX_ACTION_DELAY = 5.0

# A cookie file without this cookie isn't an authenticated session at all -
# fail fast instead of driving a browser through a login wall for a minute
# before erroring out.
REQUIRED_COOKIE_NAMES = {"li_at"}
