"""
Pattern 05: Selenium Dynamic Scraping + Vector RAG + DeepEval Evaluation
A comprehensive TestOps showcase:
1. Selenium loads an IMDb movie review page and waits for client-side JavaScript rendering.
2. Extracts page body text and chunks text with a sliding window (1200 size, 150 overlap).
3. Indexes chunks into dense vector embeddings using Cohere embed-v4.0.
4. Performs semantic retrieval and generates a grounded movie review summary.
5. Evaluates summary quality using DeepEval metrics (AnswerRelevancyMetric & HallucinationMetric)
   via custom CohereModel judge.
"""

import os
from pathlib import Path
import sys
import time
import numpy as np
import cohere
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

# Ensure root directory is on sys.path for src imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Ensure UTF-8 output on Windows consoles
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

load_dotenv()
api_key = os.getenv("COHERE_API_KEY")
if not api_key:
    raise ValueError("COHERE_API_KEY not found. Please set it in your .env file.")

from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric, HallucinationMetric
from src.cohere_evalmodel import CohereModel

co = cohere.ClientV2(api_key=api_key)

MOVIE_URL = "https://www.imdb.com/title/tt33764258/"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150
TOP_K = 6
EMBED_MODEL = "embed-v4.0"
CHAT_MODEL = "command-a-03-2025"


def scrape_rendered_page(url: str) -> str:
    """Load dynamic page with Selenium Chrome, allowing JavaScript to execute."""
    print(f"\n[Step 1] Loading dynamic IMDb page with Selenium: {url}...")
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1200")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            lambda browser: browser.execute_script("return document.readyState") == "complete"
        )
        time.sleep(3)  # Allow dynamic review components to settle
        body_text = driver.find_element("tag name", "body").text.strip()
        print(f"Extracted {len(body_text)} characters of rendered text.")
        return body_text
    finally:
        driver.quit()


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        chunk = text[start : start + size].strip()
        if chunk:
            chunks.append(chunk)
        start += size - overlap
    return chunks


def run_scraping_rag_pipeline():
    page_text = scrape_rendered_page(MOVIE_URL)
    chunks = chunk_text(page_text)
    print(f"[Step 2] Chunked page into {len(chunks)} overlapping segments.")

    print(f"[Step 3] Generating dense embeddings with '{EMBED_MODEL}'...")
    # Index up to 30 chunks to maintain fast execution
    index_chunks = chunks[:30]
    embed_resp = co.embed(
        model=EMBED_MODEL,
        texts=index_chunks,
        input_type="search_document",
        embedding_types=["float"]
    )
    doc_vectors = np.array(embed_resp.embeddings.float)

    query = "Summarize the audience and critic reviews for this movie. What are the key praises and criticisms?"
    print(f"\n[Step 4] Query: \"{query}\"")

    query_resp = co.embed(
        model=EMBED_MODEL,
        texts=[query],
        input_type="search_query",
        embedding_types=["float"]
    )
    q_vec = np.array(query_resp.embeddings.float[0])

    scores = doc_vectors @ q_vec
    top_indices = scores.argsort()[-TOP_K:][::-1]
    retrieved_context = [index_chunks[int(i)] for i in top_indices]

    print(f"[Step 5] Generating grounded review summary with '{CHAT_MODEL}'...")
    prompt = f"""
Summarize the reviews for this movie using strictly the context below.
Capture both positive and critical feedback.

Context:
{"\n\n---\n\n".join(retrieved_context)}

Question:
{query}
"""
    ans_resp = co.chat(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=300
    )
    actual_summary = "".join(
        item.text for item in ans_resp.message.content
        if getattr(item, "text", None)
    ).strip()

    print("\n" + "=" * 70)
    print("AI-GENERATED REVIEW SUMMARY:")
    print("=" * 70)
    print(actual_summary)

    # Step 6: DeepEval Quality Audit
    print("\n[Step 6] Auditing summary quality with DeepEval and Cohere LLM Judge...")
    judge = CohereModel()

    relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=judge)
    hallucination_metric = HallucinationMetric(threshold=0.7, model=judge)

    test_case = LLMTestCase(
        input=query,
        actual_output=actual_summary,
        context=retrieved_context,
        retrieval_context=retrieved_context
    )

    assert_test(test_case, [relevancy_metric, hallucination_metric])

    for metric in [relevancy_metric, hallucination_metric]:
        print(f"\nMetric: {metric.__class__.__name__}")
        print(f"Score:   {metric.score}")
        print(f"Passed:  {metric.success}")
        print(f"Reason:  {getattr(metric, 'reason', 'N/A')}")


if __name__ == "__main__":
    run_scraping_rag_pipeline()
