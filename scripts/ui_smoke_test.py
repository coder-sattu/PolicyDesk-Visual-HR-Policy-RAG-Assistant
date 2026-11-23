"""Headless UI test: upload -> pipeline -> ask -> trace. Needs backend on :8000."""
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "docs" / "HR_Policy_Handbook.pdf"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/ui_shots")
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(URL)
    expect(page.get_by_text("From PDF to searchable knowledge")).to_be_visible()
    page.screenshot(path=OUT / "1_empty.png")
    print("ok  empty state")

    page.set_input_files("input[type=file]", str(PDF))
    expect(page.locator(".station.is-running").first).to_be_visible(timeout=5000)
    page.screenshot(path=OUT / "2_running.png")
    print("ok  pipeline running")

    expect(page.get_by_role("button", name="Ask a question")).to_be_visible(timeout=20000)
    assert page.locator(".station.is-done").count() == 6, "not all 6 stations done"
    page.screenshot(path=OUT / "3_ingested.png", full_page=True)
    print("ok  all 6 ingestion stations done")

    page.get_by_role("button", name="Ask a question").click()
    page.get_by_role("button", name="How many days of sick leave do I get in a year?").click()
    expect(page.locator(".msg__sources")).to_be_visible(timeout=20000)
    expect(page.locator(".trace__step.is-done")).to_have_count(5, timeout=10000)
    page.screenshot(path=OUT / "4_answer.png")
    print("ok  answer + 5 retrieval steps:", page.locator(".msg--bot").first.inner_text()[:120].replace("\n", " "))

    page.fill("#q", "And how many days of paternity leave?")
    page.keyboard.press("Enter")
    expect(page.locator(".msg__sources")).to_have_count(2, timeout=20000)
    page.locator(".srcchip").last.click()
    page.screenshot(path=OUT / "5_followup.png")
    print("ok  follow-up answered")

    page.fill("#q", "xylophone zeppelin quokka?")
    page.keyboard.press("Enter")
    expect(page.locator(".trace__step.is-done h3", has_text="Fallback")).to_be_visible(timeout=20000)
    print("ok  off-topic question routed to fallback")

    page.get_by_role("button", name="View chunks").first.click()
    expect(page.locator(".drawer .chunk").first).to_be_visible()
    page.screenshot(path=OUT / "6_chunks.png")
    page.keyboard.press("Escape")
    print("ok  chunk browser")

    page.set_viewport_size({"width": 390, "height": 844})
    page.get_by_role("button", name="Ingest").click()
    page.screenshot(path=OUT / "7_mobile.png", full_page=True)
    print("ok  mobile layout")

    browser.close()
    if errors:
        print("CONSOLE ERRORS:", errors)
        sys.exit(1)
    print("UI smoke test passed")
