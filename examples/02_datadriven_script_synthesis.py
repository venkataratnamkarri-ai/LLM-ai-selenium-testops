"""
Pattern 02: Data-Driven AI Test Script Synthesis
Demonstrates:
1. Loading live test credentials from Excel workbooks (test_users.xlsx) using openpyxl.
2. Selecting secure test credentials at random.
3. Prompting Cohere with security and best-practice constraints (e.g. parameterizing credentials via env vars).
4. Generating an automated QA executive summary report.
"""

import os
from pathlib import Path
import secrets
import sys
import cohere
from dotenv import load_dotenv
from openpyxl import load_workbook

# Ensure UTF-8 output on Windows consoles
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

load_dotenv()
api_key = os.getenv("COHERE_API_KEY")
if not api_key:
    raise ValueError("COHERE_API_KEY not found. Please set it in your .env file.")

co = cohere.ClientV2(api_key)

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = BASE_DIR / "data" / "test_users.xlsx"
LOGIN_URL = "https://demo.jmix.io/bookstore/login"

if not CREDENTIALS_FILE.is_file():
    raise FileNotFoundError(f"Credentials workbook not found: {CREDENTIALS_FILE}")

def get_random_credentials() -> dict[str, str]:
    """Load User/Password pairs and return one random account."""
    workbook = load_workbook(CREDENTIALS_FILE, read_only=True, data_only=True)
    try:
        sheet = workbook.active
        headers = tuple(cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1)))
        if headers[:2] != ("User", "Password"):
            raise ValueError(f"Expected header ('User', 'Password'), got {headers!r}")

        credentials = [
            {"user": str(user).strip(), "password": str(password).strip()}
            for user, password, *_ in sheet.iter_rows(min_row=2, values_only=True)
            if user is not None and password is not None
        ]
    finally:
        workbook.close()

    if not credentials:
        raise ValueError(f"No valid credential rows found in {CREDENTIALS_FILE}")
    return secrets.choice(credentials)

def generate_parameterized_selenium_test(account: dict[str, str]) -> str:
    print(f"\nSynthesizing test script for account: '{account['user']}'...")
    prompt = f"""Write an executable Python Selenium login test for {LOGIN_URL}.
Target Account:
Username: {account['user']}
Password: {account['password']}

Requirements:
- Use ChromeOptions and explicit WebDriverWait with expected_conditions.
- Target real locators (#username, #password, button[type='submit']).
- For credential security, have the script read credentials from environment variables TEST_USERNAME and TEST_PASSWORD, with fallback to the account above.
- Do not assert that the test has already passed; generate only the runnable test script.
"""
    response = co.chat(
        model="command-a-03-2025",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=600
    )

    return "".join(
        item.text for item in response.message.content
        if getattr(item, "text", None)
    ).strip()


if __name__ == "__main__":
    print(f"Reading test users from: {CREDENTIALS_FILE}")
    account = get_random_credentials()
    print(f"Randomly Selected Account: {account['user']} (masked password)")

    script = generate_parameterized_selenium_test(account)

    print("\n" + "=" * 70)
    print("AI-SYNTHESIZED PARAMETERIZED SELENIUM SCRIPT:")
    print("=" * 70)
    print(script)
