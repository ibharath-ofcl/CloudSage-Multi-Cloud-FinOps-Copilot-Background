"""
CloudSage Remediation Guidance Generator.
Produces vendor-specific CLI commands, Terraform configuration snippets, rollback steps,
and mandatory non-destructive advisory notices for AWS, Azure, and GCP.
"""

from typing import Any, Dict, List, Optional
from backend.app.core.enums import CloudProvider, RecommendationAction

ADVISORY_DISCLAIMER = (
    "ADVISORY NOTICE: CloudSage operates strictly as a read-only advisory copilot. "
    "CloudSage will NEVER automatically terminate, resize, detach, or modify production resources. "
    "All recommendations must be evaluated and approved by authorized engineering and FinOps personnel."
)


def generate_cli_command(
    provider: CloudProvider,
    action: RecommendationAction,
    resource_id: Optional[str],
    resource_name: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> str:
    """Generates copy-paste ready hyperscaler CLI commands."""
    params = parameters or {}
    res_ref = resource_id or "RESOURCE_ID"

    if provider == CloudProvider.AWS:
        if action == RecommendationAction.TERMINATE:
            return f"aws ec2 terminate-instances --instance-ids {res_ref}"
        elif action == RecommendationAction.SCHEDULE_SHUTDOWN:
            return f"aws ec2 stop-instances --instance-ids {res_ref}"
        elif action == RecommendationAction.RIGHTSIZE:
            target_type = params.get("target_type", "m5.large")
            return (
                f"# 1. Stop instance\naws ec2 stop-instances --instance-ids {res_ref}\n"
                f"# 2. Modify instance attribute\naws ec2 modify-instance-attribute --instance-id {res_ref} --instance-type '{{\"Value\": \"{target_type}\"}}'\n"
                f"# 3. Restart instance\naws ec2 start-instances --instance-ids {res_ref}"
            )
        elif action == RecommendationAction.DELETE_SNAPSHOT:
            return f"aws ec2 delete-snapshot --snapshot-id {res_ref}"
        elif action == RecommendationAction.RELEASE_IP:
            alloc_id = params.get("allocation_id", res_ref)
            return f"aws ec2 release-address --allocation-id {alloc_id}"
        elif action == RecommendationAction.CONVERT_STORAGE_TIER:
            bucket = params.get("bucket", "BUCKET_NAME")
            prefix = params.get("prefix", "")
            tier = params.get("target_tier", "GLACIER")
            return f"aws s3api put-bucket-lifecycle-configuration --bucket {bucket} --lifecycle-configuration file://lifecycle.json"
        elif action == RecommendationAction.PURCHASE_SAVINGS_PLAN:
            return "aws savingsplans create-savings-plan --savings-plan-offering-id OFFERING_ID --commitment COMMITMENT_USD"
        elif action == RecommendationAction.INVESTIGATE_ANOMALY:
            return f"aws ce get-cost-and-usage --time-period Start={params.get('start_date', '2026-01-01')},End={params.get('end_date', '2026-01-31')} --granularity DAILY --metrics UnblendedCost"
        else:
            return f"# Evaluate and remediate AWS resource {res_ref}"

    elif provider == CloudProvider.AZURE:
        rg = params.get("resource_group", "RESOURCE_GROUP")
        vm_name = resource_name or "VM_NAME"
        if action == RecommendationAction.TERMINATE:
            return f"az vm delete --resource-group {rg} --name {vm_name} --yes"
        elif action == RecommendationAction.SCHEDULE_SHUTDOWN:
            return f"az vm deallocate --resource-group {rg} --name {vm_name}"
        elif action == RecommendationAction.RIGHTSIZE:
            target_size = params.get("target_type", "Standard_D4s_v5")
            return f"az vm update --resource-group {rg} --name {vm_name} --size {target_size}"
        elif action == RecommendationAction.DELETE_SNAPSHOT:
            return f"az snapshot delete --resource-group {rg} --name {res_ref}"
        elif action == RecommendationAction.RELEASE_IP:
            return f"az network public-ip delete --resource-group {rg} --name {res_ref}"
        elif action == RecommendationAction.CONVERT_STORAGE_TIER:
            account = params.get("storage_account", "STORAGE_ACCOUNT")
            container = params.get("container", "CONTAINER_NAME")
            tier = params.get("target_tier", "Cool")
            return f"az storage blob set-tier --account-name {account} --container-name {container} --tier {tier} --name BLOB_NAME"
        elif action == RecommendationAction.PURCHASE_SAVINGS_PLAN or action == RecommendationAction.RESERVE_CAPACITY:
            return "az reservations reservation-order calculate --sku SKU_NAME"
        elif action == RecommendationAction.INVESTIGATE_ANOMALY:
            return "az costmanagement query --type Usage --timeframe Custom"
        else:
            return f"# Evaluate and remediate Azure resource {res_ref}"

    elif provider == CloudProvider.GCP:
        project = params.get("project_id", "PROJECT_ID")
        zone = params.get("zone", "us-central1-a")
        inst_name = resource_name or "INSTANCE_NAME"
        if action == RecommendationAction.TERMINATE:
            return f"gcloud compute instances delete {inst_name} --project={project} --zone={zone} --quiet"
        elif action == RecommendationAction.SCHEDULE_SHUTDOWN:
            return f"gcloud compute instances stop {inst_name} --project={project} --zone={zone}"
        elif action == RecommendationAction.RIGHTSIZE:
            target_mach = params.get("target_type", "e2-standard-4")
            return (
                f"# 1. Stop instance\ngcloud compute instances stop {inst_name} --project={project} --zone={zone}\n"
                f"# 2. Resize machine type\ngcloud compute instances set-machine-type {inst_name} --machine-type={target_mach} --project={project} --zone={zone}\n"
                f"# 3. Start instance\ngcloud compute instances start {inst_name} --project={project} --zone={zone}"
            )
        elif action == RecommendationAction.DELETE_SNAPSHOT:
            return f"gcloud compute snapshots delete {res_ref} --project={project} --quiet"
        elif action == RecommendationAction.RELEASE_IP:
            return f"gcloud compute addresses delete {res_ref} --project={project} --region={zone[:-2]} --quiet"
        elif action == RecommendationAction.CONVERT_STORAGE_TIER:
            bucket = params.get("bucket", "BUCKET_NAME")
            tier = params.get("target_tier", "NEARLINE")
            return f"gcloud storage buckets update gs://{bucket} --default-storage-class={tier}"
        elif action == RecommendationAction.PURCHASE_SAVINGS_PLAN or action == RecommendationAction.RESERVE_CAPACITY:
            return "gcloud compute commitments create COMMITMENT_NAME --plan=TWELVE_MONTH"
        elif action == RecommendationAction.INVESTIGATE_ANOMALY:
            return "gcloud billing accounts reports get BILLING_ACCOUNT_ID"
        else:
            return f"# Evaluate and remediate GCP resource {res_ref}"

    return f"# Advisory guidance for {provider} {res_ref}"


def generate_terraform_snippet(
    provider: CloudProvider,
    action: RecommendationAction,
    resource_id: Optional[str],
    resource_name: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> str:
    """Generates declarative Terraform HCL code showing desired target state."""
    params = parameters or {}
    name = resource_name or "app_resource"

    if action == RecommendationAction.RIGHTSIZE:
        target_type = params.get("target_type", "t3.medium")
        current_type = params.get("current_type", "t3.2xlarge")
        return (
            f"# Before: instance_type = \"{current_type}\"\n"
            f"# Target state:\n"
            f"resource \"aws_instance\" \"{name}\" {{\n"
            f"  instance_type = \"{target_type}\"\n"
            f"  # Preserve existing tags and disk attachments\n"
            f"}}"
        )
    elif action == RecommendationAction.SCHEDULE_SHUTDOWN:
        return (
            f"resource \"aws_autoscaling_schedule\" \"nightly_shutdown\" {{\n"
            f"  scheduled_action_name = \"nightly-stop\"\n"
            f"  min_size              = 0\n"
            f"  max_size              = 0\n"
            f"  desired_capacity      = 0\n"
            f"  recurrence            = \"0 20 * * 1-5\" # 8 PM UTC Weekdays\n"
            f"  time_zone             = \"UTC\"\n"
            f"}}"
        )
    elif action == RecommendationAction.CONVERT_STORAGE_TIER:
        return (
            f"resource \"aws_s3_bucket_lifecycle_configuration\" \"archive_rule\" {{\n"
            f"  bucket = \"{params.get('bucket', 'logs-bucket')}\"\n"
            f"  rule {{\n"
            f"    id     = \"archive-infrequent-data\"\n"
            f"    status = \"Enabled\"\n"
            f"    transition {{\n"
            f"      days          = 30\n"
            f"      storage_class = \"GLACIER\"\n"
            f"    }}\n"
            f"  }}\n"
            f"}}"
        )
    elif action == RecommendationAction.TERMINATE:
        return (
            f"# Remove or comment out resource block to decommission cleanly:\n"
            f"# resource \"...\" \"{name}\" {{\n"
            f"#   ...\n"
            f"# }}"
        )
    else:
        return "# Review Terraform definitions and apply parameter adjustments via GitOps workflow."


def generate_rollback_procedure(
    provider: CloudProvider,
    action: RecommendationAction,
    resource_id: Optional[str],
    parameters: Optional[Dict[str, Any]] = None,
) -> str:
    """Generates safety rollback steps in case of service disruption."""
    params = parameters or {}
    res_ref = resource_id or "RESOURCE_ID"

    if action == RecommendationAction.RIGHTSIZE:
        current_type = params.get("current_type", "original_instance_type")
        return (
            f"ROLLBACK PROCEDURE:\n"
            f"If performance degrades below SLA thresholds:\n"
            f"1. Stop instance: aws/az/gcloud compute stop {res_ref}\n"
            f"2. Restore previous type to {current_type}\n"
            f"3. Start instance and verify application health metrics."
        )
    elif action == RecommendationAction.SCHEDULE_SHUTDOWN:
        return (
            f"ROLLBACK PROCEDURE:\n"
            f"If workloads require off-hours execution:\n"
            f"1. Disable scheduled stop trigger or override schedule tag: env:schedule=24x7\n"
            f"2. Start instance manually."
        )
    elif action == RecommendationAction.TERMINATE:
        return (
            f"ROLLBACK PROCEDURE:\n"
            f"Ensure snapshot/backup exists prior to termination.\n"
            f"1. Check automated recovery snapshot: {params.get('backup_id', 'snapshot-latest')}\n"
            f"2. Restore from snapshot or redeploy from CI/CD pipeline."
        )
    else:
        return "ROLLBACK PROCEDURE: Revert configuration change in version-controlled infrastructure repository."


def build_implementation_guidance(
    provider: CloudProvider,
    action: RecommendationAction,
    resource_id: Optional[str],
    resource_name: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assembles complete structured implementation guidance dictionary."""
    cli_snippet = generate_cli_command(provider, action, resource_id, resource_name, parameters)
    tf_snippet = generate_terraform_snippet(provider, action, resource_id, resource_name, parameters)
    rollback = generate_rollback_procedure(provider, action, resource_id, parameters)

    return {
        "advisory_disclaimer": ADVISORY_DISCLAIMER,
        "cli_snippet": cli_snippet,
        "terraform_snippet": tf_snippet,
        "rollback_procedure": rollback,
        "prerequisites": [
            "Confirm backup/snapshot availability",
            "Verify no downstream hard dependencies",
            "Obtain change management approval",
        ],
        "validation_steps": [
            "Monitor CPU and memory utilization post-change",
            "Validate application health endpoint status 200 OK",
            "Review next billing cycle invoice for realized cost reduction",
        ],
    }
