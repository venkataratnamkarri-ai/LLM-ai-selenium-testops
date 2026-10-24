"""
Pattern 04: Headless Selenium Web Scraping + AI Translation
Demonstrates:
1. Using Headless Chrome to scrape dynamic web content from BlazeDemo Vacation page.
2. Extracting textual DOM elements.
3. Passing extracted web text to Cohere translation models to extract and translate
   the destination of the week into Hindi.
"""

import os
import sys
import time
from dotenv import load_dotenv
import cohere
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Ensure UTF-8 output on Windows consoles
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

load_dotenv()
api_key = os.getenv("COHERE_API_KEY")
if not api_key:
    raise ValueError("COHERE_API_KEY not found. Please set it in your .env file.")

co = cohere.ClientV2(api_key=api_key)

TARGET_URL = "https://blazedemo.com/vacation.html"

def scrape_destination_text() -> str:
    print(f"Launching headless Chrome to scrape: {TARGET_URL}...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(TARGET_URL)
        wait = WebDriverWait(driver, 10)
        element = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//div[contains(text(),'Destination of the week')]"))
        )
        text = element.text.strip()
        print(f"Scraped DOM Text: \"{text}\"")
        return text
    finally:
        driver.quit()

def translate_destination(scraped_text: str) -> str:
    print("\nRequesting Cohere to extract the destination and translate into Hindi...")
    prompt = f"Extract the main destination name from this text and translate it into Hindi: {scraped_text}"

    # Use command-a-translate or fallback to command-a
    response = co.chat(
        model="command-a-translate-08-2025",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=150
    )

    return "".join(
        item.text for item in response.message.content
        if getattr(item, "text", None)
    ).strip()


if __name__ == "__main__":
    extracted_text = scrape_destination_text()
    translation = translate_destination(extracted_text)

    print("\n" + "=" * 70)
    print("SCRAPED & TRANSLATED RESULT:")
    print("=" * 70)
    print(f"Original Text: {extracted_text}")
    print(f"Hindi Translation: {translation}")
