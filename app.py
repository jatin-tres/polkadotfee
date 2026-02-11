import streamlit as st
import pandas as pd
import requests
import time

# --- Page Config ---
st.set_page_config(page_title="Polkadot Fee & Transfer Fetcher", page_icon="🪙", layout="wide")

# --- App Title ---
st.title("🪙 Polkadot Subscan Data Fetcher (Exact Amounts)")
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

# --- Helper Function to Format DOT (Fixed for Full Precision) ---
def format_dot(raw_amount, decimals=10):
    try:
        # Convert raw string/int to float and divide by 10^10
        val = float(raw_amount) / (10 ** decimals)
        
        # Format with 10 decimal places (standard for DOT) to capture everything
        # Then strip trailing zeros for cleaner look if it's a whole number
        formatted_val = f"{val:,.10f}".rstrip('0').rstrip('.')
        
        return f"{formatted_val} DOT"
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
            est_fee = None
            used_fee = None
            transfer_amount = None
            status_msg = "Pending"

            try:
                response = requests.post(url, json={"hash": tx_hash}, headers=headers)
                data = response.json()
                
                if response.status_code == 200 and data.get('message') == 'Success':
                    ex_data = data.get('data', {})
                    
                    if ex_data:
                        # 1. Get Fees
                        # Capture raw fee first, then format same as amount
                        raw_est_fee = ex_data.get('fee', '0')
                        raw_used_fee = ex_data.get('fee_used', '0')
                        
                        est_fee = format_dot(raw_est_fee)
                        used_fee = format_dot(raw_used_fee)

                        # 2. Get Transfer Amount (Robust Logic)
                        
                        # Check params (most reliable for transfer_allow_death)
                        params = ex_data.get('params', [])
                        found_param = False
                        
                        # First try finding 'value' in params
                        for p in params:
                            if p.get('name') == 'value':
                                transfer_amount = format_dot(p.get('value'))
                                found_param = True
                                break
                        
                        # If not found in params, try the 'transfer' object (Plan B)
                        if not found_param:
                            transfer_obj = ex_data.get('transfer')
                            if transfer_obj:
                                raw = transfer_obj.get('amount')
                                transfer_amount = format_dot(raw)
                            else:
                                transfer_amount = "N/A"
                        
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
        st.subheader("Results")
        st.dataframe(res_df)
        
        st.download_button(
            "Download CSV",
            res_df.to_csv(index=False).encode('utf-8'),
            "polkadot_exact_amounts.csv",
            "text/csv"
        )
