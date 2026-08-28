# Customer Churn Prediction and Explainability using XGBoost

## Project Overview

Every subscription or usage-based platform loses a slice of its customer base every month — quietly, and usually before anyone notices. This project builds a churn prediction pipeline that goes one step further than a typical classification notebook: instead of just outputting a probability, it explains *why* a specific customer is flagged as high risk, and translates that into a concrete retention action.

The same pattern applies well beyond telecom. A large multi-service platform operating across ride-hailing, food delivery, and digital payments — the kind of business common across Southeast Asia — deals with the exact same underlying problem: users who quietly reduce activity across trips, orders, or transactions before eventually leaving altogether. A model like this, paired with explainability, is what lets a growth or retention team move from broad, blanket campaigns to targeted interventions aimed at the right users, for the right reason.

## Dataset

**Source:** Telco Customer Churn (IBM) dataset
**Kaggle path used in this notebook:** `/kaggle/input/datasets/yeanzc/telco-customer-churn-ibm-dataset`

The dataset contains customer-level records including demographics (gender, senior citizen status, partner/dependents), account information (tenure, contract type, payment method), service subscriptions (internet, phone, streaming, security add-ons), billing details (monthly and total charges), and a churn label.

The notebook auto-detects the CSV file inside the dataset folder and the exact name of the target column (`Churn`, `Churn Label`, or `Churn Value`, depending on dataset version), so it does not need to be modified if Kaggle updates the dataset export slightly.

## Project Workflow

1. **Load & Explore** — pull the dataset, check shape, types, missing values, and target balance
2. **EDA** — visualize churn against tenure, monthly charges, contract type, and internet service
3. **Data Cleaning** — fix `TotalCharges`, drop identifiers, encode the target
4. **Feature Engineering** — add a handful of practical, interpretable features
5. **Encoding** — label-encode binary categorical columns, one-hot encode the rest
6. **Train/Test Split** — 80/20 stratified split
7. **Model Training** — compare Logistic Regression, Random Forest, and XGBoost
8. **Hyperparameter Tuning** — lightweight `RandomizedSearchCV` on XGBoost only
9. **Final Evaluation** — confusion matrix, ROC curve, classification report
10. **Explainability** — SHAP summary plots and a per-customer explanation function
11. **Risk Scoring** — convert probabilities into Low / Medium / High risk tiers
12. **Recommendations** — rule-based retention actions per risk tier
13. **Save & Infer** — persist the model with `joblib` and demonstrate inference on a new customer

## Technologies Used

| Category | Tools |
|---|---|
| Language | Python 3 |
| Data handling | Pandas, NumPy |
| Visualization | Matplotlib, Seaborn, Plotly |
| Modeling | Scikit-learn (Logistic Regression, Random Forest), XGBoost |
| Explainability | SHAP |
| Persistence | Joblib |

No deep learning frameworks, no external experiment trackers, no orchestration tools — the goal is a lean, understandable pipeline, not a heavyweight MLOps stack.

## How to Run on Kaggle

1. Create a new Kaggle notebook.
2. Add the dataset **Telco Customer Churn (IBM)** (`yeanzc/telco-customer-churn-ibm-dataset`) as a data source. Kaggle will mount it automatically under `/kaggle/input/...`.
3. Upload `Customer_Churn_Prediction.ipynb` or copy its cells into your Kaggle notebook.
4. Confirm the dataset path in Section 3 matches how Kaggle mounted it (this notebook auto-searches the folder for the CSV, so minor path differences are handled automatically).
5. Run all cells top to bottom (**Run All**). No manual edits should be required.
6. All required libraries (Pandas, Scikit-learn, XGBoost, SHAP, etc.) are pre-installed in the standard Kaggle Python environment.

## Expected Outputs

- EDA plots: churn distribution, tenure/monthly charge distributions, contract & internet service breakdowns, correlation heatmap
- A model comparison table (Accuracy, Precision, Recall, F1, ROC-AUC) across three models
- Best hyperparameters found for XGBoost via randomized search
- Confusion matrix and ROC curve for the final tuned model
- SHAP global feature importance and summary plot
- Per-customer explanation output via `explain_customer(index)`
- Risk category distribution across the test set
- Saved model artifacts: `xgboost_model.pkl`, `feature_columns.pkl`, `encoder.pkl`
- A sample inference run showing prediction, probability, risk level, and recommended action

## Model Used

**XGBoost Classifier**, tuned via `RandomizedSearchCV` over `max_depth`, `learning_rate`, `n_estimators`, and `subsample`. Chosen over Logistic Regression and Random Forest for its typically stronger ROC-AUC on this kind of mixed numeric/categorical tabular data, while remaining fully explainable via SHAP's `TreeExplainer`.

## Project Structure

```
Customer_Churn_Prediction.ipynb   # End-to-end notebook (data → model → explainability → inference)
README.md                          # This file

Artifacts generated when the notebook runs:
xgboost_model.pkl                  # Trained, tuned XGBoost model
feature_columns.pkl                # Exact feature column order expected by the model
encoder.pkl                        # Label encoders for binary categorical columns
```

## Future Improvements

- **Customer Lifetime Value (CLTV)** — weight retention effort by customer value, not just churn probability
- **Real-time prediction** — score customers continuously as behavior changes, rather than in a static batch
- **Model monitoring** — track prediction drift and feature drift over time as customer behavior and pricing evolve
