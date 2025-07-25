# Wallet Risk Scoring Engine for Compound Protocol

This repository contains a Python-based tool to score the risk profile of Ethereum wallets based on their historical transaction activity with the Compound V2 and V3 protocols. The score ranges from 0 (highest risk) to 1000 (lowest risk).

### 1. Data Collection Method

- **Source:** Transaction data was fetched directly from the Ethereum blockchain using the Etherscan API (`account txlist` endpoint).
- **Process:** A Python script (`risk_scorer.py`) iterates through a list of 100 wallet addresses. For each address, the script retrieves its entire transaction history.
- **Filtering:** The raw transaction list was filtered to isolate only those transactions where the `to` address was a known Compound V2 cToken contract (cETH, cUSDC, cDAI) or the main Compound V3 USDC Market contract. This ensures we only analyze relevant protocol interactions.

### 2. Feature Selection & Rationale

Five key features were engineered from the transaction data to create a holistic risk profile. These features focus on historical behavior, stability, and proxies for financial health.

- **`liquidation_proxy` (Proxy for Liquidation Events):** This is the most critical risk indicator. A true on-chain liquidation is when a third party calls the `liquidateBorrow` function on a user's address. This feature counts events where our wallet's address appears in the input data of a `liquidateBorrow` call made to a Compound contract. A non-zero value is a major red flag for high-risk behavior.
- **`health_factor_proxy` (Proxy for Health Factor):** The health factor ((Collateral * Factor) / Borrows) is a live measure of solvency. As this is difficult to calculate from transaction lists alone, this feature is a *simulation* based on other wallet characteristics. It assumes that older, more active wallets are generally better at managing their health factor. A lower value indicates higher risk.
- **`days_since_last_tx` (Recency of Activity):** This measures the number of days since the wallet last interacted with Compound. A wallet that has been inactive for a long time may pose a risk, as its owner may not be actively managing their position against market volatility.
- **`wallet_age_days` (Protocol Experience):** This measures the number of days since the wallet's *first* transaction with Compound. An older, more established wallet is considered less risky than a brand-new wallet, as it has a longer track record.
- **`interaction_count` (Protocol Activity Level):** A simple count of all supply, borrow, and repay events. While not a direct risk indicator on its own, a very low count can suggest a lack of experience or engagement with the protocol, which can be a minor risk factor. Log normalization (`log1p`) was used to reduce the effect of hyper-active whale wallets.

### 3. Scoring Method

The risk score is calculated using a weighted model designed to be clear and justifiable.

- **Normalization:** Each of the five features was normalized to a common scale of 0 to 1 using Min-Max scaling. For every normalized feature, a value of **1 represents the highest risk** and **0 represents the lowest risk**. Features where a higher value is "good" (e.g., `wallet_age_days`) were inverted during normalization (`1 - scaled_value`).

- **Scoring Logic:** A final risk score (0-1) was calculated by multiplying each normalized feature by its assigned weight and summing the results. The weights reflect the importance of each indicator:
    - `liquidation_proxy`: **40%** (Past failure is the strongest predictor of future risk).
    - `health_factor_proxy`: **30%** (Proximity to liquidation is a primary concern).
    - `days_since_last_tx`: **15%** (Unmanaged positions are a significant risk).
    - `wallet_age_days`: **10%** (Experience and stability are good indicators).
    - `interaction_count`: **5%** (Provides context but is the least direct risk measure).

- **Final Scaling:** The resulting 0-1 risk score (where 1 is riskiest) was inverted and scaled to the required **0-1000** range, where a higher score indicates a healthier, safer wallet.
  
  `Final Score = (1 - WeightedRiskScore) * 1000`

This methodology provides a scalable and transparent system for assessing wallet risk based on demonstrable on-chain behavior.
