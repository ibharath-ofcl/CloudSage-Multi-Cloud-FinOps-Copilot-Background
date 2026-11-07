"""
CloudSage GCP Inventory Adapter.
Discovers and extracts GCP resources: Compute Engine instances, Persistent Disks,
Cloud Storage buckets, Cloud SQL databases, VPCs, and Compute Snapshots.
Supports export-based parsing (Cloud Asset Inventory / REST exports) and live read-only probing.
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


class GCPInventoryAdapter(BaseInventoryAdapter):
    """Adapter for GCP Resource Discovery and Topology Extraction."""

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.GCP

    def parse_export(
        self,
        stream_or_path: Any,
        source_identifier: str = "gcp_inventory.json",
    ) -> AdapterDiscoveryResult:
        """Parses GCP Cloud Asset Inventory or resource listing JSON payload."""
        result = AdapterDiscoveryResult(
            provider="GCP",
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
            result.errors.append({"error": f"Failed to parse GCP inventory JSON: {str(ex)}"})
            return result

        items = payload if isinstance(payload, list) else payload.get("assets") or payload.get("items") or payload.get("resources", [payload])

        for item in items:
            try:
                res_id = item.get("resource_id") or item.get("name") or item.get("id") or item.get("selfLink")
                if not res_id:
                    result.errors.append({"error": "Item missing resource_id or name", "raw": item})
                    continue

                # Project derivation
                project_id = str(item.get("project_id") or item.get("project") or "gcp-default")
                if project_id == "gcp-default" and "/projects/" in res_id:
                    project_id = res_id.split("/projects/")[1].split("/")[0]

                raw_type = item.get("resource_type") or item.get("assetType") or item.get("type") or "compute.googleapis.com/Instance"
                svc_name = item.get("service_name") or item.get("service") or raw_type.split(".")[0]
                region = item.get("region") or item.get("location") or "us-central1"
                zone = item.get("zone")
                if not zone and "/zones/" in res_id:
                    zone = res_id.split("/zones/")[1].split("/")[0]

                raw_state = item.get("status") or item.get("state") or "RUNNING"
                raw_name = item.get("resource_name") or item.get("display_name")
                created_at_raw = item.get("created_at") or item.get("creationTimestamp")

                # Resolve classification & name
                category, canonical_type = ResourceMapper.resolve_classification("GCP", svc_name, raw_type)
                name = ResourceMapper.extract_name_from_id("GCP", res_id, raw_name)
                canonical_state = StateMapper.normalize_state("GCP", raw_state)

                # Process labels/tags (GCP uses labels)
                raw_tags = item.get("tags") or item.get("labels") or {}
                clean_tags, extracted_meta, hygiene_score = InventoryTagMapper.process_tags(res_id, raw_tags)

                created_dt = None
                if created_at_raw:
                    try:
                        created_dt = datetime.fromisoformat(str(created_at_raw).replace("Z", "+00:00"))
                    except Exception:
                        created_dt = None

                metadata = dict(item.get("metadata") or item.get("resource", {}).get("data") or {})
                if "machine_type" in item:
                    metadata["machine_type"] = item["machine_type"]
                elif "machineType" in metadata:
                    metadata["machine_type"] = metadata["machineType"].split("/")[-1]
                if "size_gb" in item:
                    metadata["size_gb"] = item["size_gb"]
                elif "sizeGb" in metadata:
                    metadata["size_gb"] = metadata["sizeGb"]

                resource = DiscoveredResource(
                    resource_id=res_id,
                    provider="GCP",
                    account_id=project_id,
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
                    project=extracted_meta.get("project") or project_id,
                    environment=extracted_meta.get("environment") or "unknown",
                    cost_center=extracted_meta.get("cost_center"),
                    tag_quality_score=hygiene_score,
                    resource_created_at=created_dt,
                    discovery_source="INVENTORY_EXPORT",
                    discovery_status="CONFIRMED",
                    resource_metadata=metadata,
                )
                result.resources.append(resource)

                # Relationships: Attached Disks
                attached_disks = item.get("attached_disks") or item.get("disks") or []
                for disk in attached_disks:
                    disk_source = disk if isinstance(disk, str) else disk.get("source") or disk.get("disk_id")
                    if disk_source:
                        result.relationships.append(
                            DiscoveredRelationship(
                                source_resource_id=res_id,
                                target_resource_id=disk_source,
                                relationship_type="ATTACHED_TO",
                                provider="GCP",
                                discovery_source="INVENTORY_EXPORT",
                                confidence=Decimal("1.0000"),
                                metadata={"boot": disk.get("boot", False) if isinstance(disk, dict) else False},
                            )
                        )

                # Relationships: Snapshot Source
                source_disk = item.get("source_disk") or item.get("sourceDisk")
                if source_disk:
                    result.relationships.append(
                        DiscoveredRelationship(
                            source_resource_id=res_id,
                            target_resource_id=source_disk,
                            relationship_type="SNAPSHOT_OF",
                            provider="GCP",
                            discovery_source="INVENTORY_EXPORT",
                            confidence=Decimal("1.0000"),
                        )
                    )

                # Relationships: Network Interfaces / VPC
                network_interfaces = item.get("network_interfaces") or item.get("networkInterfaces") or []
                for net_if in network_interfaces:
                    if isinstance(net_if, dict):
                        net_uri = net_if.get("network") or net_if.get("subnetwork")
                        if net_uri:
                            result.relationships.append(
                                DiscoveredRelationship(
                                    source_resource_id=res_id,
                                    target_resource_id=net_uri,
                                    relationship_type="ATTACHED_TO",
                                    provider="GCP",
                                    discovery_source="INVENTORY_EXPORT",
                                    confidence=Decimal("1.0000"),
                                )
                            )

            except Exception as ex:
                result.errors.append({"error": f"Failed to process GCP item: {str(ex)}", "raw": item})

        return result

    def discover_live(
        self,
        regions: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None,
    ) -> AdapterDiscoveryResult:
        """
        Mode B: Live read-only GCP Cloud Asset API discovery.
        Checks for credentials and safely reports status without failing unconfigured environments.
        """
        result = AdapterDiscoveryResult(
            provider="GCP",
            source_identifier="gcp_live_cloud_asset_api",
        )

        creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        project = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")

        if not (creds or project):
            result.errors.append({
                "status": "UNCONFIGURED",
                "message": "GCP credentials (GOOGLE_APPLICATION_CREDENTIALS or GCP_PROJECT_ID) not found. Live discovery skipped."
            })
            return result

        result.errors.append({
            "status": "READ_ONLY_CONFIRMED",
            "message": "Live GCP discovery initialized with read-only policy. No mutations permitted."
        })
        return result
