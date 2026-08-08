"""
Core Selenium logic: launching Chrome, searching LinkedIn for a company,
and extracting fields from a company's About page.
"""
import re
import time
from datetime import datetime
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import HEADLESS, MAX_SEARCH_RESULTS, ELEMENT_WAIT_TIMEOUT
from cookies_utils import human_delay


class ScraperError(Exception):
    """Anything that should stop the run and show a clear message in the UI."""


def get_driver() -> webdriver.Chrome:
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")  # avoids crashes in low-shm containers
    options.add_argument("--window-size=1400,1000")
    options.add_argument("--lang=en-US")
    try:
        driver = webdriver.Chrome(options=options)
    except WebDriverException as e:
        raise ScraperError(
            "معرفتش أفتح Chrome. تأكد إن Chrome + chromedriver متثبتين على الجهاز ده "
            f"ومتوافقين في الإصدار.\nتفاصيل: {e}"
        )
    driver.set_page_load_timeout(60)
    return driver


def search_companies(driver, name: str, max_results: int = MAX_SEARCH_RESULTS):
    """
    Search LinkedIn for `name` and return up to `max_results` candidate
    companies as [{"name": ..., "url": ...}, ...] (root /company/<slug>/
    pages, /about/ not appended yet).

    Real live "as you type" suggestions aren't practical here - each lookup
    drives a real logged-in browser page load, which is too slow/heavy to
    fire on every keystroke, and doing it per-keystroke would hammer
    LinkedIn's servers from your account. Instead this is a "search once,
    see close matches, pick the right one" step: you see what LinkedIn
    thinks matches your typed name before committing to scraping any one
    of them.
    """
    search_url = f"https://www.linkedin.com/search/results/companies/?keywords={quote_plus(name)}"
    try:
        driver.get(search_url)
    except TimeoutException:
        raise ScraperError("صفحة البحث في LinkedIn استغرقت وقت طويل عشان تفتح. جرّب تاني.")

    wait = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT)
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/company/']")))
    except TimeoutException:
        # Could be zero real results, or a login wall / rate-limit page -
        # tell the caller which so the UI can show the right message.
        if "authwall" in driver.current_url or "login" in driver.current_url:
            raise ScraperError("الجلسة رجعت لصفحة تسجيل الدخول - الكوكيز غالبًا منتهية.")
        return []

    results = driver.execute_script(
        """
        const maxResults = arguments[0];
        let seen = new Set();
        let results = [];
        let links = document.querySelectorAll('a[href*="/company/"]');
        for (let link of links) {
            if (link.closest('header') || link.closest('nav')) continue;
            let path;
            try {
                path = new URL(link.href).pathname;
            } catch (e) {
                continue;
            }
            if (!/^\\/company\\/[^\\/]+\\/?$/.test(path)) continue;
            if (seen.has(path)) continue;
            let name = link.innerText ? link.innerText.trim() : "";
            if (!name) continue;
            seen.add(path);
            results.push({name: name, url: "https://www.linkedin.com" + path});
            if (results.length >= maxResults) break;
        }
        return results;
        """,
        max_results,
    )
    return results or []


def _extract_field(lines, label):
    """
    LinkedIn's About page renders each field as its own line ('Industry'),
    with the value on the line right after it. Far more robust than
    regex-matching to the *next* field name, since field order and which
    fields are even present varies per company.
    """
    for i, line in enumerate(lines):
        if line == label:
            if i + 1 < len(lines):
                return lines[i + 1].strip()
    return None


def _extract_field_dom(driver, label):
    """
    Fallback for fields whose value sits in its own element (e.g. a
    badge-like <p> with hashed/CSS-module class names) next to a label
    element ("Type"). Those hashed classes aren't stable enough to hardcode
    as a selector, so instead we find the element whose text is *exactly*
    the label, then read the next element in the DOM (sibling, or parent's
    next sibling) for the value.
    """
    return driver.execute_script(
        """
        const label = arguments[0];
        let elements = document.querySelectorAll('h3, dt, span, div, p, li');
        for (let el of elements) {
            if (el.children.length === 0) {
                let text = el.innerText ? el.innerText.trim() : "";
                if (text === label) {
                    let sib = el.nextElementSibling;
                    if (sib && sib.innerText && sib.innerText.trim()) {
                        return sib.innerText.trim();
                    }
                    let parent = el.parentElement;
                    if (parent) {
                        let parentSib = parent.nextElementSibling;
                        if (parentSib && parentSib.innerText && parentSib.innerText.trim()) {
                            return parentSib.innerText.trim();
                        }
                    }
                }
            }
        }
        return null;
        """,
        label,
    )


def scrape_company_page(driver, company_url: str) -> dict:
    try:
        driver.get(company_url)
    except TimeoutException:
        raise ScraperError("صفحة الشركة استغرقت وقت طويل عشان تفتح. جرّب تاني.")

    wait = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT)
    try:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except TimeoutException:
        raise ScraperError("الصفحة متفتحتش صح - جرّب تاني.")

    if "authwall" in driver.current_url or "/login" in driver.current_url:
        raise ScraperError("الجلسة رجعت لصفحة تسجيل الدخول وإحنا بنحاول نسحب البيانات - الكوكيز منتهية.")

    # Small settle time for late-rendering React content - a fixed sleep is
    # still the pragmatic choice here since there's no single reliable
    # "the page is done" selector on this layout, but we keep it short
    # since the explicit waits above already did the heavy lifting.
    time.sleep(2)

    company_info = driver.find_element(By.TAG_NAME, "body").text
    lines = [l.strip() for l in company_info.split("\n") if l.strip()]

    industry = _extract_field(lines, "Industry")
    company_size = _extract_field(lines, "Company size")
    headquarters = _extract_field(lines, "Headquarters")

    # "Type" (Public Company / Privately Held / ...) renders as its own
    # styled badge, not as a plain text line right after "Type" in
    # body.innerText - so the line-based extractor misses it. Try that
    # first (cheap, works if LinkedIn ever renders it as plain text), then
    # fall back to walking the DOM for the label's neighboring element.
    company_type = _extract_field(lines, "Type") or _extract_field_dom(driver, "Type")

    founded_raw = _extract_field(lines, "Founded")
    founded_match = re.search(r"\d{4}", founded_raw) if founded_raw else None
    founded = founded_match.group(0) if founded_match else founded_raw

    overview = driver.execute_script(
        """
        let paragraphs = document.querySelectorAll('p');
        for (let p of paragraphs) {
            let text = p.innerText.trim();
            if (text.length > 150) {
                return text;
            }
        }
        return null;
        """
    )

    # Location is a short address-like paragraph near the header, NOT the
    # long overview text. Explicitly exclude the overview string and
    # require the text to look like an address (short + contains a digit,
    # e.g. a street number or postal code) instead of just containing a
    # country name (which the overview text often does too).
    location = driver.execute_script(
        """
        const overview = arguments[0];
        let paragraphs = document.querySelectorAll('p');
        for (let p of paragraphs) {
            let text = p.innerText.trim();
            if (
                text.length > 3 &&
                text.length < 150 &&
                text !== overview &&
                /\\d/.test(text)
            ) {
                return text;
            }
        }
        return null;
        """,
        overview,
    )

    associated_members = driver.execute_script(
        """
        let links = document.querySelectorAll('a');
        for (let link of links) {
            let text = link.innerText.trim();
            if (text.includes("associated members")) {
                return text.replace("associated members", "").trim();
            }
        }
        return null;
        """
    )

    title = driver.title
    title = re.sub(r"^\(\d+\)\s*", "", title)
    company_display_name = title.split(":")[0].strip() if title else None

    if not company_display_name and not overview and not industry:
        # Everything came back empty - almost always means LinkedIn served
        # a different layout/challenge page instead of the real About page,
        # not that the company genuinely has zero fields.
        raise ScraperError(
            "الصفحة اتفتحت بس معرفتش أستخرج أي بيانات منها - ممكن LinkedIn يكون غيّر شكل الصفحة "
            "أو عرض صفحة تحقق بدل صفحة الشركة."
        )

    return {
        "linkedin_url": company_url,
        "Company Name": company_display_name,
        "overview": overview,
        "industry": industry,
        "company_size": company_size,
        "company_type": company_type,
        "headquarters": headquarters,
        "founded": founded,
        "location": location,
        "associated_members": associated_members,
        "source": "LinkedIn",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
