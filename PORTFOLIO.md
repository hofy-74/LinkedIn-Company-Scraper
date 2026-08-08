# Portfolio Description — LinkedIn Company Scraper

## One-liner (for a project card or resume bullet)
Built a Streamlit + Selenium tool that automates LinkedIn company research,
turning a company name into a structured Excel record in seconds.

## Short version (portfolio card, ~60 words)
A Streamlit web app that searches LinkedIn for a company, lets the user
confirm the right match, then scrapes its public profile — industry, size,
headquarters, founding year, and more — straight into a running Excel
dataset. Built with Python and Selenium, with a modular codebase separating
the UI, session handling, and scraping logic.

## Full version (portfolio page / case study, ~180 words)
**LinkedIn Company Scraper** is a self-contained data collection tool built
to remove the manual work of researching companies one by one on LinkedIn.
The user types a company name, the app searches LinkedIn and surfaces the
closest matches, and once the right company is confirmed it scrapes the
About page — name, overview, industry, company size, type, headquarters,
founding year, location, and associated member count — appending the result
to a growing, deduplicated Excel dataset that can be downloaded at any time.

Technically, the project is split into four modules: a Streamlit UI layer,
a Selenium-driven scraper, a cookie/session-validation layer that checks a
saved LinkedIn session is actually authenticated before use, and a single
config file controlling paths and timeouts. The app runs headless and adds
randomized delays between actions rather than firing requests in a fixed,
obviously automated pattern.

**Stack:** Python, Streamlit, Selenium, Pandas, OpenPyXL
**Skills demonstrated:** browser automation, DOM parsing without stable
selectors, session/auth handling, defensive error handling, and building a
usable UI around a scraping workflow.

## Suggested tags
`Python` `Streamlit` `Selenium` `Web Scraping` `Automation` `Data Collection` `Pandas`

## Notes for the portfolio write-up
- Worth adding 1–2 screenshots of the app (search step + result card) once
  you run it locally — visuals carry more weight than text on a portfolio
  page for a UI-driven project like this one.
- If a reviewer might ask about it in an interview, it's worth being upfront
  that this scrapes LinkedIn using a personal session cookie, which is
  against LinkedIn's Terms of Service — framing it as "built to practice
  Selenium, DOM parsing, and session handling" rather than "a tool I run
  regularly" keeps that honest.
