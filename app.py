# app.py
import time
from typing import Optional
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Accounting Ratios Dashboard", page_icon="📈")

st.title("📈 Current & Acid-Test (Quick) Ratios")
st.caption("Reads the latest single record from Google Sheets (row 2).")

REFRESH_SECONDS = 5

# ---- Google Sheets helpers ---------------------------------------------------
def get_gspread_client() -> gspread.Client:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

def open_ws(client: gspread.Client) -> gspread.Worksheet:
    ss = client.open_by_key(st.secrets["gsheet_id"])
    ws_name = st.secrets.get("gsheet_worksheet", "latest")
    try:
        return ss.worksheet(ws_name)
    except gspread.WorksheetNotFound:
        # Create with header row if missing
        ws = ss.add_worksheet(title=ws_name, rows=10, cols=6)
        ws.update("A1:D1", [["timestamp_utc", "current_assets", "current_liabilities", "inventory"]])
        return ws

def read_latest() -> Optional[pd.DataFrame]:
    client = get_gspread_client()
    ws = open_ws(client)
    # Expect headers in row 1; values in row 2
    data = ws.get_values("A1:D2")
    if len(data) < 2 or len(data[1]) < 4:
        return None
    df = pd.DataFrame([data[1]], columns=data[0])
    return df

# ---- Ratios ------------------------------------------------------------------
def compute_ratios(ca: float, cl: float, inv: float):
    if cl <= 0:
        return None, None
    return ca / cl, (ca - inv) / cl

# ---- UI ----------------------------------------------------------------------
latest = read_latest()

if latest is None or latest.empty:
    st.warning("No data found yet. Open **🔁 Data Generator** to start emitting values.")
else:
    row = latest.iloc[0]
    try:
        ca = float(row["current_assets"])
        cl = float(row["current_liabilities"])
        inv = float(row["inventory"])
    except Exception:
        st.error("Sheet has invalid numbers. Check row 2 (A2:D2).")
        st.stop()

    cr, qr = compute_ratios(ca, cl, inv)

    top = st.columns(3)
    top[0].metric("Current Assets (£)", f"{ca:,.2f}")
    top[1].metric("Current Liabilities (£)", f"{cl:,.2f}")
    top[2].metric("Inventory (£)", f"{inv:,.2f}")

    st.divider()
    r1, r2 = st.columns(2)
    r1.metric("Current Ratio", f"{cr:.2f}" if cr is not None else "—")
    r2.metric("Acid-Test (Quick) Ratio", f"{qr:.2f}" if qr is not None else "—")

    if "timestamp_utc" in row and row["timestamp_utc"]:
        st.caption(f"Last updated (UTC): {row['timestamp_utc']}")

time.sleep(REFRESH_SECONDS)
st.rerun()
