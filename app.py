
import streamlit as st
import pandas as pd
import numpy as np
import requests
st.set_page_config(page_title="EUR/USD Signal Bot", layout="wide")

st.title("EUR/USD Signal Dashboard")
st.caption("RSI + EMA | 1-minute strategy | Signal-only")

st.warning("এটি পরীক্ষামূলক সিগন্যাল টুল, আর্থিক পরামর্শ নয়। সিগন্যাল লাভের নিশ্চয়তা দেয় না।")

uploaded = st.file_uploader("Upload EUR/USD candle CSV", type=["csv"])

def calculate_signals(df):
    df.columns = [str(c).lower().strip() for c in df.columns]

    if "close" not in df.columns:
        raise ValueError("CSV file must contain a close column.")

    close = pd.to_numeric(df["close"], errors="coerce")
    df["close"] = close

    df["EMA9"] = close.ewm(span=9, adjust=False).mean()
    df["EMA21"] = close.ewm(span=21, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    df["Signal"] = "WAIT"
    df.loc[(df["EMA9"] > df["EMA21"]) & (df["RSI"] > 50), "Signal"] = "BUY"
    df.loc[(df["EMA9"] < df["EMA21"]) & (df["RSI"] < 50), "Signal"] = "SELL"
    return df

if uploaded is not None:
    try:
        data = pd.read_csv(uploaded)
        result = calculate_signals(data)

        a, b, c = st.columns(3)
        a.metric("BUY", int((result["Signal"] == "BUY").sum()))
        b.metric("SELL", int((result["Signal"] == "SELL").sum()))
        c.metric("WAIT", int((result["Signal"] == "WAIT").sum()))

        st.subheader("Latest signal")
        st.dataframe(result.tail(20), use_container_width=True)
        st.download_button(
            "Download signals CSV",
            result.to_csv(index=False).encode("utf-8"),
            "eurusd_signals.csv",
            "text/csv"
        )
    except Exception as e:
        st.error(f"Could not process CSV: {e}")
else:
    st.info("Upload candle data with a close column to calculate signals.")
