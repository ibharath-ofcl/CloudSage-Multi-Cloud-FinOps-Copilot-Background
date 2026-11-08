# Multi-Format Remediation Playbook Generator

**Project:** CloudSage – Multi-Cloud FinOps Copilot  
**Stage:** Stage 11 – Enterprise Recommendation & Waste Management Workspace  
**Status:** Implemented & Verified  

---

## 1. Executive Overview

CloudSage is an **advisory-only** FinOps platform. To maintain strict enterprise security and compliance, CloudSage **never directly modifies, mutates, or deletes cloud infrastructure** via live provider APIs.

Instead, Stage 11 delivers the **Multi-Format Remediation Playbook Generator**. This system translates abstract recommendations (e.g., "rightsize instance to t3.medium" or "delete unattached EBS volume") into tangible, production-grade infrastructure-as-code (IaC) definitions and CLI execution scripts.

Engineers can review, validate, and incorporate these playbooks into their existing GitOps, Terraform, or CI/CD pipelines with complete confidence.

---

## 2. Supported Formats & Capabilities

The generator supports **7 standardized enterprise formats**:

| Format Key | Language / Syntax | File Extension | Use Case |
|---|---|---|---|
| `terraform` | HashiCorp Configuration Language (HCL) | `.tf` | GitOps workflows, Terraform Cloud, OpenTofu pipelines. |
| `cloudformation` | AWS CloudFormation YAML | `.yaml` | Native AWS stack management and template updates. |
| `aws_cli` | Bash Shell Script with AWS CLI | `.sh` | Operator shell execution for AWS environments. |
| `azure_cli` | Bash Shell Script with Azure CLI (`az`) | `.sh` | Operator shell execution for Azure subscriptions. |
| `azure_bicep` | Azure Bicep DSL | `.bicep` | Modern Infrastructure-as-Code for Microsoft Azure. |
| `gcp_cli` | Bash Shell Script with Google Cloud CLI (`gcloud`) | `.sh` | Operator shell execution for Google Cloud Platform. |
| `markdown` | Human-Readable Markdown | `.md` | Architecture documentation, Jira tickets, peer review notes. |

---

## 3. Mandatory Safety & Security Guardrails

Every generated playbook strictly adheres to enterprise safety rules:

1. **Prominent Advisory Warning Header:**
   All scripts and templates begin with a standardized advisory warning emphasizing that the script must be reviewed before execution in production.
2. **Input Identifier Sanitization (`sanitize_identifier`):**
   Resource IDs, ARNs, and parameters are stripped of shell metacharacters (`;`, `&`, `|`, `$`, `` ` ``, `<`, `>`, newline) to prevent command injection vulnerabilities.
3. **Pre-Flight Safety Checks:**
   CLI scripts verify CLI installation and credentials before running (`aws --version`, `az account show`, `gcloud auth list`).
4. **Credential Isolation:**
   Playbooks **never** hardcode API keys, access secrets, or tokens. Scripts rely exclusively on ambient environment credentials (IAM roles, AWS SSO, Managed Identities, Workload Identity).
5. **Rollback & Recovery Plans:**
   Every generated playbook contains an explicit rollback section explaining how to restore or re-provision the modified asset if issues arise.

---

## 4. Code Generation Engine Details

Located in `backend/app/recommendations/playbooks.py`, the `RemediationPlaybookGenerator` evaluates:
- **Action Type:** `RIGHTSIZE`, `TERMINATE`, `STORAGE_TIER`, `CLEANUP_SNAPSHOT`, `DELETE_ORPHAN`.
- **Target Provider:** `AWS`, `AZURE`, `GCP`.
- **Resource Context:** Resource ID, region, account ID, service type, and recommended target SKU.
- **Financial Context:** Estimated monthly savings.

### Example: Terraform Playbook Generation (`.tf`)

```hcl
# ==============================================================================
# CLOUDSAGE ADVISORY REMEDIATION PLAYBOOK (TERRAFORM)
# ==============================================================================
# Provider: AWS
# Action: RIGHTSIZE
# Resource: i-0abcdef1234567890
# Estimated Monthly Savings: $75.0000 USD
#
# IMPORTANT: CloudSage is an advisory-only platform. Review and test this
# Terraform configuration in a staging environment before applying.
# ==============================================================================

# Update your existing Terraform resource block:
# resource "aws_instance" "app_server" {
#   ...
#   instance_type = "t3.medium" # Updated by CloudSage recommendation
#   ...
# }

# ------------------------------------------------------------------------------
# ROLLBACK PLAN:
# If performance degrades, revert the instance_type argument to the previous type
# and run 'terraform apply' to restore original capacity.
# ------------------------------------------------------------------------------
```

### Example: AWS CLI Script Generation (`.sh`)

```bash
#!/usr/bin/env bash
# ==============================================================================
# CLOUDSAGE ADVISORY REMEDIATION SCRIPT (AWS CLI)
# Action: TERMINATE | Resource: i-0abcdef1234567890
# Estimated Monthly Savings: $150.0000 USD
# ==============================================================================
set -euo pipefail

# 1. Pre-flight verification
if ! command -v aws &> /dev/null; then
    echo "ERROR: aws CLI is not installed or not in PATH."
    exit 1
fi

RESOURCE_ID="i-0abcdef1234567890"

echo "Evaluating target resource: ${RESOURCE_ID}..."
aws ec2 describe-instances --instance-ids "${RESOURCE_ID}" --query "Reservations[].Instances[].[InstanceId,State.Name]" --output table

read -p "Are you sure you want to proceed with terminating this resource? (yes/no): " CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
    echo "Aborted by operator."
    exit 0
fi

# 2. Execution
echo "Terminating ${RESOURCE_ID}..."
aws ec2 terminate-instances --instance-ids "${RESOURCE_ID}"

echo "Remediation initiated successfully."
```

---

## 5. API & UI Consumption

- **Preview Endpoint:** `GET /api/v1/recommendations/{id}/playbook?format=terraform`
- **Download Endpoint:** `GET /api/v1/recommendations/{id}/playbook/download?format=aws_cli`
- **UI Viewer (`RemediationPlaybookPanel.tsx`):**
  - Tabbed format switcher.
  - One-click copy to clipboard with toast notification.
  - Direct file download button (`download="remediation-i-0abc.tf"`).
  - Prominent safety banner reminding operators of advisory-only boundaries.
