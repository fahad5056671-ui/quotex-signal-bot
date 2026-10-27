
import streamlit as st
import pandas as pd
import numpy as np
import requests
st.set_page_config(page_title="EUR/USD Signal Bot", layout="wide")

st.title("EUR/USD Signal Dashboard")
st.caption("RSI + EMA | 1-minute strategy | Signal-only")

st.warning("এটি পরীক্ষামূলক সিগন্যাল টুল, আর্থিক পরামর্শ নয়। সিগন্যাল লাভের নিশ্চয়তা দেয় না।")

uploaded = st.file_uploader("Upload EUR/USD candle CSV", type=["csv"])


st.subheader("Live API Candle Data")

try:
    api_key = st.secrets["OTCHARTS_API_KEY"]

    response = requests.get(
        "https://otcharts.com/v1/candles",
        headers={"Authorization": f"Bearer {api_key}"},
        params={
            "venue": "quotex",
            "symbol": "EURUSD_otc",
            "tf": 60,
            "limit": 100
        },
        timeout=20
    )

    if response.status_code == 200:
        candles = response.json().get("candles", [])
        if candles:
            api_data = pd.DataFrame(candles)
            result = calculate_signals(api_data)
            st.success("ক্যান্ডেল ডেটা পাওয়া গেছে!")
            st.dataframe(
                result.tail(20),
                use_container_width=True
            )
        else:
            st.warning("API কোনো ক্যান্ডেল ফেরত দেয়নি।")
    else:
        st.error(
            f"API Error {response.status_code}: "
            f"{response.text}"
        )

except Exception as e:
    st.error(f"API সংযোগে সমস্যা: {e}")
 calculate_signals(df):
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
        result =result = calculate_signals(data)

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

def result = calculate_signals(data):
    df = df.copy()

    # প্রয়োজনীয় candle columns আছে কি না পরীক্ষা
    required = ["open", "high", "low", "close"]
    if not all(col in df.columns for col in required):
        return df

    df["EMA9"] = df["close"].ewm(span=9, adjust=False).mean()
    df["EMA21"] = df["close"].ewm(span=21, adjust=False).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(0, float("nan"))
    df["RSI"] = 100 - (100 / (1 + rs))

    df["Signal"] = "WAIT"
    df.loc[
        (df["EMA9"] > df["EMA21"]) & (df["RSI"] < 70),
        "Signal"
    ] = "BUY"
    df.loc[
        (df["EMA9"] < df["EMA21"]) & (df["RSI"] > 30),
        "Signal"
    ] = "SELL"

    return df
