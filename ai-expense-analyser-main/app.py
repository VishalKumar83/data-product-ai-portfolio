import streamlit as st
import pandas as pd
import numpy as np

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB

st.title("🤖 AI Expense Analyzer (Fintech Project)")

# ==============================
# 🔹 Load Training Data
# ==============================
train_df = pd.read_csv("data.csv")

# Convert text → numerical features
vectorizer = CountVectorizer()
X = vectorizer.fit_transform(train_df["description"])

# Train ML model
model = MultinomialNB()
model.fit(X, train_df["category"])

# ==============================
# 🔹 Upload User File
# ==============================
uploaded_file = st.file_uploader("📁 Upload your expenses CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # ==============================
    # 🔹 ML Prediction
    # ==============================
    X_test = vectorizer.transform(df["description"])
    df["category"] = model.predict(X_test)

    st.subheader("📄 Classified Data")
    st.dataframe(df)

    # ==============================
    # 🔹 Summary
    # ==============================
    summary = df.groupby("category")["amount"].sum()

    st.subheader("📊 Summary")
    st.write(summary)

    st.subheader("💵 Total Spending")
    st.write(summary.sum())

    st.subheader("📈 Spending Breakdown")
    st.bar_chart(summary)

    # ==============================
    # 🔹 Anomaly Detection
    # ==============================
    st.subheader("🚨 Anomaly Detection")

    mean = np.mean(df["amount"])
    std = np.std(df["amount"])

    df["anomaly"] = df["amount"].apply(
        lambda x: "⚠️ Anomaly" if abs(x - mean) > 2 * std else "Normal"
    )

    st.dataframe(df)

    anomalies = df[df["anomaly"] == "⚠️ Anomaly"]

    if not anomalies.empty:
        st.subheader("🚨 Suspicious Transactions")
        st.write(anomalies)
    else:
        st.success("No suspicious transactions detected ✅")