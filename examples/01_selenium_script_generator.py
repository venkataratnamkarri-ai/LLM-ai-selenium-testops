"""
Pattern 01: AI-Powered Selenium Test Script Generation
Demonstrates using Cohere Command models to dynamically generate executable Python
Selenium automation scripts from natural language test scenarios, and subsequently
generating an executive test summary report.
"""

import os
import sys
import cohere
from dotenv import load_dotenv

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

# Test Scenario Definition
web_url = "https://demo.jmix.io/bookstore/login"
valid_username = "hikari"
valid_password = "hikari"

def generate_selenium_test() -> str:
    print(f"Requesting Cohere to generate an executable Selenium script for {web_url}...")

    prompt = (
        f"Write an executable Selenium WebDriver test script in Python to log into {web_url} "
        f"with Username: {valid_username} and Password: {valid_password}. "
        "The script must use explicit WebDriverWait with expected_conditions and real locators."
    )

    response = co.chat(
        model="command-a-03-2025",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=600
    )

    if response.message and response.message.content:
        return "".join(
            item.text for item in response.message.content
            if getattr(item, "text", None)
        ).strip()
    return "No valid script generated."

def generate_test_summary_report(script: str) -> str:
    print("\nGenerating Executive Test Summary Report with Cohere...")
    prompt = (
        f"Generate a professional QA summary report describing the test objectives, "
        f"prerequisites, and execution flow of this Selenium script:\n\n{script}"
    )

    response = co.chat(
        model="command-a-03-2025",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=300
    )

    return "".join(
        item.text for item in response.message.content
        if getattr(item, "text", None)
    ).strip()


if __name__ == "__main__":
    generated_code = generate_selenium_test()

    print("\n" + "=" * 70)
    print("AI-GENERATED SELENIUM TEST SCRIPT:")
    print("=" * 70)
    print(generated_code)

    summary_report = generate_test_summary_report(generated_code)
    print("\n" + "=" * 70)
    print("AI TEST SUMMARY REPORT:")
    print("=" * 70)
    print(summary_report)
