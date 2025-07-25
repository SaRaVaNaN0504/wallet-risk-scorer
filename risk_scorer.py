import pandas as pd
import numpy as np
import time
import requests
from sklearn.preprocessing import minmax_scale
from datetime import datetime

# --- CONFIGURATION ---

# !!! PASTE YOUR ETHERSCAN API KEY HERE !!!
ETHERSCAN_API_KEY = "VVYYZ9TSFQCVAGFP8NUD6ABNU1HHCH181K" # <--- PASTE YOUR KEY HERE

# Compound Protocol Contract Addresses on Ethereum Mainnet
COMPOUND_V2_CTOKENS = [
    "0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5",  # cETH
    "0x39aa39c021dfbae8fac545936693ac917d5e7563",  # cUSDC
    "0x5d3a536e4d6dbd6114cc1ead35777bab948e3643",  # cDAI
]
COMPOUND_V3_USDC = "0xc3d688b66703497daa19211eedff47f25384cdc3" # USDC Market [1]
ALL_COMPOUND_CONTRACTS = COMPOUND_V2_CTOKENS + [COMPOUND_V3_USDC]

WALLET_ADDRESSES = [
    '0x0039f22efb07a647557c7c5d17854cfd6d489ef3', '0x06b51c6882b27cb05e712185531c1f74996dd988',
    '0x0795732aacc448030ef374374eaae57d2965c16c', '0x0aaa79f1a86bc8136cd0d1ca0d51964f4e3766f9',
    '0x0fe383e5abc200055a7f391f94a5f5d1f844b9ae', '0x104ae61d8d487ad689969a17807ddc338b445416',
    # ... (the rest of the addresses are included in the original paste)
    '0xf7aa5d0752cfcd41b0a5945867d619a80c405e52', '0xf80a8b9cfff0febf49914c269fb8aead4a22f847',
    '0xfe5a05c0f8b24fca15a7306f6a4ebb7dcf2186ac'
]

# --- PART 1: DATA COLLECTION & FEATURE ENGINEERING ---
def get_transactions_from_etherscan(wallet_address):
    """Fetches transaction list for a given wallet address."""
    print(f"Fetching transactions for {wallet_address}...")
    url = (
        f"https://api.etherscan.io/api?module=account&action=txlist"
        f"&address={wallet_address}&startblock=0&endblock=99999999"
        f"&sort=asc&apikey={ETHERSCAN_API_KEY}"
    )
    try:
        response = requests.get(url)
        data = response.json()
        if data["status"] == "1":
            return data["result"]
        else:
            print(f"  > No transactions found or API error for {wallet_address}.")
            return []
    except requests.exceptions.RequestException as e:
        print(f"  > Network error fetching data for {wallet_address}: {e}")
        return []

def create_features_for_wallet(wallet_address, all_transactions):
    """Creates risk features for a single wallet from its transaction list."""
    compound_txs = [tx for tx in all_transactions if tx.get('to', '').lower() in [c.lower() for c in ALL_COMPOUND_CONTRACTS]]

    if not compound_txs:
        return {'wallet_id': wallet_address, 'interaction_count': 0, 'wallet_age_days': 0, 'days_since_last_tx': 9999, 'liquidation_proxy': 0, 'health_factor_proxy': 1.0}

    interaction_count = len(compound_txs)
    first_tx_timestamp = int(compound_txs[0]['timeStamp'])
    wallet_age_days = (datetime.now().timestamp() - first_tx_timestamp) / (60 * 60 * 24)
    last_tx_timestamp = int(compound_txs[-1]['timeStamp'])
    days_since_last_tx = (datetime.now().timestamp() - last_tx_timestamp) / (60 * 60 * 24)
    
    liquidation_proxy = 0
    for tx in all_transactions:
        if tx.get('to', '').lower() in [c.lower() for c in ALL_COMPOUND_CONTRACTS] and tx.get('input', '').startswith('0xf5e3c462') and wallet_address.lower()[2:] in tx.get('input', ''):
            liquidation_proxy += 1

    simulated_health = max(1.1, 1.5 + (wallet_age_days / 365) * 0.5 + (interaction_count / 100) * 0.1)
    
    return {'wallet_id': wallet_address, 'interaction_count': interaction_count, 'wallet_age_days': round(wallet_age_days, 2), 'days_since_last_tx': round(days_since_last_tx, 2), 'liquidation_proxy': liquidation_proxy, 'health_factor_proxy': round(simulated_health, 2)}

# --- Main Data Processing Loop ---
all_features = []
print("Starting data collection and feature engineering...")
USE_DUMMY_DATA = (ETHERSCAN_API_KEY == "VVYYZ9TSFQCVAGFP8NUD6ABNU1HHCH181K")

if USE_DUMMY_DATA:
    print("\nWARNING: No Etherscan API key found. Using dummy data for demonstration.")
    for wallet in WALLET_ADDRESSES:
        all_features.append({'wallet_id': wallet, 'interaction_count': np.random.randint(5, 500), 'wallet_age_days': np.random.uniform(30, 1000), 'days_since_last_tx': np.random.uniform(1, 365), 'liquidation_proxy': np.random.choice([0, 0, 0, 1]), 'health_factor_proxy': np.random.uniform(1.1, 5.0)})
else:
    for wallet in WALLET_ADDRESSES:
        time.sleep(0.25) # Rate limit
        tx_data = get_transactions_from_etherscan(wallet)
        features = create_features_for_wallet(wallet, tx_data) if tx_data else {'wallet_id': wallet, 'interaction_count': 0, 'wallet_age_days': 0, 'days_since_last_tx': 9999, 'liquidation_proxy': 0, 'health_factor_proxy': 1.0}
        all_features.append(features)

df_features = pd.DataFrame(all_features)
print("\nFeature engineering complete.")

# --- PART 2: RISK SCORING MODEL ---
print("\nBuilding risk scoring model...")
weights = {'liquidation': 0.40, 'health_factor': 0.30, 'recency': 0.15, 'age': 0.10, 'activity': 0.05}

df_features['norm_liquidation'] = minmax_scale(df_features['liquidation_proxy'])
df_features['norm_health_factor'] = 1 - minmax_scale(df_features['health_factor_proxy'])
df_features['norm_recency'] = minmax_scale(df_features['days_since_last_tx'])
df_features['norm_age'] = 1 - minmax_scale(df_features['wallet_age_days'])
df_features['norm_activity'] = 1 - minmax_scale(np.log1p(df_features['interaction_count']))

df_features['risk_score'] = (weights['liquidation'] * df_features['norm_liquidation'] + weights['health_factor'] * df_features['norm_health_factor'] + weights['recency'] * df_features['norm_recency'] + weights['age'] * df_features['norm_age'] + weights['activity'] * df_features['norm_activity'])
df_features['score'] = (1 - df_features['risk_score']) * 1000
df_features['score'] = df_features['score'].astype(int)
print("\nScoring complete.")

# --- PART 3: CREATE DELIVERABLES ---
final_submission = df_features[['wallet_id', 'score']]
final_submission.to_csv('wallet_scores.csv', index=False)
print("\n✅ Successfully created `wallet_scores.csv`. Final result sample:")
print(final_submission.head())