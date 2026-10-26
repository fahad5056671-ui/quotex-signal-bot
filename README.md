
import requests streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="EUR/USD OTC Signal Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("EUR/USD OTC Signal Dashboard")
st.caption("RSI 14 + EMA 9/21 | 1-minute | Signal only")

st.warning(
    "সিগন্যাল নিশ্চিত ভবিষ্যদ্বাণী নয়। "
    "এটি আর্থিক পরামর্শ নয় এবং লাভের নিশ্চয়তা দেয় না।"
)

st.markdown("""
**সিগন্যালের নিয়ম**
- BUY: EMA 9 > EMA 21 এবং RSI > 50
- SELL: EMA 9 < EMA 21 এবং RSI < 50
- WAIT: অন্য সব ক্ষেত্রে
""")

uploaded_file = st.file_uploader(
    "বন্ধ হওয়া 1-minute candle-এর CSV আপলোড করুন",
    type=["csv"]
)

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    rsi = rsi.mask(
        (avg_loss == 0) & (avg_gain > 0), 100
    )
    rsi = rsi.mask(
        (avg_gain == 0) & (avg_loss > 0), 0
    )
    rsi = rsi.mask(
        (avg_gain == 0) & (avg_loss == 0), 50
    )

    return rsi

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)

        # Column names standardize
        df.columns = [
            str(col).strip().lower()
            for col in df.columns
        ]

        if "close" not in df.columns:
            st.error(
                "CSV ফাইলে close নামে একটি মূল্য কলাম থাকতে হবে।"
            )
            st.stop()

        df["close"] = pd.to_numeric(
            df["close"], errors="coerce"
        )

        df = df.dropna(subset=["close"]).copy()

        if len(df) < 30:
            st.error(
                "কমপক্ষে 30টি বন্ধ হওয়া candle দিন।"
            )
            st.stop()

        # If a time column exists, sort chronologically
        time_col = next(
            (
                col for col in
                ["datetime", "timestamp", "time", "date"]
                if col in df.columns
            ),
            None
        )

        if time_col:
            df[time_col] = pd.to_datetime(
                df[time_col], errors="coerce", utc=True
            )
            df = df.dropna(subset=[time_col])
            df = df.sort_values(time_col)

        df = df.drop_duplicates(
            subset=[time_col] if time_col else ["close"],
            keep="last"
        ).reset_index(drop=True)

        if len(df) < 30:
            st.error("পর্যাপ্ত বৈধ candle পাওয়া যায়নি।")
            st.stop()

        df["ema9"] = df["close"].ewm(
            span=9, adjust=False
        ).mean()

        df["ema21"] = df["close"].ewm(
            span=21, adjust=False
        ).mean()

        df["rsi14"] = calculate_rsi(df["close"])

        def get_signal(row):
            if pd.isna(row["rsi14"]):
                return "WAIT"

            if (
                row["ema9"] > row["ema21"]
                and row["rsi14"] > 50
            ):
                return "BUY"

            if (
                row["ema9"] < row["ema21"]
                and row["rsi14"] < 50
            ):
                return "SELL"

            return "WAIT"

        df["signal"] = df.apply(get_signal, axis=1)

        latest = df.iloc[-1]
        signal = latest["signal"]

        st.subheader("সর্বশেষ বন্ধ হওয়া candle-এর সিগন্যাল")

        if signal == "BUY":
            st.success("🟢 BUY — ঊর্ধ্বমুখী শর্ত মিলেছে")
        elif signal == "SELL":
            st.error("🔴 SELL — নিম্নমুখী শর্ত মিলেছে")
        else:
            st.info("🟡 WAIT — পরিষ্কার সিগন্যাল নেই")

        col1, col2, col3 = st.columns(3)

        col1.metric("Close", f'{latest["close"]:.5f}')
        col2.metric("EMA 9", f'{latest["ema9"]:.5f}')
        col3.metric("EMA 21", f'{latest["ema21"]:.5f}')

        st.metric("RSI 14", f'{latest["rsi14"]:.2f}')

        if time_col:
            st.caption(
                "শেষ candle-এর সময় (UTC): "
                + str(latest[time_col])
            )

        st.subheader("সাম্প্রতিক সিগন্যাল")
        show_cols = []
        if time_col:
            show_cols.append(time_col)

        show_cols += [
            "close", "ema9", "ema21", "rsi14", "signal"
        ]

        st.dataframe(
            df[show_cols].tail(20),
            use_container_width=True
        )
st.subheader("Quotex OTC ডেটা পরীক্ষা")

if st.button("EUR/USD OTC ডেটা আনুন"):
    try:
        api_key = st.secrets["OTCHARTS_API_KEY"]

        response = requests.get(
            "https://otcharts.com/v1/candles",
            headers={"Authorization": f"Bearer {api_key}"},
            params={
                "venue": "quotex",
                "symbol": "EURUSD_otc",
                "tf": 60,
                "limit": 100,
            },
            timeout=20,
        )

        if response.status_code != 200:
            st.error(
                f"API সমস্যা ({response.status_code}): "
                "ডেটা পাওয়া যায়নি। API plan ও symbol যাচাই করুন।"
            )
        else:
            payload = response.json()
            candles = payload.get("candles", [])

            if not candles:
                st.warning("API কোনো candle ফেরত দেয়নি।")
            else:
                live_df = pd.DataFrame(candles)
                live_df["time"] = pd.to_datetime(
                    live_df["time"], unit="s", utc=True
                )
                st.success(
                    f"{len(live_df)}টি candle পাওয়া গেছে।"
                )
                st.dataframe(live_df, use_container_width=True)

    except KeyError:
        st.error("Streamlit Secrets-এ API key যোগ করা নেই।")
    except Exception as e:
        st.error(f"ডেটা আনতে সমস্যা হয়েছে: {e}")
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "সিগন্যাল CSV ডাউনলোড",
            data=csv_data,
            file_name="eurusd_signals.csv",
            mime="text/csv"
        )

        st.caption(
            "এই অ্যাপ CSV-তে থাকা candle বিশ্লেষণ করে। "
            "এটি নিজে থেকে live Quotex OTC data আনে না। "
            "শুধু সম্পূর্ণ বন্ধ হওয়া candle ব্যবহার করুন।"
        )

    except Exception as e:
        st.error(f"CSV পড়তে সমস্যা হয়েছে: {e}")

else:
    st.info(
        "শুরু করতে close মূল্যসহ বন্ধ হওয়া 1-minute candle-এর CSV আপলোড করুন।"
    )
