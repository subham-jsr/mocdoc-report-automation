# ============================================================
# MOCDOC AUTOMATIC REPORT DOWNLOADER
# What this does: Every day, this script automatically opens
# MocDoc, sets the correct date, and downloads 3 reports:
# 1. Current Stock (Batchwise) — TODAY'S date
# 2. Daily Sales (Bill Wise Detailed) — YESTERDAY'S date
# 3. Daily Purchase (GRN Detailed) — YESTERDAY'S date
# ============================================================

from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

# ── CALCULATE DATES ──────────────────────────────────────────
# Yesterday's date - used for Sales and Purchase reports
yesterday = datetime.now() - timedelta(days=1)
yesterday_str = yesterday.strftime("%d/%m/%Y")
date_for_filename = yesterday.strftime("%d-%m-%Y")

# Today's date - used for Current Stock report only
today = datetime.now()
today_str = today.strftime("%d/%m/%Y")
today_for_filename = today.strftime("%d-%m-%Y")

print(f"Today's date (Current Stock): {today_str}")
print(f"Yesterday's date (Sales & Purchase): {yesterday_str}")


# ============================================================
# FUNCTION 1: handle_all_syncs
# ------------------------------------------------------------
# Master sync handler - handles BOTH types of sync together!
# Keeps looping until ALL syncing is truly done.
# No other action happens until this function returns!
# If nothing is syncing - moves on INSTANTLY with no wait!
#
# Type 1: Full page "Sync All" button → clicks it
# Type 2: "Syncing... 14%" popup → waits for it to finish
#
# FIX: Uses tight manual loop so Python does NOTHING else
# while syncing - prevents accidental page actions!
# ============================================================
def handle_all_syncs(page):
    print("🔄 Checking for any sync activity...")

    while True:
        sync_found = False

        # ── CHECK TYPE 1: Sync All button ──────────────────
        # This is the full page orange "Sync All" button
        try:
            sync_button = page.locator("button.sync-all")
            if sync_button.is_visible():
                print("⚠️  Sync All button detected! Clicking...")
                sync_button.click()
                # 1 second wait for sync process to begin
                page.wait_for_timeout(1000)
                sync_found = True
        except:
            pass

        # ── CHECK TYPE 2: Syncing popup ────────────────────
        # This is the "Syncing... 14%" progress popup
        try:
            syncing = page.locator("text=Syncing")
            if syncing.is_visible():
                print("⚠️  Syncing popup detected! Waiting...")

                # TIGHT MANUAL LOOP - Python does NOTHING else
                # inside this loop except check if sync is done!
                # This prevents accidental clicks or scrolling
                # while the page is still syncing underneath!
                while True:
                    # Wait 1 second then check again
                    page.wait_for_timeout(1000)

                    # Check if Syncing text is still showing
                    still_syncing = page.locator("text=Syncing").is_visible()

                    if not still_syncing:
                        print("✅ Syncing finished!")
                        # Extra 2 seconds after sync finishes
                        # to let the page fully settle before
                        # Python tries to do anything!
                        page.wait_for_timeout(2000)
                        break

                    # Still syncing - print and loop again
                    print("⏳ Still syncing... waiting...")

                sync_found = True
        except:
            pass

        # ── IF NOTHING FOUND → DONE, MOVE ON INSTANTLY! ───
        if not sync_found:
            print("✅ No sync activity - safe to continue!")
            break
        else:
            # Loop again to check if more sync appeared
            print("🔄 Re-checking for more sync activity...")
            page.wait_for_timeout(1000)


# ============================================================
# FUNCTION 2: wait_for_processing
# ------------------------------------------------------------
# After clicking Bill Wise Sale, GRN, or Jade Pharmacy,
# MocDoc shows a "Processing..." popup while it loads data.
# Waits for popup to disappear before moving on.
# If no processing popup appears - moves on INSTANTLY!
# ============================================================
def wait_for_processing(page):
    print("⏳ Checking for processing popup...")
    try:
        # Look for "Processing" text - wait max 8 seconds
        page.wait_for_selector("text=Processing", timeout=8000)
        print("⚠️  Processing popup detected! Waiting...")

        # Wait until "Processing" disappears - max 2 minutes
        page.wait_for_selector(
            "text=Processing",
            state="hidden",
            timeout=120000
        )
        print("✅ Processing finished!")

        # 1 second buffer after processing completes
        page.wait_for_timeout(1000)

    except:
        # No processing popup - move on instantly!
        print("✅ No processing popup - continuing!")


# ============================================================
# FUNCTION 3: set_dates
# ------------------------------------------------------------
# Sets both start date and end date on the MIS page.
# use_today=True → uses today's date (Current Stock)
# use_today=False → uses yesterday's date (Sales & Purchase)
# ============================================================
def set_dates(page, use_today=False):
    # Pick the correct date based on which report we are doing
    date_to_use = today_str if use_today else yesterday_str

    # Click start date box, select all, type new date
    page.locator("#startdate").click()
    page.wait_for_timeout(500)
    page.keyboard.press("Control+a")
    page.keyboard.type(date_to_use)
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)

    # Same steps for end date box
    page.locator("#enddate").click()
    page.wait_for_timeout(500)
    page.keyboard.press("Control+a")
    page.keyboard.type(date_to_use)
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)

    # Read back values to verify dates were set correctly
    start_val = page.locator("#startdate").input_value()
    end_val = page.locator("#enddate").input_value()
    print(f"✅ Dates set - Start: {start_val} | End: {end_val}")


# ============================================================
# FUNCTION 4: select_jade_and_download
# ------------------------------------------------------------
# After clicking a report button, MocDoc shows a
# "Choose Store" page. This function:
# 1. Waits 4 seconds for store page to load
# 2. Handles any sync
# 3. Clicks JADE PHARMACY
# 4. Waits for processing popup to finish
# 5. Clicks Export As CSV
# 6. Saves the file to Desktop with date in filename
# ============================================================
def select_jade_and_download(page, filename, use_today=False):
    # Pick the correct date for the saved filename
    file_date = today_for_filename if use_today else date_for_filename

    print("⏳ Waiting for store selection page...")

    # Wait 4 seconds for store selection page to load
    page.wait_for_timeout(4000)

    # Handle any sync before clicking
    handle_all_syncs(page)

    # Click JADE PHARMACY link in the store selection table
    page.get_by_role("link", name="JADE PHARMACY").click()
    print("→ Selected JADE PHARMACY!")

    # Wait 4 seconds for data to start loading
    page.wait_for_timeout(4000)

    # Wait for processing popup - waits until truly finished!
    wait_for_processing(page)

    # Handle any sync that appeared after processing
    handle_all_syncs(page)

    print("✅ Data loaded!")

    # Tell Playwright a file download is about to happen
    with page.expect_download() as download_info:
        page.get_by_text("Export As CSV").click()
        print("→ Clicked Export As CSV!")

    # Save the downloaded file to Desktop with date in name
    download = download_info.value
    filepath = f"C:/Users/Subham Mahato/Desktop/{filename}_{file_date}.csv"
    download.save_as(filepath)
    print(f"✅ Saved: {filename}_{file_date}.csv")


# ============================================================
# FUNCTION 5: go_to_mis
# ------------------------------------------------------------
# Opens the MIS reports page and sets the correct date.
# Called 3 times - once per report.
# use_today=True → today's date (Current Stock)
# use_today=False → yesterday's date (Sales & Purchase)
# ============================================================
def go_to_mis(page, use_today=False):
    page.goto(
        "https://mocdoc.com/reports/mis/vishwa-healthcare",
        wait_until="commit"
    )
    print("→ Opened MIS page!")

    # Wait 4 seconds for page AND sync popup to appear
    # Sync popup takes a moment to show after page loads
    # Checking too early means we miss it!
    page.wait_for_timeout(4000)

    # Handle any sync on page load
    handle_all_syncs(page)

    # Set the correct dates
    set_dates(page, use_today=use_today)


# ============================================================
# MAIN FUNCTION: run
# ------------------------------------------------------------
# Main engine of the script.
# Runs all 3 reports one after another.
# ============================================================
def run(playwright):

    # Open visible Chrome browser window
    browser = playwright.chromium.launch(headless=False)

    # Load saved login session and allow file downloads
    context = browser.new_context(
        accept_downloads=True,
        storage_state="session.json"
    )

    # Open a new tab
    page = context.new_page()
    print("Step 1 - Session loaded! No login needed!")

    # Open MocDoc home page to activate session
    page.goto("https://mocdoc.com/frontoffice/home", wait_until="commit")
    print("Step 2 - Opened MocDoc home!")

    # Wait 4 seconds for page and sync popup to appear
    page.wait_for_timeout(4000)

    # Handle any sync on home page
    handle_all_syncs(page)

    # ─────────────────────────────────────────────────────
    # REPORT 1 — CURRENT STOCK (BATCHWISE)
    # Uses TODAY'S date
    # ─────────────────────────────────────────────────────
    print("\n--- REPORT 1: Current Stock (Today's date) ---")

    go_to_mis(page, use_today=True)

    # Click Current Stock dropdown toggle
    page.locator("#currstock").locator(
        "xpath=ancestor::div[contains(@class,'btn-group')]"
    ).locator("button.dropdown-toggle").click()
    page.wait_for_timeout(2000)
    handle_all_syncs(page)

    # Click Batchwise
    page.locator("#currstock").click()
    wait_for_processing(page)
    handle_all_syncs(page)
    select_jade_and_download(page, "current_stock", use_today=True)

    # ─────────────────────────────────────────────────────
    # REPORT 2 — DAILY SALES (BILL WISE DETAILED)
    # Uses YESTERDAY'S date
    # ─────────────────────────────────────────────────────
    print("\n--- REPORT 2: Daily Sales (Yesterday's date) ---")

    go_to_mis(page)

    # Click Sale dropdown toggle
    page.locator("#salebillwise_det").locator(
        "xpath=ancestor::div[contains(@class,'btn-group')]"
    ).locator("button.dropdown-toggle").click()
    page.wait_for_timeout(2000)
    handle_all_syncs(page)

    # Click Bill Wise Detailed
    page.locator("#salebillwise_det").click()
    wait_for_processing(page)
    handle_all_syncs(page)
    select_jade_and_download(page, "daily_sales")

    # ─────────────────────────────────────────────────────
    # REPORT 3 — DAILY PURCHASE (GRN DETAILED)
    # Uses YESTERDAY'S date
    # ─────────────────────────────────────────────────────
    print("\n--- REPORT 3: Daily Purchase (Yesterday's date) ---")

    go_to_mis(page)

    # Click Purchase dropdown toggle
    page.locator("#grnlist_det").locator(
        "xpath=ancestor::div[contains(@class,'btn-group')]"
    ).locator("button.dropdown-toggle").click()
    page.wait_for_timeout(2000)
    handle_all_syncs(page)

    # Click GRN Detailed
    page.locator("#grnlist_det").click()
    wait_for_processing(page)
    handle_all_syncs(page)
    select_jade_and_download(page, "daily_purchase")

    # Close the browser
    browser.close()

    # Final success message
    print("\n🎉 ALL 3 REPORTS DOWNLOADED SUCCESSFULLY!")
    print(f"📁 Check your Desktop for:")
    print(f"   → current_stock_{today_for_filename}.csv")
    print(f"   → daily_sales_{date_for_filename}.csv")
    print(f"   → daily_purchase_{date_for_filename}.csv")


# ============================================================
# SCRIPT ENTRY POINT
# ------------------------------------------------------------
# Python starts here when you type: python hello_browser.py
# ============================================================
with sync_playwright() as p:
    run(p)