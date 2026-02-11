import streamlit as st
import pandas as pd
import requests
import time
import json

# --- Page Config ---
st.set_page_config(page_title="Polkadot Subscan Fetcher", page_icon="🪙", layout="wide")

# --- App Title ---
st.title("🪙 Polkadot Subscan Data Fetcher (Fees, Amount, Sender, From, To)")
st.markdown("""
**Instructions:**
1. Upload your CSV.
2. Select the Hash column.
3. Click "Fetch Data".

**Captures:** `Estimated Fee`, `Used Fee`, `Transfer Amount`, `Sender`, `From`, `To`
""")

# --- Sidebar ---
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Subscan API Key (Optional)", type="password")
sleep_time = st.sidebar.slider("Seconds between requests", 0.1, 2.0, 0.4)

# --- Helper: Format DOT ---
def format_dot(raw_amount, decimals=10):
    try:
        val = float(raw_amount) / (10 ** decimals)
        formatted_val = f"{val:,.10f}".rstrip('0').rstrip('.')
        return f"{formatted_val} DOT"
    except:
        return None

# --- Helper: Extract Address from Param ---
def extract_address(value):
    # Sometimes 'dest' is just a string, sometimes it's a dict like {'Id': '...'}
    if isinstance(value, dict):
        return value.get('Id', str(value))
    return str(value)

# --- Main Logic ---
uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.dataframe(df.head())

    columns = df.columns.tolist()
    hash_col = st.selectbox("Select Transaction Hash Column", columns)

    if st.button("Fetch Data"):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        headers = {"Content-Type": "application/json", "User-Agent": "StreamlitApp"}
        if api_key: headers["X-API-Key"] = api_key

        total_tx = len(df)
        
        for index, row in df.iterrows():
            tx_hash = str(row[hash_col]).strip()
            url = "https://polkadot.api.subscan.io/api/scan/extrinsic"
            
            # Init variables
            est_fee = used_fee = transfer_amount = None
            sender = from_addr = to_addr = None
            status_msg = "Pending"

            try:
                response = requests.post(url, json={"hash": tx_hash}, headers=headers)
                data = response.json()
                
                if response.status_code == 200 and data.get('message') == 'Success':
                    ex_data = data.get('data', {})
                    
                    if ex_data:
                        # --- 1. Get Sender (Top Level) ---
                        sender = ex_data.get('account_id', 'N/A')

                        # --- 2. Get Fees ---
                        est_fee = format_dot(ex_data.get('fee', '0'))
                        used_fee = format_dot(ex_data.get('fee_used', '0'))

                        # --- 3. Get Amount, From, To (Robust Logic) ---
                        
                        # PLAN A: Check 'transfer' object (Simple transfers)
                        transfer_obj = ex_data.get('transfer')
                        
                        if transfer_obj:
                            # Amount
                            raw = transfer_obj.get('amount')
                            transfer_amount = format_dot(raw)
                            # From/To
                            from_addr = transfer_obj.get('from')
                            to_addr = transfer_obj.get('to')
                            
                        # PLAN B: Check 'params' (Complex transfers like transfer_allow_death)
                        else:
                            # Default 'From' to Sender if not found elsewhere
                            from_addr = sender 
                            
                            params = ex_data.get('params', [])
                            found_val = False
                            
                            for p in params:
                                name = p.get('name')
                                value = p.get('value')
                                
                                # Find Amount
                                if name == 'value':
                                    transfer_amount = format_dot(value)
                                    found_val = True
                                
                                # Find Destination (To)
                                if name == 'dest':
                                    to_addr = extract_address(value)

                            if not found_val:
                                transfer_amount = "N/A"
                                if not to_addr: to_addr = "N/A"

                        status_msg = "Success"
                    else:
                        status_msg = "Not Found"
                else:
                    status_msg = f"API Error: {data.get('message')}"

            except Exception as e:
                status_msg = f"Error: {str(e)}"

            results.append({
                "Tx Hash": tx_hash,
                "Sender": sender,
                "From": from_addr,
                "To": to_addr,
                "Transfer Amount": transfer_amount,
                "Estimated Fee": est_fee,
                "Used Fee": used_fee,
                "Status": status_msg
            })

            progress_bar.progress((index + 1) / total_tx)
            status_text.text(f"Processing {index + 1}/{total_tx}...")
            time.sleep(sleep_time)

        status_text.success("Done!")
        res_df = pd.DataFrame(results)
        
        # Reorder columns for better readability
        cols = ["Tx Hash", "Status", "Sender", "From", "To", "Transfer Amount", "Estimated Fee", "Used Fee"]
        # Only use columns that actually exist (in case of error)
        cols = [c for c in cols if c in res_df.columns]
        res_df = res_df[cols]

        st.subheader("Results")
        st.dataframe(res_df)
        
        st.download_button(
            "Download CSV",
            res_df.to_csv(index=False).encode('utf-8'),
            "polkadot_full_data.csv",
            "text/csv"
        )
