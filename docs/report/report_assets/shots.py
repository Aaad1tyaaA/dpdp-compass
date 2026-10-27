"""Captures the report's application screenshots from the running app (frontend :3002, mock backend :8001)."""
import json, pathlib, re, sys, time
from playwright.sync_api import sync_playwright

OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://localhost:3002"
ACC = json.loads(pathlib.Path(r"D:\DPDPRag\project\backend\storage\dev-test-account.json").read_text())
FACTS = {"company": "Kirana Express Pvt Ltd", "service": "An app for 30-minute grocery delivery in Bengaluru", "website": "https://kirana.in/privacy",
         "address": "12 MG Road, Bengaluru 560001", "dpo_name": "Priya Rao", "contact": "privacy@kirana.in, +91 80 1234 5678", "grievance_days": "30",
         "children": "No, users must be 18 or over; age checked at sign-up", "data": "Name, mobile number, email, delivery address, order history, UPI ID",
         "data_auto": "Device ID, IP address, approximate location", "purpose": "Deliver orders, take payment, prevent fraud, answer support requests",
         "consent_method": "Ticking an unticked box on the sign-up screen after reading the notice",
         "withdraw_method": "Settings > Privacy > Withdraw consent, or email privacy@kirana.in", "languages": "English, Hindi, Kannada",
         "sharing": "Razorpay (payments), AWS Mumbai (hosting), Shiprocket (delivery)", "storage_location": "India (AWS Mumbai region)",
         "security": "AES-256 encryption at rest, TLS in transit, role-based access control, daily backups",
         "retention": "Invoices 8 years (GST law); account data until deletion plus 30 days; support chats 12 months",
         "rights_channel": "Email privacy@kirana.in or use the form at kirana.in/privacy"}
WEAK = ("We collect your name, phone number and location to provide our services. By using our app you agree to this policy. "
        "If we become aware of a breach, we will notify affected users by email. We keep your data as long as necessary. "
        "We share data with trusted third parties. Contact support@example.com for any questions about this policy.")


def shot(page, name, full=False):
    page.wait_for_timeout(700)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
    print("saved", name)


def tab(page, label):
    page.get_by_role("tab", name=label).click()
    page.wait_for_timeout(500)


def fill(page, values):
    for k, v in values.items():
        el = page.locator(f"#f-{k}")
        if el.count():
            el.fill(v)


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1366, "height": 768}, device_scale_factor=1.5, color_scheme="light")
    page = ctx.new_page()
    page.add_init_script("try{localStorage.setItem('theme','light')}catch(e){}")

    page.goto(BASE + "/"); page.wait_for_load_state("networkidle"); shot(page, "s01_landing")
    page.goto(BASE + "/signin"); page.wait_for_load_state("networkidle"); shot(page, "s02_signin")
    r = page.request.post(BASE + "/api/auth/login", data={"email": ACC["email"], "password": ACC["password"]})
    assert r.ok, r.status

    page.goto(BASE + "/dashboard"); page.wait_for_load_state("networkidle"); page.wait_for_timeout(1200); shot(page, "s03_dashboard")

    # Business: audit a weak policy
    page.goto(BASE + "/business"); page.wait_for_load_state("networkidle"); tab(page, "Check a policy")
    shot(page, "s04_audit_input")
    page.locator("#pasted").fill(WEAK)
    page.get_by_role("button", name="Run audit").click()
    page.get_by_text("obligations checked").wait_for(timeout=120000)
    page.locator('[aria-label^="Compliance score"]').scroll_into_view_if_needed(); page.mouse.wheel(0, -120)
    shot(page, "s05_audit_result")
    first = page.locator("button", has_text="Notice of data and purpose").first
    first.click(); page.wait_for_timeout(600); first.scroll_into_view_if_needed(); shot(page, "s06_audit_finding")

    # Business: write a policy
    tab(page, "Write a new policy")
    page.locator("#f-company").scroll_into_view_if_needed(); shot(page, "s07_create_form")
    page.locator('button[aria-label="What to enter here"]').nth(4).hover(); page.wait_for_timeout(600); shot(page, "s08_info_tooltip")
    fill(page, {**FACTS, "dpo_name": "", "grievance_days": "", "security": "we keep data safe"})
    page.get_by_role("button", name="Draft the policy").click(); page.get_by_text("A few questions before I draft this").wait_for(timeout=60000)
    page.get_by_text("A few questions before I draft this").scroll_into_view_if_needed(); shot(page, "s09_followup_questions")
    page.get_by_role("button", name="Draft anyway with placeholders").click(); page.locator("mark[data-placeholder]").first.wait_for(timeout=60000)
    page.locator("mark[data-placeholder]").first.scroll_into_view_if_needed(); page.mouse.wheel(0, -200); shot(page, "s10_placeholders")
    fill(page, FACTS)
    page.get_by_role("button", name=re.compile("Draft the policy|Check my answers again")).click(); page.get_by_text("Passes 14 of 14 audit rules").wait_for(timeout=60000)
    page.get_by_text("Passes 14 of 14 audit rules").scroll_into_view_if_needed(); page.mouse.wheel(0, -150); shot(page, "s11_generated_policy")
    page.get_by_role("button", name="Audit this draft").click(); page.wait_for_timeout(1500)
    page.get_by_text("obligations checked").wait_for(timeout=120000)
    page.locator('[aria-label^="Compliance score"]').scroll_into_view_if_needed(); page.mouse.wheel(0, -120); shot(page, "s12_generated_audit_100")

    # Citizen
    page.goto(BASE + "/citizen"); page.wait_for_load_state("networkidle"); shot(page, "s13_citizen")
    page.get_by_placeholder("Type your question here").fill("Can a company keep my data after I withdraw consent?")
    page.get_by_role("button", name="Ask").click(); page.wait_for_timeout(9000); shot(page, "s14_citizen_answer")

    for path, name in (("/evaluation", "s15_evaluation"), ("/about", "s16_about"), ("/account", "s17_account")):
        page.goto(BASE + path); page.wait_for_load_state("networkidle"); page.wait_for_timeout(1200); shot(page, name)

    page.goto("http://localhost:8001/docs"); page.wait_for_load_state("networkidle"); page.wait_for_timeout(1500); shot(page, "t01_swagger_api")

    m = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, color_scheme="light")
    mp = m.new_page(); mp.request.post(BASE + "/api/auth/login", data={"email": ACC["email"], "password": ACC["password"]})
    mp.goto(BASE + "/dashboard"); mp.wait_for_load_state("networkidle"); mp.wait_for_timeout(1000)
    mp.screenshot(path=str(OUT / "s18_mobile.png")); print("saved s18_mobile")
    b.close()
