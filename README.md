# NUS Fintech Summit - Tokenised Crowd-sourced Scholarships

A blockchain-based platform for semester-based crowd-sourced university financing using the XRP Ledger (XRPL). 
This system enables crowdfunded scholarships where investors receive tokens representing income-sharing agreements with students, who repay through post-graduation income distributions.

## Concept

Traditional student loans create debt burdens. This system creates an alternative where:
- **Students** receive funding for their education without taking on debt
- **Investors** support education with the potential to bare returns depending on graduate success
- **Transparency** is built-in through XRPL's blockchain
- **Flexibility** allows semester-by-semester funding adjustments

### How It Works

1. **Token Issuance**: At the start of each semester, tokens are created representing a percentage of the student's future income
2. **Crowdfunding**: Investors purchase tokens on the decentralized exchange
3. **Education Funding**: Proceeds fund the student's semester expenses
4. **Post-Graduation**: Student shares a percentage of their income with token holders
5. **Dividend Distribution**: Income is automatically distributed proportionally to all token holders
6. **Free Market-Based Pricing**: Token prices reflect student performance and market confidence

## Features

- **Income-Share Agreements (ISAs)**: Students commit a small percentage (0.01% per token) of future income
- **Semester-Based Funding**: New tokens minted each semester based on market token prices
- **Market-Driven Valuation**: Token prices reflect investor confidence in student success
- **Automated Repayment**: Smart distribution of income to all token holders
- **Decentralized Trading**: Open market for scholarship tokens
- **Dynamic Supply**: Token issuance adjusts based on market capitalization

## Installation
Install dependencies: 
```bash
pip install -r requirements.txt
```
Run the `main.py` file to produce the local Gradio demo:
```bash
python main.py
```

## System Architecture

### Participants

| Role | Description | Blockchain Identity |
|------|-------------|-------------------|
| **Student** | Token issuer, future income provider | Issuer Wallet |
| **Initial Investor** | Primary market scholarship provider | Seller Wallet(s) |
| **Market Investors** | Secondary market participants | Buyer Wallet(s) |

### Token Economics

```
Token Symbol: PYT (customizable per student)
Initial Supply: 125 tokens (Semester 1)
Income Share: 0.01% of annual income per token
Example: 125 tokens = 1.25% of annual income
```

## Project Structure

### 1. First Funded Semester: Initial Token Issuance
**Purpose**: Bootstrap the scholarship with first semester funding

```python
# Contract Pricing Formula
CONTRACT_PRICE_IN_USD = SEMESTER_FEE_IN_USD / 125      # Initial token issue count = 125
CONTRACT_PRICE_IN_XRP = CONTRACT_PRICE_IN_USD / XRP_PRICE_IN_USD

# Assuming:
SEMESTER_FEE_IN_USD = "2150"       # Approx. 2750 SGD
XRP_PRICE_IN_USD = "2.15"        # Approx. 2.80 SGD
TOKEN_SUPPLY = "125"            # Represents 1.25% future income share
# Then:
PRICE_IN_XRP = "8"              # Initial token price
```

**Process**:
- Issuer issues tokens for student
- Initial investor establishes trust line
- 125 tokens issued representing income-sharing agreement
- Tokens sold to fund first semester

### 2. Secondary Market Trading
**Purpose**: Enable scholarship token trading and income speculation

Investors can:
- Buy tokens betting on student success
- Sell tokens to exit their position
- Price tokens based on expected graduate income

This creates a **transparent market** for education financing.

### 3. Performance-Based Pricing
**Purpose**: Track token valuation based on academic progress

Prices is driven by:
- Student performance
- Investor confidence
- Student incentive to increase prices and decrease contracts issuable

**Key Indicator**: If tokens trade at higher prices, it signals strong investor confidence in the student's earning potential and benefits the student by allowing the issuing lesser contracts for future semesters.

### 4. Dynamic Supply Management
**Purpose**: Fund subsequent semesters based on market cap

```python
ISSUED_TOKENS = floor(SEMESTER_FEE_IN_USD / TOKEN_PRICE_IN_USD)
```

**Logic**:
- **Strong Performance** → Higher token price → Fewer new tokens needed
- **Needs Support** → Lower token price → More tokens issued
- **Result**: Market-based dilution reflecting student trajectory

### 5. Post-Graduation Income Distribution
**Purpose**: Fulfill income-sharing agreement with payouts

```python
Annual Income → Convert to XRP → Distribute to token holders
Each token holder receives: (TOKENS_HELD * INCOME * 0.0001)
```

**Example Calculation**:
```
Graduate Income: $50,000 USD/year
Total Token Supply: 500 tokens (4 semesters)
Income Share: 0.01% per token = 5% total
Annual Payout Pool: $2,500
XRP Conversion: $2,500 / $2.50 = 1,000 XRP
Token Holder (100 tokens): 1,000 XRP * (100/500) = 200 XRP
```

## Benefits Over Traditional Loans

| Traditional Loans | Tokenized ISA |
|-------------------|---------------|
| Fixed debt regardless of income | Income-proportional payments |
| Interest compounds | No interest |
| Credit score required | Performance-based funding |
| No incentivisaton | Performance-based incentivisaton |
| No investor participation | Community-supported education |
| Rigid repayment | Flexible market-based system |
| Opaque terms | Transparent blockchain records |

## Ethical Considerations

### Protections Built-In

- **Small Income Cap**: 0.01% per token limits total obligation and exploiting payouts
- **Market Discipline**: Over-issuance decreases token value
- **Voluntary Participation**: Students control issuance over all semesters
- **Transparent Terms**: All agreements on-chain

## Technical Implementation

### Network Configuration

```python
# Testnet for development
client = JsonRpcClient("https://s.altnet.rippletest.net:51234/")

# Mainnet for production (requires real XRP)
# client = JsonRpcClient("https://xrplcluster.com/")
```

## Resources

- [XRPL Documentation](https://xrpl.org/)