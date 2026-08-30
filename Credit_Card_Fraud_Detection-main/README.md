# 💳 Credit Card Fraud Detection using Machine Learning

## 📌 Project Overview
This project builds a **machine learning model** to detect fraudulent credit card transactions from historical financial data.  
The goal is to help financial institutions **identify suspicious behavior early**, reduce risks, and prevent monetary losses.  

Fraud detection is a **highly imbalanced classification problem**: fraudulent transactions account for less than **0.02%** of all cases.  
The project focuses on handling this imbalance and building a robust model that balances **high precision** (few false alarms) with **high recall** (catching real frauds).  

---

## 🚀 Features
- **Exploratory Data Analysis (EDA):**
  - Distribution of fraud vs. valid transactions
  - Transaction amount comparison
  - Correlation heatmaps to analyze feature relationships
- **Data Preprocessing:**
  - Handled class imbalance (fraudulent vs. non-fraudulent)
  - Converted dataset into feature matrix `X` and target `y`
  - Train-test split (80/20) with reproducibility
- **Modeling:**
  - Implemented **Random Forest Classifier**
  - Tuned hyperparameters for better generalization
  - Evaluated using multiple metrics beyond accuracy
- **Evaluation Metrics:**
  - Accuracy, Precision, Recall, F1-Score, Matthews Correlation Coefficient (MCC)
  - Confusion Matrix for visualizing detection performance

---

## 📊 Dataset
- **Source:** [Kaggle Credit Card Fraud Detection Dataset](https://www.kaggle.com/mlg-ulb/creditcardfraud)
- **Size:** 284,807 transactions  
- **Features:**  
  - `Time`: Seconds elapsed since the first transaction  
  - `V1–V28`: PCA-transformed features for anonymity  
  - `Amount`: Transaction amount  
  - `Class`: Target (0 = Valid, 1 = Fraudulent)  

---

## 🛠️ Tech Stack
- **Languages/Tools:** Python, Jupyter Notebook  
- **Libraries:** NumPy, Pandas, Matplotlib, Seaborn, Scikit-learn  

---

## 📈 Results
- **Accuracy:** 99.96% (misleading due to imbalance)  
- **Precision:** 98.73% (low false positives)  
- **Recall:** 79.59% (majority of frauds detected)  
- **F1-Score:** 88.14% (balance between precision & recall)  
- **MCC:** 0.8863 (balanced metric for imbalanced datasets)  

Confusion Matrix visualization confirms the model is strong but misses a small fraction of fraud cases.  

---

## 🔮 Future Improvements
- Handle class imbalance with **SMOTE (oversampling)** or **undersampling** techniques  
- Experiment with **XGBoost, LightGBM, and ensemble models**  
- Deploy the model as a **real-time fraud detection API** for financial systems  
- Add **cost-sensitive learning** (penalize missing fraud cases more heavily)  

---

## 📂 Project Structure
CreditCardFraudDetection/
│── data/
│ └── creditcard.csv
│── notebooks/
│ └── fraud_detection.ipynb
│── README.md
│── requirements.txt
│── results/
│ └── confusion_matrix.png



---

## 🙌 Acknowledgements
- Dataset: [Kaggle - Credit Card Fraud Detection](https://www.kaggle.com/mlg-ulb/creditcardfraud)  
- Inspired by finance security challenges and anomaly detection research.  

---
