"""
Cookie loading / validation helpers.

Split out of app.py so the Streamlit script stays focused on UI, and so
these checks are unit-testable without spinning up Streamlit.
"""
import pickle
import random
import time

from config import (
    REQUIRED_COOKIE_NAMES,
    MIN_ACTION_DELAY,
    MAX_ACTION_DELAY,
    LOGIN_CHECK_TIMEOUT,
)


class CookieError(Exception):
    """Missing/malformed cookie file, or a session that isn't actually authenticated."""


def load_cookie_file(path: str):
    """Read + validate the pickle file. Raises CookieError with a message
    that's actually useful instead of a raw pickle/OSError traceback."""
    try:
        with open(path, "rb") as f:
            cookies = pickle.load(f)
    except FileNotFoundError:
        raise CookieError(
            f"ملف الكوكيز مش موجود: {path}\n"
            "تأكد إنه موجود في نفس مجلد المشروع أو غيّر LINKEDIN_COOKIES_PATH."
        )
    except (pickle.UnpicklingError, EOFError) as e:
        raise CookieError(f"ملف الكوكيز تالف أو مش بصيغة pickle صحيحة: {e}")

    if not isinstance(cookies, list) or not cookies:
        raise CookieError("ملف الكوكيز فاضي أو شكله مش زي المتوقع (لازم يكون list of dicts).")

    names = {c.get("name") for c in cookies if isinstance(c, dict)}
    missing = REQUIRED_COOKIE_NAMES - names
    if missing:
        raise CookieError(
            "الكوكيز ناقصة كوكي أساسي للجلسة ({}). "
            "غالبًا الجلسة منتهية - سجّل دخول تاني بسكريبت منفصل وصدّر الكوكيز من جديد."
            .format(", ".join(missing))
        )
    return cookies


def apply_cookies(driver, cookies):
    """Load linkedin.com once so the cookie domain matches, inject the
    cookies, then refresh to pick them up."""
    driver.get("https://www.linkedin.com")
    for cookie in cookies:
        cookie = dict(cookie)  # don't mutate the caller's list
        cookie.pop("sameSite", None)
        if cookie.get("expiry") is not None:
            # selenium chokes on a float/str expiry in some driver versions
            try:
                cookie["expiry"] = int(cookie["expiry"])
            except (TypeError, ValueError):
                cookie.pop("expiry", None)
        try:
            driver.add_cookie(cookie)
        except Exception:
            continue
    driver.refresh()
    human_delay()


def is_logged_in(driver, timeout: int = LOGIN_CHECK_TIMEOUT) -> bool:
    """Confirm the cookies actually produced an authenticated session,
    rather than LinkedIn silently bouncing us to /login or /checkpoint
    (dead session, flagged account, or a security challenge)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        url = driver.current_url
        if "linkedin.com/login" not in url and "linkedin.com/checkpoint" not in url \
                and "linkedin.com/authwall" not in url:
            return True
        time.sleep(0.5)
    return False


def human_delay(min_s: float = MIN_ACTION_DELAY, max_s: float = MAX_ACTION_DELAY):
    """Randomized pause between page actions, so requests don't fire in an
    obviously mechanical back-to-back pattern. This is a courtesy to
    LinkedIn's servers, not a way to make automated access allowed - it
    still isn't, per LinkedIn's Terms of Service, no matter the timing."""
    time.sleep(random.uniform(min_s, max_s))
