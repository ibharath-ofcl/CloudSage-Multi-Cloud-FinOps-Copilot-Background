# CloudSage Cost Anomaly Detection Architecture

## 1. Executive Summary

The **CloudSage Cost Anomaly Detection Engine** provides enterprise-grade, continuous statistical and time-series monitoring across multi-cloud infrastructure (Amazon Web Services, Microsoft Azure, Google Cloud Platform).

Designed to address fragmented billing visibility and sudden unbudgeted cloud expenditures, the engine continuously tracks daily expenditure distributions, computes robust non-parametric baselines, isolates unexpected spikes, identifies persistent structural shifts, attributes root causes to specific cloud resources, and projects financial impacts.

```
+---------------------------------------------------------------------------------------------------+
|                                  CLOUDSAGE ADVISORY-ONLY NOTICE                                   |
| CloudSage operates strictly in an advisory, non-intrusive capacity. It NEVER automatically stops, |
| resizes, deletes, terminates, or alters production cloud infrastructure. All outputs are FinOps   |
| advisory findings and root-cause explanations.                                                    |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. End-to-End System Architecture

```mermaid
flowchart TD
    subgraph DataSources["1. Normalized Ingestion & Inventory"]
        BR["Billing Records\n(FOCUS 1.0 Normalized)\nNumeric(18,4)"]
        CR["Cloud Resources\n(Stage 5 Inventory)\nOwner, Env, Tags"]
    end

    subgraph Aggregation["2. Time-Series Aggregation Service"]
        AG["Contiguous Daily Aggregator\n(Zero-filling, Credit Isolation)"]
        D1["Provider Series"]
        D2["Account Series"]
        D3["Service Series"]
        D4["Resource Series"]
        AG --> D1 & D2 & D3 & D4
    end

    subgraph BaselineEngine["3. Statistical Baseline Engine"]
        BE["Multi-Window Rolling Baselines\n(7, 14, 30, 60, 90 Days)"]
        STATS["Parametric & Non-Parametric Stats\n(Mean, StdDev, Median, MAD, Quartiles, IQR)"]
        BE --> STATS
    end

    subgraph Detectors["4. Pluggable Detector Registry"]
        DET1["Statistical Ensemble Detector\n(Z-Score, Modified Z-Score, IQR)"]
        DET2["Change Point Detector\n(CUSUM & Dual-Window t-test)"]
        DET3["Service Cost Spike Detector"]
        DET4["Resource Cost Spike Detector"]
        DET5["Provider / Account Spike Detector"]
        DET6["Usage vs Rate Divergence Detector"]
        DET7["New Spend Pattern Detector"]
    end

    subgraph AttributionEngine["5. Root-Cause Attribution & Impact"]
        ATTR["Attribution Engine\n(Ranked Resource/SKU Drivers)"]
        CORR["Inventory Correlation\n(Owner, Environment, Project)"]
        IMP["Financial Impact Calculator\n(Excess, Monthly/Annual Projections)"]
        ATTR --> CORR --> IMP
    end

    subgraph LifecycleEngine["6. Anomaly Lifecycle & Storage"]
        DEDUP["Idempotent Deduplication\n(In-Place Updates & Reopening)"]
        AUTORES["Auto-Resolution Guard\n(Cost Returns <= Baseline Fence)"]
        POSTGRES[("PostgreSQL Database\n- cost_anomalies\n- cost_baselines\n- anomaly_detection_runs")]
        DEDUP --> POSTGRES
        AUTORES --> POSTGRES
    end

    subgraph API["7. REST API & Celery"]
        ROUTER["FastAPI Router\n(14 REST Endpoints)"]
        CELERY["Celery Background Worker\n(Scheduled Scans)"]
    end

    BR & CR --> AG
    D1 & D2 & D3 & D4 --> BE
    BE --> DET1 & DET2 & DET3 & DET4 & DET5 & DET6 & DET7
    DET1 & DET2 & DET3 & DET4 & DET5 & DET6 & DET7 --> ATTR
    IMP --> DEDUP & AUTORES
    POSTGRES --> ROUTER
    CELERY --> AG
```

---

## 3. Core Architectural Principles

1. **Zero-Float Financial Guarantee**:
   All statistical aggregations, baselines, standard deviations, deviations, and projected impacts are evaluated strictly using Python `Decimal` and PostgreSQL `Numeric(18, 4)`. No binary floating-point representation (`float`) is permitted in financial logic.

2. **Credit & Refund Isolation**:
   Negative billing adjustments, promotional credits, and enterprise discounts are isolated from positive expenditure time series. Incorporating negative credits into baseline standard deviation calculations artificially inflates variance, which can suppress real cost spikes or trigger false alarms when legitimate promotional credits expire.

3. **Pluggable & Extensible Detectors**:
   All detection heuristics conform to the `BaseAnomalyDetector` abstract interface and are managed through the centralized `AnomalyDetectorRegistry`. This decoupled design allows adding domain-specific anomaly detection models without modifying the core aggregation or persistence layers.

4. **Multi-Faceted Attribution & Inventory Correlation**:
   Cost anomalies do not exist in isolation. Every detected deviation is immediately correlated with underlying FOCUS 1.0 billing records and Stage 5 `CloudResource` inventory items to identify the exact runaway resource, SKU, owner, and environment.

5. **Auditable Lifecycle Management**:
   The engine tracks every anomaly through states: `DETECTED`, `INVESTIGATING`, `ACKNOWLEDGED`, `RESOLVED`, `DISMISSED`, and `REOPENED`. Dismissals and resolutions require mandatory justifications and user attribution, ensuring auditable FinOps governance.

