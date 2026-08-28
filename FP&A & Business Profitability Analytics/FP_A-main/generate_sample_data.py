"""
Sample Data Generator for FP&A Analysis Toolkit
================================================

This script generates realistic budget and actuals Excel files
for testing the FP&A Analysis Toolkit.

Usage: Run it from terminal/command line (Bash)
    python generate_sample_data.py

Output:
    - data/budget_2024.xlsx
    - data/actuals_2024.xlsx
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Configuration
FISCAL_YEAR = 2024
CURRENT_MONTH_INDEX = 9  # October (0-indexed)

DEPARTMENTS = ['Sales', 'Marketing', 'Operations', 'IT', 'Finance', 'HR']

COST_CENTERS = {
    'Sales': ['CC-1001', 'CC-1002', 'CC-1003'],
    'Marketing': ['CC-2001', 'CC-2002'],
    'Operations': ['CC-3001', 'CC-3002', 'CC-3003'],
    'IT': ['CC-4001', 'CC-4002'],
    'Finance': ['CC-5001'],
    'HR': ['CC-6001']
}

EXPENSE_CATEGORIES = [
    'Salaries & Wages',
    'Benefits',
    'Travel & Entertainment',
    'Marketing Spend',
    'Software & Licenses',
    'Office Supplies',
    'Rent & Utilities',
    'Professional Services',
    'Depreciation',
    'Other Operating Expenses'
]

REVENUE_CATEGORIES = [
    'Product Revenue',
    'Service Revenue',
    'Subscription Revenue',
    'Other Revenue'
]

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def generate_budget_actuals():
    """Generate realistic budget and actuals data"""

    print("=" * 80)
    print("SAMPLE DATA GENERATOR FOR FP&A TOOLKIT")
    print("=" * 80)
    print(f"\nGenerating data for FY{FISCAL_YEAR}...")
    print(
        f"Current period: {MONTHS[CURRENT_MONTH_INDEX]} (month {CURRENT_MONTH_INDEX + 1} of 12)")

    np.random.seed(42)  # For reproducibility

    budget_records = []
    actuals_records = []

    # ========================================================================
    # GENERATE EXPENSE DATA
    # ========================================================================
    print("\n[1/2] Generating expense data...")

    expense_count = 0
    for dept in DEPARTMENTS:
        for cc in COST_CENTERS[dept]:
            for account in EXPENSE_CATEGORIES:
                # Base amount varies by account type
                if 'Salaries' in account or 'Benefits' in account:
                    base_amount = np.random.uniform(50000, 150000)
                elif 'Marketing' in account:
                    base_amount = np.random.uniform(20000, 80000)
                elif 'Software' in account:
                    base_amount = np.random.uniform(5000, 30000)
                else:
                    base_amount = np.random.uniform(5000, 50000)

                for month_idx, month in enumerate(MONTHS):
                    # Add seasonality (higher in Q4)
                    seasonal_factor = 1 + \
                        (0.15 * np.sin(month_idx * np.pi / 6))

                    # Budget with slight random variation
                    budget_amount = base_amount * seasonal_factor * \
                        np.random.uniform(0.95, 1.05)

                    budget_records.append({
                        'Department': dept,
                        'Cost_Center': cc,
                        'Account': account,
                        'Month': month,
                        'Budget': round(budget_amount, 2),
                        'Type': 'Expense'
                    })
                    expense_count += 1

                    # Generate actuals only for YTD months
                    if month_idx <= CURRENT_MONTH_INDEX:
                        # Actuals vary from budget by -15% to +15%
                        variance_factor = np.random.uniform(0.85, 1.15)
                        actual_amount = budget_amount * variance_factor

                        # Add some accounts with larger variances (material variances)
                        if np.random.random() < 0.1:  # 10% chance of large variance
                            variance_factor = np.random.uniform(0.70, 1.30)
                            actual_amount = budget_amount * variance_factor

                        actuals_records.append({
                            'Department': dept,
                            'Cost_Center': cc,
                            'Account': account,
                            'Month': month,
                            'Actual': round(actual_amount, 2),
                            'Type': 'Expense'
                        })

    print(f"  ✓ Generated {expense_count:,} expense budget records")
    print(
        f"  ✓ Generated {len(actuals_records):,} expense actuals records (YTD)")

    # ========================================================================
    # GENERATE REVENUE DATA
    # ========================================================================
    print("\n[2/2] Generating revenue data...")

    revenue_count = 0
    for month_idx, month in enumerate(MONTHS):
        for account in REVENUE_CATEGORIES:
            # Revenue varies by type
            if 'Product' in account:
                base_revenue = np.random.uniform(300000, 600000)
            elif 'Service' in account:
                base_revenue = np.random.uniform(200000, 400000)
            elif 'Subscription' in account:
                base_revenue = np.random.uniform(150000, 300000)
            else:
                base_revenue = np.random.uniform(50000, 150000)

            # Stronger seasonality for revenue (Q4 spike)
            seasonal_factor = 1 + (0.25 * np.sin(month_idx * np.pi / 6))

            budget_revenue = base_revenue * seasonal_factor

            budget_records.append({
                'Department': 'Revenue',
                'Cost_Center': 'REV-001',
                'Account': account,
                'Month': month,
                'Budget': round(budget_revenue, 2),
                'Type': 'Revenue'
            })
            revenue_count += 1

            # Generate actuals for YTD
            if month_idx <= CURRENT_MONTH_INDEX:
                # Revenue typically has tighter variance
                variance_factor = np.random.uniform(0.90, 1.10)
                actual_revenue = budget_revenue * variance_factor

                actuals_records.append({
                    'Department': 'Revenue',
                    'Cost_Center': 'REV-001',
                    'Account': account,
                    'Month': month,
                    'Actual': round(actual_revenue, 2),
                    'Type': 'Revenue'
                })

    print(f"  ✓ Generated {revenue_count:,} revenue budget records")
    print(
        f"  ✓ Generated {len([r for r in actuals_records if r['Type'] == 'Revenue']):,} revenue actuals records (YTD)")

    # ========================================================================
    # CREATE DATAFRAMES
    # ========================================================================
    df_budget = pd.DataFrame(budget_records)
    df_actuals = pd.DataFrame(actuals_records)

    # ========================================================================
    # PRINT SUMMARY STATISTICS
    # ========================================================================
    print("\n" + "=" * 80)
    print("DATA SUMMARY")
    print("=" * 80)

    budget_summary = df_budget.groupby('Type')['Budget'].sum()
    actuals_summary = df_actuals.groupby('Type')['Actual'].sum()

    print("\nFull Year Budget:")
    print(f"  Revenue:  ${budget_summary.get('Revenue', 0):>15,.0f}")
    print(f"  Expense:  ${budget_summary.get('Expense', 0):>15,.0f}")
    print(
        f"  Net Income: ${budget_summary.get('Revenue', 0) - budget_summary.get('Expense', 0):>15,.0f}")

    print(f"\nYTD Actuals (Through {MONTHS[CURRENT_MONTH_INDEX]}):")
    print(f"  Revenue:  ${actuals_summary.get('Revenue', 0):>15,.0f}")
    print(f"  Expense:  ${actuals_summary.get('Expense', 0):>15,.0f}")
    print(
        f"  Net Income: ${actuals_summary.get('Revenue', 0) - actuals_summary.get('Expense', 0):>15,.0f}")

    # Calculate YTD variance
    ytd_budget = df_budget[df_budget['Month'].isin(
        MONTHS[:CURRENT_MONTH_INDEX+1])].groupby('Type')['Budget'].sum()
    ytd_variance_pct = ((actuals_summary - ytd_budget) / ytd_budget * 100)

    print(f"\nYTD Variance vs Budget:")
    for type_name in ['Revenue', 'Expense']:
        if type_name in ytd_variance_pct:
            var_pct = ytd_variance_pct[type_name]
            print(f"  {type_name}: {var_pct:+.1f}%")

    return df_budget, df_actuals


def save_to_excel(df_budget, df_actuals):
    """Save data to Excel files"""

    print("\n" + "=" * 80)
    print("SAVING DATA TO EXCEL")
    print("=" * 80)

    # Create data directory
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)

    # Save budget
    budget_file = data_dir / f'budget_{FISCAL_YEAR}.xlsx'
    print(f"\nSaving budget to: {budget_file}")
    df_budget.to_excel(budget_file, index=False, sheet_name='Budget')
    print(f"  ✓ Saved {len(df_budget):,} records")

    # Save actuals
    actuals_file = data_dir / f'actuals_{FISCAL_YEAR}.xlsx'
    print(f"\nSaving actuals to: {actuals_file}")
    df_actuals.to_excel(actuals_file, index=False, sheet_name='Actuals')
    print(f"  ✓ Saved {len(df_actuals):,} records")

    print("\n" + "=" * 80)
    print("✓ DATA GENERATION COMPLETE!")
    print("=" * 80)

    print(f"""
Next Steps:
1. Open Jupyter Notebook: jupyter notebook fpa_analysis_toolkit.ipynb
2. Run Cells 1-9 (one time setup)
3. In Cell 2, verify:
   - CURRENT_MONTH = '{MONTHS[CURRENT_MONTH_INDEX]}'
   - BUDGET_FILE = '{budget_file}'
   - ACTUALS_FILE = '{actuals_file}'
4. Run Cell 10 to execute the analysis
5. Check the output/ folder for your Excel report!
""")


def preview_data(df_budget, df_actuals):
    """Show sample of generated data"""

    print("\n" + "=" * 80)
    print("DATA PREVIEW")
    print("=" * 80)

    print("\nBudget Sample (first 10 rows):")
    print(df_budget.head(10).to_string(index=False))

    print("\n\nActuals Sample (first 10 rows):")
    print(df_actuals.head(10).to_string(index=False))


if __name__ == "__main__":
    # Generate data
    df_budget, df_actuals = generate_budget_actuals()

    # Show preview
    preview_data(df_budget, df_actuals)

    # Save to Excel
    save_to_excel(df_budget, df_actuals)
