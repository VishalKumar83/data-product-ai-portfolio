<img width="101" height="16" alt="image" src="https://github.com/user-attachments/assets/b30cd631-da67-4cee-a4de-07d511c01aec" /># Investment Banking Valuation Toolkit

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive, production‑ready valuation toolkit that calculates the intrinsic value of any public company using five different methodologies, generates sensitivity tables and heatmaps, and produces a professional **football field chart** – exactly as used in investment banking pitch books.

---

## Overview

This project automates the entire valuation process for a given stock ticker. It fetches real‑time financial data from **Yahoo Finance** and **SEC EDGAR** (via `yfinance`), then performs:

- **Discounted Cash Flow (DCF) Analysis**
- **Comparable Company Analysis (Trading Comps)**
- **Precedent Transaction Analysis**
- **Leveraged Buyout (LBO) Analysis**
- **Sum‑of‑the‑Parts (SOTP) Analysis**

For each method, the toolkit produces a valuation range, and the results are consolidated into a **football field chart**. Full sensitivity analysis (2D tables and heatmaps) is provided for DCF and LBO models. All outputs are saved as Excel files and PNG images, ready to be included in reports or presentations.

---

## Key Features

- **Fully automated data collection** – no manual input beyond the ticker symbol.
- **Five valuation methodologies** – covers the core techniques used by investment banks.
- **Sensitivity analysis** – DCF sensitivity (WACC vs. terminal growth) and LBO sensitivity (purchase multiple vs. exit multiple) with heatmaps.
- **Trading Comps percentile valuations** – 25th, 50th, 75th percentiles of EV/Revenue, EV/EBITDA, and P/E.
- **Football field chart** – compares all valuation ranges with the current share price and the median of all midpoints.
- **Excel export** – all results, sensitivity tables, and percentile valuations are saved in a multi‑sheet Excel workbook.
- **Visualisations** – heatmaps and football field chart are saved as high‑resolution PNG files.

---

## Data Sources

| Source          | Data                                                          | Access                        |
|-----------------|---------------------------------------------------------------|-------------------------------|
| Yahoo Finance   | Stock price, financial statements (income, balance sheet, cash flow), market cap, shares outstanding, peer data | `yfinance` |
| Wikipedia       | S&P 500 constituents (for peer selection)                    | `requests` + `pandas`         |
| SEC EDGAR       | Financial facts (via Yahoo Finance) – no separate API required | `yfinance` |

All data is free, public, and updated daily.

---
## Example Output: General Electric (GE)

We ran the toolkit for GE Aerospace (ticker: GE) on April 2025. Below are the results.

Valuation Ranges
|Methodology	|Low ($)	|High ($)	|Midpoint ($) |
|-------------|---------|---------|-------------|
Comparable Company Analysis |	200.04	| 415.85	| 307.95|
Sum‑of‑the‑Parts (SOTP) |	99.97 |	149.95 |	124.96
Discounted Cash Flow (DCF) |	107.41 |	129.26 |	118.34
Precedent Transactions |	58.08 |	176.97 |	117.53
Leveraged Buyout (LBO) |	43.03 |	64.55 |	53.79

**Current share price: $281.16**
**Median of all valuation midpoints: $118.34 (approx)**

The current market price is significantly above all valuation ranges, suggesting the stock is overvalued relative to the fundamental analysis.

## Football Field Chart
<img width="1783" height="1184" alt="football_field" src="https://github.com/user-attachments/assets/a62f7a46-4159-4e5c-9ab4-66191dbd5206" />
The chart shows each valuation method as a horizontal bar. The red dashed line is the current price ($281.16); the green dashed line is the median of all midpoints ($118.34).


## DCF Sensitivity Heatmap

The DCF model’s output per share varies with the WACC (discount rate) and terminal growth rate.
<img width="1500" height="900" alt="dcf_sensitivity_heatmap" src="https://github.com/user-attachments/assets/7f4dc639-3948-487c-b8d2-89daaaed491d" />

Interpretation: Lower WACC and higher terminal growth produce higher valuations.

## LBO Sensitivity Heatmap
<img width="1500" height="900" alt="lbo_sensitivity_heatmap" src="https://github.com/user-attachments/assets/995af4a4-3669-4965-8293-f803e99d8e2a" />

The LBO model’s entry price depends on the purchase multiple (entry EV/EBITDA) and exit multiple (exit EV/EBITDA).

For GE, the LBO‑implied price ranges from ~$43 to $65 per share, well below the current market price.

Trading Comps Percentile Valuations

The toolkit also computes implied share prices using the 25th, 50th, and 75th percentiles of peer multiples:

| Multiple |	25th Percentile ($) |	50th Percentile ($) |	75th Percentile ($)|
|----------|----------------------|---------------------|--------------------|
|EV/Revenue |	200.4 |	231.84 |	264.46 |
|EV/EBITDA |	283.84 |	290.06 |	317.22 |
|P/E	| 283.84 |	314.73 |	415.85 |

These are exported to the Excel report.
