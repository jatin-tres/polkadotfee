import streamlit as st
import pandas as pd
import requests
import time

# --- Page Config ---
st.set_page_config(page_title="Polkadot Fee Fetcher", page_icon="🪙")

# --- App Title & Instructions ---
st.title("🪙 Polkadot Subscan Fee Fetcher")
st.markdown("""
This app automates fetching **Estimated Fee** and **Used Fee** from Polkadot Subscan.
1. Upload a CSV file containing Transaction Hashes.
2. Select the column that holds the hash.
3. The app will query Subscan for each transaction and retrieve the fees.
""")

# --- Sidebar: API Configuration ---
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Subscan API Key (Recommended)", type="password", help="Get a free key from https://support.subscan.io/ to avoid rate limits.")

# Rate limit setting: Free tier usually allows ~2 requests/sec, but we go slower to be safe.
sleep_time = st.sidebar.slider("Seconds between requests", min_value=0.1, max_value=2.0, value=0.4)

# --- Main Logic ---
uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.write("Preview of uploaded data:")
    st.dataframe(df.head())

    # Column Selector
    columns = df.columns.tolist()
    hash_col = st.selectbox("Select the column containing Transaction Hash (Tx Hash)", columns)

    if st.button("Fetch Fee Data"):
        # Create placeholders for results
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Streamlit App)"
        }
        if api_key:
            headers["X-API-Key"] = api_key

        total_tx = len(df)
        
        # Iterate through rows
        for index, row in df.iterrows():
            tx_hash = str(row[hash_col]).strip()
            
            # API Endpoint for Polkadot Extrinsics
            url = "https://polkadot.api.subscan.io/api/scan/extrinsic"
            payload = {"hash": tx_hash}

            try:
                response = requests.post(url, json=payload, headers=headers)
                data = response.json()
                
                # Check if request was successful
                if response.status_code == 200 and data.get('message') == 'Success':
                    extrinsic_data = data.get('data', {})
                    
                    if extrinsic_data:
                        # Capture the specific fields requested
                        # Subscan API usually returns 'fee' (Total/Estimated) and 'fee_used' (Used)
                        estimated_fee = extrinsic_data.get('fee', 'N/A')
                        used_fee = extrinsic_data.get('fee_used', 'N/A')
                        
                        # Format them to resemble the UI (adding DOT symbol logic if needed)
                        # The API returns raw numbers usually formatted as strings or floats
                        results.append({
                            "Tx Hash": tx_hash,
                            "Estimated Fee": estimated_fee,
                            "Used Fee": used_fee,
                            "Status": "Found"
                        })
                    else:
                         results.append({
                            "Tx Hash": tx_hash,
                            "Estimated Fee": None,
                            "Used Fee": None,
                            "Status": "Not Found"
                        })
                else:
                    results.append({
                        "Tx Hash": tx_hash,
                        "Estimated Fee": None,
                        "Used Fee": None,
                        "Status": f"Error: {data.get('message', 'Unknown')}"
                    })

            except Exception as e:
                results.append({
                    "Tx Hash": tx_hash,
                    "Estimated Fee": None,
                    "Used Fee": None,
                    "Status": f"Exception: {str(e)}"
                })

            # Update progress
            progress = (index + 1) / total_tx
            progress_bar.progress(progress)
            status_text.text(f"Processing {index + 1}/{total_tx}: {tx_hash[:10]}...")
            
            # Sleep to prevent getting banned by Subscan
            time.sleep(sleep_time)

        # Final Processing
        status_text.text("Processing Complete!")
        results_df = pd.DataFrame(results)
        
        # Merge with original data (optional, or just show new data)
        # We will display the new results dataframe
        st.subheader("Results")
        st.dataframe(results_df)

        # Download Button
        csv = results_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Data as CSV",
            data=csv,
            file_name='polkadot_fees_captured.csv',
            mime='text/csv',
        )
