import streamlit as st
import pandas as pd
import requests
import time

# --- Page Config ---
st.set_page_config(page_title="Polkadot Fee & Transfer Fetcher", page_icon="🪙", layout="wide")

# --- App Title & Instructions ---
st.title("🪙 Polkadot Subscan Data Fetcher")
st.markdown("""
This app automates fetching details from Polkadot Subscan.
It now captures:
1. **Estimated Fee**
2. **Used Fee**
3. **Asset Transfer Amount** (The quantity sent, e.g., 12,467 DOT)

**Instructions:**
1. Upload a CSV file containing Transaction Hashes.
2. Select the column that holds the hash.
3. Click "Fetch Data".
""")

# --- Sidebar: API Configuration ---
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Subscan API Key (Optional)", type="password", help="Get a free key from https://support.subscan.io/ to avoid rate limits.")
sleep_time = st.sidebar.slider("Seconds between requests", min_value=0.1, max_value=2.0, value=0.4)

# --- Main Logic ---
uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.subheader("Preview of Uploaded Data")
    st.dataframe(df.head())

    # Column Selector
    columns = df.columns.tolist()
    hash_col = st.selectbox("Select the column containing Transaction Hash (Tx Hash)", columns)

    if st.button("Fetch Data"):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # API Headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Streamlit App)"
        }
        if api_key:
            headers["X-API-Key"] = api_key

        total_tx = len(df)
        
        for index, row in df.iterrows():
            tx_hash = str(row[hash_col]).strip()
            
            # API Endpoint
            url = "https://polkadot.api.subscan.io/api/scan/extrinsic"
            payload = {"hash": tx_hash}

            # Default values
            estimated_fee = None
            used_fee = None
            transfer_amount = None
            status = "Pending"

            try:
                response = requests.post(url, json=payload, headers=headers)
                data = response.json()
                
                if response.status_code == 200 and data.get('message') == 'Success':
                    extrinsic_data = data.get('data', {})
                    
                    if extrinsic_data:
                        # 1. Get Fees
                        estimated_fee = extrinsic_data.get('fee', '0')
                        used_fee = extrinsic_data.get('fee_used', '0')

                        # 2. Get Transfer Amount
                        # Subscan puts simple transfers in a 'transfer' object
                        transfer_info = extrinsic_data.get('transfer')
                        
                        if transfer_info:
                            raw_amount = float(transfer_info.get('amount', 0))
                            decimals = int(transfer_info.get('decimals', 10)) # Default to 10 if missing
                            symbol = transfer_info.get('symbol', 'DOT')
                            
                            # Convert raw units to readable DOT (e.g. 10000000000 -> 1.0)
                            readable_amount = raw_amount / (10 ** decimals)
                            transfer_amount = f"{readable_amount:,.4f} {symbol}" # Format with commas
                        else:
                            # If no direct transfer object, it might be a different type of transaction
                            transfer_amount = "N/A (Not a simple transfer)"

                        status = "Success"
                    else:
                        status = "Not Found"
                else:
                    status = f"API Error: {data.get('message', 'Unknown')}"

            except Exception as e:
                status = f"Error: {str(e)}"

            # Append to results
            results.append({
                "Tx Hash": tx_hash,
                "Estimated Fee": estimated_fee,
                "Used Fee": used_fee,
                "Transfer Amount": transfer_amount,
                "Status": status
            })

            # Update Progress
            progress = (index + 1) / total_tx
            progress_bar.progress(progress)
            status_text.text(f"Processing {index + 1}/{total_tx}...")
            
            # Rate limit sleep
            time.sleep(sleep_time)

        # Final Output
        status_text.text("Processing Complete!")
        results_df = pd.DataFrame(results)
        
        st.subheader("Results")
        st.dataframe(results_df)

        # CSV Download
        csv = results_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name='polkadot_data_captured.csv',
            mime='text/csv',
        )
