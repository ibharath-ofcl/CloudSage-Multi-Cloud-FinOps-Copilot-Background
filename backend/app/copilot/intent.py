"""
FinOps Intent Classification and Entity Extraction Engine.
Maps natural language user queries to one of the 15 canonical FinOps intents
and extracts cloud providers, services, resource IDs, time windows, and tags.
"""

from datetime import datetime, timedelta, timezone
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.enums import CloudProvider, CopilotIntent


# Keyword mappings for the 15 FinOps intents
INTENT_KEYWORDS = {
    CopilotIntent.TOTAL_CLOUD_SPEND: [
        r"total\s+(cloud\s+)?(spend|spending|cost|expenditure|bill)",
        r"how\s+much\s+(did\s+we|have\s+we)\s+spen(t|d)",
        r"overall\s+(spend|cost|expenditure)",
        r"total\s+bill",
        r"sum\s+of\s+(all\s+)?costs",
    ],
    CopilotIntent.PROVIDER_COST_COMPARISON: [
        r"compare\s+(cloud\s+)?(spend|cost|spending|providers|expenditure)",
        r"(aws|azure|gcp)\s+vs\s+(aws|azure|gcp)",
        r"between\s+(aws|azure|gcp)\s+and\s+(aws|azure|gcp)",
        r"breakdown\s+by\s+(cloud\s+)?provider",
        r"which\s+cloud(\s+provider)?\s+(is\s+more\s+expensive|costs?\s+(the\s+)?most|costs?\s+more|spends?\s+most)",
        r"provider\s+comparison",
        r"spend\s+across\s+clouds",
    ],
    CopilotIntent.SERVICE_COST_BREAKDOWN: [
        r"service\s+breakdown",
        r"breakdown\s+by\s+service",
        r"(top\s+\d*\s*)?(most\s+expensive|highest\s+cost)\s+(cloud\s+)?services?",
        r"(top|most\s+expensive)\s+services",
        r"how\s+much\s+(did|does)\s+(ec2|s3|rds|ebs|bigquery|compute engine|storage|vm)\s+cost",
        r"(spend|spent|cost)\s+(on|for)\s+(amazon\s+)?(ec2|s3|rds|ebs|bigquery|compute\s+engine|storage|virtual\s+machines|vm)",
        r"cost\s+of\s+(ec2|s3|rds|ebs|bigquery|compute engine|storage|vm)",
        r"service\s+cost",
    ],
    CopilotIntent.RESOURCE_COST_ANALYSIS: [
        r"(cost|spend)\s+of\s+(resource|instance|vm|volume|snapshot|i-[0-9a-z]+)",
        r"(top|most\s+expensive)\s+resources",
        r"resource\s+(level\s+)?(cost|spending)",
        r"which\s+resource(s)?\s+(is|are)\s+costing\s+the\s+most",
        r"which\s+resources?\s+are\s+driving\s+(the\s+)?(highest|most)\s+cost",
        r"resources?\s+driving\s+(the\s+)?highest\s+cost",
    ],
    CopilotIntent.COST_TREND_ANALYSIS: [
        r"cost\s+trend",
        r"spending\s+trend",
        r"daily\s+(spend|cost)",
        r"month\s+over\s+month",
        r"is\s+(our\s+)?spending\s+(increasing|decreasing|going\s+up|going\s+down)",
        r"trajectory",
        r"(cost|spending|budget)\s+forecast",
        r"forecast\s+(cost|spending|budget)",
    ],
    CopilotIntent.COST_ANOMALY_EXPLANATION: [
        r"(cost\s+)?anomal(y|ies)",
        r"spike(s)?",
        r"surge(s)?",
        r"unusual\s+(spend|spending|cost|increase)",
        r"why\s+did\s+(this\s+|our\s+)?(bill|cost|spend|spending)?\s*(increase|spike|jump|surge)",
        r"unexpected\s+(cost|increase)",
        r"investigat(e|ion)",
        r"root\s+cause",
        r"pareto",
        r"what\s+caused\s+(the\s+)?(spike|anomaly|cost\s+increase|surge)",
        r"inv-\d{4}-\d{4,6}",
    ],
    CopilotIntent.WASTE_DETECTION_ANALYSIS: [
        r"waste",
        r"idle\s+(instance|vm|volume|disk|ip|load\s+balancer|resource)",
        r"unattached\s+(disk|volume)",
        r"orphaned\s+snapshot",
        r"unused\s+(ip|resource|disk)",
        r"underutilized",
    ],
    CopilotIntent.OPTIMIZATION_RECOMMENDATIONS: [
        r"recommendation",
        r"how\s+(can|do)\s+we\s+optimize",
        r"suggest(ion)?s?\s+to\s+reduce",
        r"ways\s+to\s+save",
        r"actionable\s+savings",
    ],
    CopilotIntent.SAVINGS_OPPORTUNITY: [
        r"(how\s+much|potential)\s+savings",
        r"money\s+can\s+we\s+save",
        r"total\s+savings\s+opportunity",
        r"annual\s+savings",
        r"monthly\s+savings",
    ],
    CopilotIntent.RESOURCE_UTILIZATION: [
        r"(cpu|memory|disk|network)\s+utilization",
        r"utilization\s+(metric|data|rate)",
        r"low\s+(cpu|utilization)",
        r"average\s+utilization",
        r"inventory\s+and\s+utilization",
        r"utilization",
    ],
    CopilotIntent.OWNER_COST_ANALYSIS: [
        r"(cost|spend)\s+by\s+owner",
        r"who\s+spent\s+the\s+most",
        r"team\s+(spend|cost)",
        r"department\s+(spend|cost)",
        r"owner\s+tag",
    ],
    CopilotIntent.COST_CENTER_ANALYSIS: [
        r"cost\s+center",
        r"spend\s+by\s+cost\s*center",
        r"cost-center",
        r"department\s+code",
    ],
    CopilotIntent.BILLING_DATA_QUALITY: [
        r"data\s+quality",
        r"untagged\s+(resource|billing|spend)",
        r"missing\s+tag",
        r"unallocated\s+(cost|spend)",
        r"billing\s+accuracy",
        r"focus\s+compliance",
    ],
    CopilotIntent.GENERAL_FINOPS_QUESTION: [
        r"what\s+is\s+focus",
        r"what\s+is\s+finops",
        r"unblended\s+vs\s+(blended|effective)",
        r"what\s+is\s+rightsizing",
        r"how\s+does\s+cloudsage\s+work",
        r"explain\s+(spot|reserved\s+instances|savings\s+plans)",
    ],
}


class IntentClassifier:
    """Classifies user queries into the 15 FinOps intents and extracts structured entities."""

    @classmethod
    def classify(cls, query: str) -> CopilotIntent:
        """Determines the most accurate CopilotIntent for the given user question."""
        clean_query = query.lower().strip()

        # Score matching intents
        intent_scores: Dict[CopilotIntent, int] = {}

        for intent, patterns in INTENT_KEYWORDS.items():
            total_matches = 0
            for pattern in patterns:
                matches = re.findall(pattern, clean_query, re.IGNORECASE)
                if matches:
                    total_matches += len(matches)
            if total_matches > 0:
                score = total_matches * 2
                # Prioritize more specific intent categories over generic spend
                if intent in [
                    CopilotIntent.COST_ANOMALY_EXPLANATION,
                    CopilotIntent.WASTE_DETECTION_ANALYSIS,
                    CopilotIntent.OPTIMIZATION_RECOMMENDATIONS,
                    CopilotIntent.SAVINGS_OPPORTUNITY,
                    CopilotIntent.PROVIDER_COST_COMPARISON,
                    CopilotIntent.SERVICE_COST_BREAKDOWN,
                    CopilotIntent.RESOURCE_COST_ANALYSIS,
                    CopilotIntent.RESOURCE_UTILIZATION,
                    CopilotIntent.OWNER_COST_ANALYSIS,
                    CopilotIntent.COST_CENTER_ANALYSIS,
                    CopilotIntent.BILLING_DATA_QUALITY,
                    CopilotIntent.COST_TREND_ANALYSIS,
                ]:
                    score += 3
                intent_scores[intent] = score

        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            return best_intent

        # Heuristics for fallback if keywords matched
        finops_terms = ["finops", "focus", "unblended", "effective", "amortized", "rightsizing", "cloudsage", "showback", "chargeback"]
        if any(term in clean_query for term in finops_terms):
            return CopilotIntent.GENERAL_FINOPS_QUESTION

        if any(term in clean_query for term in ["cost", "spend", "dollar", "$", "budget", "bill", "price", "expenditure"]):
            return CopilotIntent.TOTAL_CLOUD_SPEND

        return CopilotIntent.UNSUPPORTED_OR_AMBIGUOUS_QUERY

    @classmethod
    def extract_entities(cls, query: str) -> Dict[str, Any]:
        """
        Extracts multi-cloud providers, services, dates, resource IDs, and tags.
        """
        clean = query.lower()
        entities: Dict[str, Any] = {
            "providers": [],
            "services": [],
            "resource_ids": [],
            "case_numbers": [],
            "time_window": "last_30_days",
            "start_time": None,
            "end_time": None,
            "tags": {},
            "owner": None,
            "cost_center": None,
        }

        # 1. Cloud Providers
        if "aws" in clean or "amazon" in clean:
            entities["providers"].append(CloudProvider.AWS.value)
        if "azure" in clean or "microsoft" in clean:
            entities["providers"].append(CloudProvider.AZURE.value)
        if "gcp" in clean or "google" in clean:
            entities["providers"].append(CloudProvider.GCP.value)

        # 2. Services
        service_patterns = {
            "Amazon EC2": [r"\bec2\b", r"elastic\s+compute"],
            "Amazon S3": [r"\bs3\b", r"simple\s+storage"],
            "Amazon RDS": [r"\brds\b", r"relational\s+database\s+service"],
            "Amazon EBS": [r"\bebs\b", r"elastic\s+block\s+store"],
            "Virtual Machines": [r"virtual\s+machine", r"\bazure\s+vm\b"],
            "Blob Storage": [r"blob\s+storage"],
            "Compute Engine": [r"compute\s+engine", r"\bgce\b"],
            "Cloud Storage": [r"cloud\s+storage", r"\bgcs\b"],
            "BigQuery": [r"bigquery", r"\bbq\b"],
        }
        for canonical, patterns in service_patterns.items():
            for p in patterns:
                if re.search(p, clean):
                    entities["services"].append(canonical)
                    break

        # 3. Resource IDs & Case Numbers
        res_matches = re.findall(r"\b(i-[a-z0-9]{8,17}|vol-[a-z0-9]{8,17}|snap-[a-z0-9]{8,17})\b", query, re.IGNORECASE)
        if res_matches:
            entities["resource_ids"].extend(res_matches)

        case_matches = re.findall(r"\b(INV-\d{4}-\d{4,6})\b", query, re.IGNORECASE)
        if case_matches:
            entities["case_numbers"].extend(case_matches)

        # 4. Time Windows
        now = datetime.now(timezone.utc)
        if "last 7 days" in clean or "past 7 days" in clean or "past week" in clean:
            entities["time_window"] = "last_7_days"
            entities["start_time"] = now - timedelta(days=7)
            entities["end_time"] = now
        elif "yesterday" in clean:
            entities["time_window"] = "yesterday"
            entities["start_time"] = now - timedelta(days=1)
            entities["end_time"] = now
        elif "last month" in clean:
            entities["time_window"] = "last_month"
            entities["start_time"] = now - timedelta(days=60)
            entities["end_time"] = now - timedelta(days=30)
        else:
            # Default to last 30 days
            entities["time_window"] = "last_30_days"
            entities["start_time"] = now - timedelta(days=30)
            entities["end_time"] = now

        # 5. Owner / Cost Center extraction (preserve case)
        owner_match = re.search(r"owner[:\s]+([a-zA-Z0-9_\-]+)", query, re.IGNORECASE)
        if owner_match:
            entities["owner"] = owner_match.group(1)

        cc_match = re.search(r"cost[\s\-_]*center[:\s]+([a-zA-Z0-9_\-]+)", query, re.IGNORECASE)
        if cc_match:
            entities["cost_center"] = cc_match.group(1)

        return entities
