import streamlit as st
import pandas as pd
import requests
import time

# --- Page Config ---
st.set_page_config(page_title="Polkadot Fee & Transfer Fetcher", page_icon="🪙", layout="wide")

# --- App Title ---
st.title("🪙 Polkadot Subscan Data Fetcher (Fixed)")
st.markdown("""
**Instructions:**
1. Upload your CSV.
2. Select the Hash column.
3. Click "Fetch Data".
""")

# --- Sidebar ---
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Subscan API Key (Optional)", type="password")
sleep_time = st.sidebar.slider("Seconds between requests", 0.1, 2.0, 0.4)

# --- Helper Function to Format DOT ---
def format_dot(raw_amount, decimals=10):
    try:
        # Convert raw string/int to float and divide by 10^10
        val = float(raw_amount) / (10 ** decimals)
        return f"{val:,.4f} DOT"
    except:
        return None

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
            status_msg = "Pending"

            try:
                response = requests.post(url, json={"hash": tx_hash}, headers=headers)
                data = response.json()
                
                if response.status_code == 200 and data.get('message') == 'Success':
                    ex_data = data.get('data', {})
                    
                    if ex_data:
                        # 1. Get Fees (Handle huge integers by treating as float first if needed)
                        # Subscan fees are usually raw, so we assume 10 decimals for fees too if you want them formatted
                        # But your request showed raw integers for fees, so we keep them raw or basic formatted.
                        est_fee = ex_data.get('fee', '0')
                        used_fee = ex_data.get('fee_used', '0')

                        # 2. Get Transfer Amount (The Robust Logic)
                        
                        # PLAN A: Check for direct 'transfer' object
                        transfer_obj = ex_data.get('transfer')
                        
                        if transfer_obj:
                            raw = transfer_obj.get('amount')
                            transfer_amount = format_dot(raw)
                            
                        # PLAN B: Check 'params' (Common for transfer_allow_death)
                        else:
                            params = ex_data.get('params', [])
                            found_param = False
                            for p in params:
                                # Look for a parameter named 'value' (standard for balance transfers)
                                if p.get('name') == 'value':
                                    transfer_amount = format_dot(p.get('value'))
                                    found_param = True
                                    break
                            
                            if not found_param:
                                transfer_amount = "N/A (Complex Tx)"
                        
                        status_msg = "Success"
                    else:
                        status_msg = "Not Found"
                else:
                    status_msg = f"API Error: {data.get('message')}"

            except Exception as e:
                status_msg = f"Error: {str(e)}"

            results.append({
                "Tx Hash": tx_hash,
                "Estimated Fee": est_fee,
                "Used Fee": used_fee,
                "Transfer Amount": transfer_amount,
                "Status": status_msg
            })

            progress_bar.progress((index + 1) / total_tx)
            status_text.text(f"Processing {index + 1}/{total_tx}...")
            time.sleep(sleep_time)

        status_text.success("Done!")
        res_df = pd.DataFrame(results)
        st.dataframe(res_df)
        
        st.download_button(
            "Download CSV",
            res_df.to_csv(index=False).encode('utf-8'),
            "polkadot_data_fixed.csv",
            "text/csv"
        )
