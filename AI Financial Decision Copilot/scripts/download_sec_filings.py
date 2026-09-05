"""
scripts/download_sec_filings.py
────────────────────────────────
Downloads SEC 10-K filings from the SEC EDGAR full-text search API.
No API key required — EDGAR is a public database.

Usage:
    python scripts/download_sec_filings.py --tickers AAPL MSFT GOOGL AMZN NVDA --years 2022 2023
    python scripts/download_sec_filings.py --all-sp500-sample   # downloads top 20 S&P 500 10-Ks
"""

import argparse
import json
import time
from pathlib import Path

import httpx
import sys
sys.path.append(str(Path(__file__).parent.parent))

from config import FILINGS_DIR
from loguru import logger

# ── EDGAR endpoints ────────────────────────────────────────────────────────────
EDGAR_BASE = "https://data.sec.gov"
EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index"
EDGAR_COMPANY_SEARCH = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt={year}-01-01&enddt={year}-12-31&forms=10-K"
HEADERS = {"User-Agent": "FinancialRAG nithinr1808@gmail.com"}  # SEC requires a User-Agent

# Top S&P 500 companies sample
SP500_SAMPLE = {
    "AAPL": "Apple Inc",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc",
    "AMZN": "Amazon.com Inc",
    "NVDA": "NVIDIA Corporation",
    "META": "Meta Platforms Inc",
    "TSLA": "Tesla Inc",
    "JPM": "JPMorgan Chase & Co",
    "V": "Visa Inc",
    "JNJ": "Johnson & Johnson",
}


def get_cik_for_ticker(ticker: str) -> str | None:
    """Resolve ticker symbol → SEC CIK number via EDGAR company search."""
    url = f"{EDGAR_BASE}/submissions/"
    # Use the company tickers JSON
    tickers_url = f"{EDGAR_BASE}/files/company_tickers.json"
    try:
        resp = httpx.get(tickers_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                cik = str(entry["cik_str"]).zfill(10)
                logger.info(f"Resolved {ticker} → CIK {cik}")
                return cik
    except Exception as e:
        logger.error(f"Failed to resolve CIK for {ticker}: {e}")
    return None


def get_10k_filings(cik: str, years: list[int]) -> list[dict]:
    """Fetch list of 10-K filings for a given CIK and year range."""
    url = f"{EDGAR_BASE}/submissions/CIK{cik}.json"
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch submissions for CIK {cik}: {e}")
        return []

    filings = []
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accession_numbers = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])

    for i, form in enumerate(forms):
        if form == "10-K":
            filing_year = int(filing_dates[i][:4])
            if not years or filing_year in years:
                filings.append({
                    "accession": accession_numbers[i].replace("-", ""),
                    "accession_formatted": accession_numbers[i],
                    "date": filing_dates[i],
                    "primary_doc": primary_docs[i],
                    "cik": cik,
                })
    return filings


def download_filing_text(cik: str, accession: str, primary_doc: str) -> str | None:
    """Download the actual 10-K filing document text."""
    # Try the primary document first
    url = f"{EDGAR_BASE}/Archives/edgar/data/{int(cik)}/{accession}/{primary_doc}"
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.warning(f"Primary doc failed ({url}): {e}")

    # Fallback: get filing index and find HTM/TXT file
    index_url = f"{EDGAR_BASE}/Archives/edgar/data/{int(cik)}/{accession}/{accession}-index.htm"
    try:
        resp = httpx.get(index_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        # Simple extraction — find first .htm document link
        for line in resp.text.splitlines():
            if ".htm" in line.lower() and "10-k" in line.lower():
                start = line.find('href="') + 6
                end = line.find('"', start)
                if start > 5:
                    doc_url = f"{EDGAR_BASE}{line[start:end]}"
                    r2 = httpx.get(doc_url, headers=HEADERS, timeout=60)
                    r2.raise_for_status()
                    return r2.text
    except Exception as e:
        logger.warning(f"Index fallback also failed: {e}")
    return None


def download_for_ticker(ticker: str, years: list[int], output_dir: Path) -> int:
    """Download all 10-K filings for one ticker. Returns number of files saved."""
    logger.info(f"Processing {ticker}...")
    cik = get_cik_for_ticker(ticker)
    if not cik:
        logger.warning(f"Could not find CIK for {ticker}, skipping.")
        return 0

    filings = get_10k_filings(cik, years)
    if not filings:
        logger.warning(f"No 10-K filings found for {ticker} in years {years}")
        return 0

    saved = 0
    ticker_dir = output_dir / ticker.upper()
    ticker_dir.mkdir(parents=True, exist_ok=True)

    for filing in filings:
        out_file = ticker_dir / f"{ticker}_{filing['date']}_10K.txt"
        if out_file.exists():
            logger.info(f"  Already downloaded: {out_file.name}")
            saved += 1
            continue

        logger.info(f"  Downloading {ticker} 10-K filed {filing['date']}...")
        text = download_filing_text(filing["cik"], filing["accession"], filing["primary_doc"])
        if text:
            out_file.write_text(text, encoding="utf-8", errors="replace")
            # Save metadata
            meta_file = ticker_dir / f"{ticker}_{filing['date']}_10K_meta.json"
            meta_file.write_text(json.dumps({
                "ticker": ticker,
                "cik": cik,
                "filing_date": filing["date"],
                "accession": filing["accession_formatted"],
                "source_url": f"{EDGAR_BASE}/Archives/edgar/data/{int(cik)}/{filing['accession']}/{filing['primary_doc']}",
            }, indent=2))
            logger.success(f"  Saved: {out_file.name} ({len(text):,} chars)")
            saved += 1
        else:
            logger.error(f"  Failed to download {ticker} 10-K filed {filing['date']}")

        time.sleep(0.5)  # EDGAR rate-limit: be polite

    return saved


def main():
    parser = argparse.ArgumentParser(description="Download SEC 10-K filings from EDGAR")
    parser.add_argument("--tickers", nargs="+", default=list(SP500_SAMPLE.keys()),
                        help="Ticker symbols to download (default: top 10 S&P 500)")
    parser.add_argument("--years", nargs="+", type=int, default=[2022, 2023],
                        help="Filing years to include (default: 2022 2023)")
    parser.add_argument("--output-dir", default=str(FILINGS_DIR),
                        help="Output directory for downloaded filings")
    parser.add_argument("--all-sp500-sample", action="store_true",
                        help="Download all 10 companies in the sample set")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tickers = list(SP500_SAMPLE.keys()) if args.all_sp500_sample else args.tickers
    years = args.years

    logger.info(f"Downloading 10-K filings for: {tickers}")
    logger.info(f"Years: {years}")
    logger.info(f"Output dir: {output_dir}")

    total = 0
    for ticker in tickers:
        count = download_for_ticker(ticker, years, output_dir)
        total += count
        time.sleep(1)  # Polite delay between companies

    logger.success(f"\nDone! Downloaded {total} filings to {output_dir}")
    logger.info("Next step: run `python scripts/ingest_documents.py` to build the vector index.")


if __name__ == "__main__":
    main()
