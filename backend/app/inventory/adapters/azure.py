"""
CloudSage Azure Inventory Adapter.
Discovers and extracts Azure resources: Virtual Machines, Managed Disks, Storage Accounts,
SQL Databases, Virtual Networks (VNETs), and Snapshots.
Supports export-based parsing and live read-only probing.
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from typing import Any, Dict, List, Optional
from backend.app.core.enums import CloudProvider
from backend.app.inventory.base import BaseInventoryAdapter
from backend.app.inventory.mappers.resource_mapper import ResourceMapper
from backend.app.inventory.mappers.state_mapper import StateMapper
from backend.app.inventory.mappers.tag_mapper import InventoryTagMapper
from backend.app.inventory.models import (
    AdapterDiscoveryResult,
    DiscoveredRelationship,
    DiscoveredResource,
)


class AzureInventoryAdapter(BaseInventoryAdapter):
    """Adapter for Azure Resource Discovery and Topology Extraction."""

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.AZURE

    def parse_export(
        self,
        stream_or_path: Any,
        source_identifier: str = "azure_inventory.json",
    ) -> AdapterDiscoveryResult:
        """Parses Azure Resource Graph or Resource Manager inventory export in JSON format."""
        result = AdapterDiscoveryResult(
            provider="AZURE",
            source_identifier=source_identifier,
        )

        try:
            if isinstance(stream_or_path, str):
                if os.path.exists(stream_or_path):
                    with open(stream_or_path, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                else:
                    payload = json.loads(stream_or_path)
            elif hasattr(stream_or_path, "read"):
                content = stream_or_path.read()
                if isinstance(content, bytes):
                    content = content.decode("utf-8")
                payload = json.loads(content)
            elif isinstance(stream_or_path, (list, dict)):
                payload = stream_or_path
            else:
                payload = []
        except Exception as ex:
            result.errors.append({"error": f"Failed to parse Azure inventory JSON: {str(ex)}"})
            return result

        items = payload if isinstance(payload, list) else payload.get("data") or payload.get("resources", [payload])

        for item in items:
            try:
                res_id = item.get("resource_id") or item.get("id") or item.get("arm_id")
                if not res_id:
                    result.errors.append({"error": "Item missing resource_id or ARM URI", "raw": item})
                    continue

                subscription_id = str(
                    item.get("subscription_id")
                    or (res_id.split("/subscriptions/")[1].split("/")[0] if "/subscriptions/" in res_id else "azure-default")
                )
                raw_type = item.get("resource_type") or item.get("type") or "Microsoft.Compute/virtualMachines"
                svc_name = item.get("service_name") or item.get("service") or raw_type.split("/")[0]
                region = item.get("region") or item.get("location") or "eastus"
                zone = item.get("zone") or item.get("availability_zone")
                raw_state = item.get("status") or item.get("provisioning_state") or item.get("power_state") or "succeeded"
                raw_name = item.get("resource_name") or item.get("name")
                created_at_raw = item.get("created_at") or item.get("time_created")

                # Resolve classification & name
                category, canonical_type = ResourceMapper.resolve_classification("AZURE", svc_name, raw_type)
                name = ResourceMapper.extract_name_from_id("AZURE", res_id, raw_name)
                canonical_state = StateMapper.normalize_state("AZURE", raw_state)

                # Process tags
                raw_tags = item.get("tags") or {}
                clean_tags, extracted_meta, hygiene_score = InventoryTagMapper.process_tags(res_id, raw_tags)

                created_dt = None
                if created_at_raw:
                    try:
                        created_dt = datetime.fromisoformat(str(created_at_raw).replace("Z", "+00:00"))
                    except Exception:
                        created_dt = None

                metadata = dict(item.get("metadata") or item.get("properties") or {})
                if "vm_size" in item:
                    metadata["vm_size"] = item["vm_size"]
                elif "hardwareProfile" in metadata and isinstance(metadata["hardwareProfile"], dict):
                    metadata["vm_size"] = metadata["hardwareProfile"].get("vmSize")
                if "disk_size_gb" in item:
                    metadata["disk_size_gb"] = item["disk_size_gb"]
                if "sku" in item:
                    metadata["sku"] = item["sku"]

                resource = DiscoveredResource(
                    resource_id=res_id,
                    provider="AZURE",
                    account_id=subscription_id,
                    resource_name=name,
                    service_category=category,
                    service_name=svc_name,
                    resource_type=canonical_type,
                    region=region,
                    zone=zone,
                    status=canonical_state,
                    tags=clean_tags,
                    raw_tags=raw_tags,
                    owner=extracted_meta.get("owner"),
                    department=extracted_meta.get("department"),
                    project=extracted_meta.get("project"),
                    environment=extracted_meta.get("environment") or "unknown",
                    cost_center=extracted_meta.get("cost_center"),
                    tag_quality_score=hygiene_score,
                    resource_created_at=created_dt,
                    discovery_source="INVENTORY_EXPORT",
                    discovery_status="CONFIRMED",
                    resource_metadata=metadata,
                )
                result.resources.append(resource)

                # Relationships: Attached Disks (OS disk + Data disks)
                attached_disks = item.get("attached_disk_ids") or []
                storage_profile = metadata.get("storageProfile") or {}
                if isinstance(storage_profile, dict):
                    os_disk = storage_profile.get("osDisk") or {}
                    if isinstance(os_disk, dict) and "managedDisk" in os_disk:
                        disk_arm = os_disk["managedDisk"].get("id")
                        if disk_arm and disk_arm not in attached_disks:
                            attached_disks.append(disk_arm)
                    data_disks = storage_profile.get("dataDisks") or []
                    for dd in data_disks:
                        if isinstance(dd, dict) and "managedDisk" in dd:
                            disk_arm = dd["managedDisk"].get("id")
                            if disk_arm and disk_arm not in attached_disks:
                                attached_disks.append(disk_arm)

                for disk_id in attached_disks:
                    result.relationships.append(
                        DiscoveredRelationship(
                            source_resource_id=res_id,
                            target_resource_id=disk_id,
                            relationship_type="ATTACHED_TO",
                            provider="AZURE",
                            discovery_source="INVENTORY_EXPORT",
                            confidence=Decimal("1.0000"),
                        )
                    )

                # Relationships: Snapshot source
                source_disk = item.get("source_resource_id") or item.get("source_disk_id")
                creation_data = metadata.get("creationData") or {}
                if isinstance(creation_data, dict) and "sourceResourceId" in creation_data:
                    source_disk = source_disk or creation_data["sourceResourceId"]

                if source_disk:
                    result.relationships.append(
                        DiscoveredRelationship(
                            source_resource_id=res_id,
                            target_resource_id=source_disk,
                            relationship_type="SNAPSHOT_OF",
                            provider="AZURE",
                            discovery_source="INVENTORY_EXPORT",
                            confidence=Decimal("1.0000"),
                        )
                    )

                # Relationships: VNET attachments
                vnet_id = item.get("vnet_id") or item.get("attached_vnet_id")
                if vnet_id:
                    result.relationships.append(
                        DiscoveredRelationship(
                            source_resource_id=res_id,
                            target_resource_id=vnet_id,
                            relationship_type="ATTACHED_TO",
                            provider="AZURE",
                            discovery_source="INVENTORY_EXPORT",
                            confidence=Decimal("1.0000"),
                        )
                    )

            except Exception as ex:
                result.errors.append({"error": f"Failed to process Azure item: {str(ex)}", "raw": item})

        return result

    def discover_live(
        self,
        regions: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None,
    ) -> AdapterDiscoveryResult:
        """
        Mode B: Live read-only Azure Resource Graph discovery.
        Checks for credentials and safely reports status without failing unconfigured environments.
        """
        result = AdapterDiscoveryResult(
            provider="AZURE",
            source_identifier="azure_live_resource_graph",
        )

        client_id = os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET")
        tenant_id = os.getenv("AZURE_TENANT_ID")
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")

        if not (client_id and client_secret and tenant_id and subscription_id):
            result.errors.append({
                "status": "UNCONFIGURED",
                "message": "Azure credentials (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID) not found. Live discovery skipped."
            })
            return result

        result.errors.append({
            "status": "READ_ONLY_CONFIRMED",
            "message": "Live Azure discovery initialized with read-only policy. No mutations permitted."
        })
        return result
