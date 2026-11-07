# Advanced Currency Normalization & Historical FX Engine

## 1. Executive Summary

Global enterprises consume cloud resources across dozens of sovereign regions and currencies (EUR, GBP, INR, JPY, CAD, AUD, etc.). To provide unified executive dashboards, cross-cloud anomaly detection, and accurate FinOps savings calculations, CloudSage normalizes all expenditures into **US Dollars (USD)** while strictly preserving original financial figures.

- **Module**: `backend/app/normalization/currency/`
- **Database Model**: `ExchangeRate` (`exchange_rates` table)
- **Service**: `CurrencyService`
- **Cache**: `ExchangeRateCache`
- **Precision Guarantee**: 100% `Decimal` calculations; zero floating point types.

---

## 2. Multi-Currency Support

CloudSage provides out-of-the-box support for 15+ major global currencies:

| Currency Code | Currency Name | Reference Rate (1 Unit = X USD) | Region / Cloud Support |
| :---: | :--- | :---: | :--- |
| `USD` | US Dollar | $1.000000$ | Standard Global Base Currency |
| `EUR` | Euro | $1.085000$ | AWS eu-central-1, Azure westeurope, GCP europe-west3 |
| `GBP` | British Pound | $1.295000$ | AWS eu-west-2, Azure uksouth, GCP europe-west2 |
| `INR` | Indian Rupee | $0.011800$ | AWS ap-south-1, Azure centralindia, GCP asia-south1 |
| `JPY` | Japanese Yen | $0.006700$ | AWS ap-northeast-1, Azure japaneast, GCP asia-northeast1 |
| `CAD` | Canadian Dollar | $0.725000$ | AWS ca-central-1, Azure canadacentral, GCP northamerica-northeast1 |
| `AUD` | Australian Dollar | $0.660000$ | AWS ap-southeast-2, Azure australiaeast, GCP australia-southeast1 |
| `CHF` | Swiss Franc | $1.125000$ | AWS eu-central-2, Azure switzerlandnorth, GCP europe-west6 |
| `BRL` | Brazilian Real | $0.174000$ | AWS sa-east-1, Azure brazilsouth, GCP southamerica-east1 |
| `SGD` | Singapore Dollar | $0.748000$ | AWS ap-southeast-1, Azure southeastasia, GCP asia-southeast1 |
| `SEK` | Swedish Krona | $0.093000$ | AWS eu-north-1, Azure swedencentral |
| `NZD` | New Zealand Dollar | $0.595000$ | Azure newzealandnorth |
| `ZAR` | South African Rand | $0.054000$ | AWS af-south-1, Azure southafricanorth, GCP africa-south1 |
| `AED` | UAE Dirham | $0.272300$ | AWS me-central-1, Azure uaenorth, GCP me-central1 |
| `SAR` | Saudi Riyal | $0.266500$ | GCP me-central2 |

---

## 3. Architecture & Resolution Sequence

When converting a billing line item, `CurrencyService.convert_to_usd` resolves exchange rates through a 3-tier fallback architecture:

```
                        ┌──────────────────────────────────────────────┐
                        │        CurrencyService.convert_to_usd        │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │      Tier 1: In-Memory Rate Cache            │
                        │      (Key: (Currency, EffectiveDate))        │
                        └──────────────┬───────────────────────────────┘
                                       │ (Cache Miss)
                                       ▼
                        ┌──────────────────────────────────────────────┐
                        │      Tier 2: PostgreSQL exchange_rates       │
                        │      1. Exact Date Match                     │
                        │      2. Preceding Business Day Rollback      │
                        └──────────────┬───────────────────────────────┘
                                       │ (DB Miss or Offline)
                                       ▼
                        ┌──────────────────────────────────────────────┐
                        │      Tier 3: Static Reference Provider       │
                        │      (Deterministic Fallback Baseline)       │
                        └──────────────────────────────────────────────┘
```

### Business Day Rollback Policy (Weekends & Market Holidays)
Foreign exchange markets do not publish spot rates on Saturdays, Sundays, and major bank holidays.
- If a billing line item occurs on a Sunday, the engine automatically rolls back up to 7 business days to find the latest verified closing rate (typically the preceding Friday).
- The returned `RateLookupResult` marks `is_interpolated = True` and appends `_INTERPOLATED` to the source descriptor.
- CloudSage **never** silently substitutes today's live rate for historical billing dates.

---

## 4. Financial Precision & Rounding Rules

1. **Zero Float Rule**: Floating-point representations (`float`, `double`) are strictly prohibited in financial paths to prevent binary rounding anomalies ($0.1 + 0.2 \ne 0.3$).
2. **Formula**:
   $$\text{Converted USD} = \text{ROUND}\left( \text{Original Cost} \times \text{Rate to USD},\ 4,\ \text{ROUND\_HALF\_UP} \right)$$
3. **Preservation**: The original invoiced cost and original currency are persisted in the record's metadata (`original_cost`, `original_currency`, `_exchange_rate_source`, `_exchange_rate_date`, `_exchange_rate_used`).

---

## 5. REST API Usage Example

Query current exchange rates:
```bash
curl "http://localhost:8000/api/v1/normalization/currency-rates"
```

Response:
```json
{
  "base_currency": "USD",
  "rates_to_usd": {
    "USD": 1.0,
    "EUR": 1.085,
    "GBP": 1.295,
    "INR": 0.0118,
    "JPY": 0.0067,
    "CAD": 0.725,
    "AUD": 0.66
  },
  "total_currencies": 15,
  "source": "ECB_AND_STATIC_FALLBACK",
  "timestamp": "2026-11-07T13:00:00Z"
}
```
