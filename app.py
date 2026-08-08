import os

import pandas as pd
import streamlit as st

from config import EXCEL_PATH, COOKIES_PATH, MAX_SEARCH_RESULTS
from cookies_utils import load_cookie_file, apply_cookies, is_logged_in, human_delay, CookieError
from scraper import get_driver, search_companies, scrape_company_page, ScraperError

st.set_page_config(
    page_title="LinkedIn Company Scraper",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Styling ----------
st.markdown(
    """
    <style>
    .stApp { background-color: #F7F9FB; }
    .block-container { padding-top: 2.2rem; max-width: 1000px; }

    .app-header {
        display: flex; align-items: center; gap: 14px; margin-bottom: 4px;
    }
    .app-header h1 {
        font-size: 1.9rem; font-weight: 700; color: #0A0A0A; margin: 0;
    }
    .app-subtitle { color: #5B6470; font-size: 0.98rem; margin-bottom: 1.6rem; }

    .stButton>button {
        border-radius: 8px; font-weight: 600; padding: 0.5rem 1.2rem;
        border: none;
    }
    .stButton>button[kind="primary"] { background-color: #0A66C2; }
    .stButton>button[kind="primary"]:hover { background-color: #084d94; }

    .status-pill {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 3px 12px; border-radius: 999px;
        font-size: 0.82rem; font-weight: 600; letter-spacing: 0.2px;
    }
    .pill-ok   { background:#E6F4EA; color:#1E7E34; }
    .pill-bad  { background:#FCE8E6; color:#C5221F; }

    .field-card {
        background: white; border: 1px solid #E7EAEE; border-radius: 10px;
        padding: 14px 18px; margin-bottom: 10px;
    }
    .field-label {
        font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.6px;
        color: #8A93A1; font-weight: 600; margin-bottom: 2px;
    }
    .field-value { font-size: 0.98rem; color: #14171A; font-weight: 500; }

    section[data-testid="stSidebar"] { background-color: #FFFFFF; }
    div[data-testid="stRadio"] > label { font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="app-header">
        <span style="font-size:1.8rem;">🔎</span>
        <h1>LinkedIn Company Scraper</h1>
    </div>
    <div class="app-subtitle">
        Type a company name, pick the right match, and I'll pull its LinkedIn
        profile — industry.
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Connection status (fixed cookie path, headless-only) ----------
cookies_ready = os.path.exists(COOKIES_PATH)

# ---------- Session state ----------
for key, default in [
    ("driver", None),
    ("candidates", []),
    ("last_result", None),
    ("searched_name", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def _cleanup_driver():
    if st.session_state.driver is not None:
        try:
            st.session_state.driver.quit()
        except Exception:
            pass
    st.session_state.driver = None


# ---------- Search ----------
col1, col2 = st.columns([4, 1], vertical_alignment="bottom")
with col1:
    company_name = st.text_input(
        "Company name", placeholder="e.g. Bosta", label_visibility="visible"
    )
with col2:
    search_button = st.button(
        "Search 🔍",
        type="primary",
        use_container_width=True,
        disabled=(not cookies_ready or not company_name),
    )

if search_button:
    # New search — close any previous browser session first so we don't
    # leak Chrome processes across searches.
    _cleanup_driver()
    st.session_state.candidates = []
    st.session_state.last_result = None
    st.session_state.searched_name = company_name

    with st.status("Looking for that company...", expanded=True) as status:
        driver = None
        try:
            st.write("Starting the browser...")
            driver = get_driver()

            st.write("Signing in with the saved session...")
            cookies = load_cookie_file(COOKIES_PATH)
            apply_cookies(driver, cookies)

            if not is_logged_in(driver):
                raise CookieError(
                    "The cookies loaded fine, but LinkedIn bounced me to a login "
                    "or checkpoint page — the session's probably expired. "
                    "Export a fresh cookie file and try again."
                )

            human_delay()
            st.write(f"Searching for '{company_name}'...")
            candidates = search_companies(driver, company_name, MAX_SEARCH_RESULTS)

            if not candidates:
                status.update(label="Nothing came up", state="error")
                st.error("Couldn't find anything close to that name — try a different spelling or a shorter version.")
                driver.quit()
            else:
                status.update(
                    label=f"Found {len(candidates)} possible matches", state="complete"
                )
                # Keep this driver open + logged in — the next step (scraping
                # the company the user picks) reuses it instead of opening
                # and logging in to a second browser.
                st.session_state.driver = driver
                st.session_state.candidates = candidates

        except (CookieError, ScraperError) as e:
            status.update(label="That didn't work", state="error")
            st.error(str(e))
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
        except Exception as e:
            status.update(label="Ran into an unexpected error", state="error")
            st.error(f"Error: {e}")
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass

if st.session_state.candidates:
    st.markdown(f"##### Which '{st.session_state.searched_name}' did you mean?")
    options = {f"{c['name']}  —  {c['url']}": c for c in st.session_state.candidates}
    picked_label = st.radio(
        "Pick the right one:", list(options.keys()), label_visibility="collapsed"
    )
    picked = options[picked_label]

    scrape_button = st.button("Pull the data 📥", type="primary")

    if scrape_button:
        with st.status("Reading the company page...", expanded=True) as status:
            try:
                driver = st.session_state.driver
                if driver is None:
                    raise ScraperError("The browser session closed on its own — run the search again.")

                human_delay()
                company_url = picked["url"].rstrip("/") + "/about/"
                st.write(f"Opening {company_url}")
                data = scrape_company_page(driver, company_url)

                status.update(label="Got it ✅", state="complete")

                # Write to Excel ONLY here, i.e. only on an actual new scrape —
                # never on a plain rerun (e.g. clicking the download button),
                # which is what used to cause duplicate rows.
                new_row_df = pd.DataFrame([data])
                if os.path.exists(EXCEL_PATH):
                    existing_df = pd.read_excel(EXCEL_PATH)
                    final_df = pd.concat([existing_df, new_row_df], ignore_index=True)
                else:
                    final_df = new_row_df
                final_df = final_df.drop_duplicates()
                final_df.to_excel(EXCEL_PATH, index=False)

                st.session_state.last_result = new_row_df

            except (CookieError, ScraperError) as e:
                status.update(label="That didn't work", state="error")
                st.error(str(e))
            except Exception as e:
                status.update(label="Ran into an unexpected error", state="error")
                st.error(f"Error: {e}")
            finally:
                # Either way, close this browser session and clear the
                # candidate list so the next search starts fresh.
                _cleanup_driver()
                st.session_state.candidates = []

# ---------- Result card ----------
if st.session_state.last_result is not None:
    row = st.session_state.last_result.iloc[0]
    st.markdown("##### Here's what I found")

    top_cols = st.columns(3)
    top_fields = [
        ("Company", row.get("Company Name")),
        ("Industry", row.get("industry")),
        ("Headquarters", row.get("headquarters")),
    ]
    for col, (label, value) in zip(top_cols, top_fields):
        with col:
            st.markdown(
                f"""
                <div class="field-card">
                    <div class="field-label">{label}</div>
                    <div class="field-value">{value or "—"}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    bottom_cols = st.columns(4)
    bottom_fields = [
        ("Company size", row.get("company_size")),
        ("Type", row.get("company_type")),
        ("Founded", row.get("founded")),
        ("Associated members", row.get("associated_members")),
    ]
    for col, (label, value) in zip(bottom_cols, bottom_fields):
        with col:
            st.markdown(
                f"""
                <div class="field-card">
                    <div class="field-label">{label}</div>
                    <div class="field-value">{value or "—"}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if row.get("overview"):
        st.markdown(
            f"""
            <div class="field-card">
                <div class="field-label">Overview</div>
                <div class="field-value">{row.get("overview")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("Show raw row"):
        st.dataframe(st.session_state.last_result, use_container_width=True)

# ---------- Download ----------
if os.path.exists(EXCEL_PATH):
    with open(EXCEL_PATH, "rb") as f:
        excel_bytes = f.read()
    total_rows = len(pd.read_excel(EXCEL_PATH))
    st.markdown("---")
    dl_col1, dl_col2 = st.columns([3, 1], vertical_alignment="center")
    with dl_col1:
        st.caption(f"You've got {total_rows} companies saved so far.")
    with dl_col2:
        st.download_button(
            "⬇️ Download Excel",
            data=excel_bytes,
            file_name="linkedin_company_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )