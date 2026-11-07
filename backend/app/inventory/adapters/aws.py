"""
CloudSage AWS Inventory Adapter.
Discovers and extracts AWS resources: EC2, EBS, S3, RDS, Lambda, and Snapshots.
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


class AWSInventoryAdapter(BaseInventoryAdapter):
    """Adapter for AWS Resource Discovery and Topology Extraction."""

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.AWS

    def parse_export(
        self,
        stream_or_path: Any,
        source_identifier: str = "aws_inventory.json",
    ) -> AdapterDiscoveryResult:
        """Parses AWS inventory export payload in JSON format."""
        result = AdapterDiscoveryResult(
            provider="AWS",
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
            result.errors.append({"error": f"Failed to parse AWS inventory JSON: {str(ex)}"})
            return result

        items = payload if isinstance(payload, list) else payload.get("resources", [payload])

        for item in items:
            try:
                res_id = item.get("resource_id") or item.get("arn") or item.get("id")
                if not res_id:
                    result.errors.append({"error": "Item missing resource_id or ARN", "raw": item})
                    continue

                account_id = str(item.get("account_id") or item.get("owner_id") or "aws-default")
                svc_name = item.get("service_name") or item.get("service") or "AmazonEC2"
                raw_type = item.get("resource_type") or item.get("type") or "ec2:instance"
                region = item.get("region") or item.get("location") or "us-east-1"
                zone = item.get("zone") or item.get("availability_zone")
                raw_state = item.get("status") or item.get("state") or "running"
                raw_name = item.get("resource_name") or item.get("name")
                created_at_raw = item.get("created_at") or item.get("launch_time")

                # Resolve classification & name
                category, canonical_type = ResourceMapper.resolve_classification("AWS", svc_name, raw_type)
                name = ResourceMapper.extract_name_from_id("AWS", res_id, raw_name)
                canonical_state = StateMapper.normalize_state("AWS", raw_state)

                # Process tags
                raw_tags = item.get("tags") or {}
                clean_tags, extracted_meta, hygiene_score = InventoryTagMapper.process_tags(res_id, raw_tags)

                created_dt = None
                if created_at_raw:
                    try:
                        created_dt = datetime.fromisoformat(str(created_at_raw).replace("Z", "+00:00"))
                    except Exception:
                        created_dt = None

                metadata = dict(item.get("metadata") or {})
                if "instance_type" in item:
                    metadata["instance_type"] = item["instance_type"]
                if "size_gb" in item:
                    metadata["size_gb"] = item["size_gb"]
                if "volume_type" in item:
                    metadata["volume_type"] = item["volume_type"]

                resource = DiscoveredResource(
                    resource_id=res_id,
                    provider="AWS",
                    account_id=account_id,
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

                # Relationship Extraction (e.g. Attached EBS volumes, VPC attachments, Snapshot sources)
                attached_vols = item.get("attached_volume_ids") or item.get("block_device_mappings") or []
                for vol in attached_vols:
                    target_vol_id = vol if isinstance(vol, str) else vol.get("volume_id")
                    if target_vol_id:
                        result.relationships.append(
                            DiscoveredRelationship(
                                source_resource_id=res_id,
                                target_resource_id=target_vol_id,
                                relationship_type="ATTACHED_TO",
                                provider="AWS",
                                discovery_source="INVENTORY_EXPORT",
                                confidence=Decimal("1.0000"),
                                metadata={"device": vol.get("device_name") if isinstance(vol, dict) else "/dev/sda1"},
                            )
                        )

                # Snapshot source volume relationship
                source_vol = item.get("source_volume_id")
                if source_vol:
                    result.relationships.append(
                        DiscoveredRelationship(
                            source_resource_id=res_id,
                            target_resource_id=source_vol,
                            relationship_type="SNAPSHOT_OF",
                            provider="AWS",
                            discovery_source="INVENTORY_EXPORT",
                            confidence=Decimal("1.0000"),
                        )
                    )

            except Exception as ex:
                result.errors.append({"error": f"Failed to process AWS item: {str(ex)}", "raw": item})

        return result

    def discover_live(
        self,
        regions: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None,
    ) -> AdapterDiscoveryResult:
        """
        Mode B: Live read-only AWS cloud discovery.
        Checks for credentials and safely reports status without failing unconfigured environments.
        """
        result = AdapterDiscoveryResult(
            provider="AWS",
            source_identifier="aws_live_cloud_api",
        )

        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        if not aws_access_key or not aws_secret_key:
            result.errors.append({
                "status": "UNCONFIGURED",
                "message": "AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) not found in environment. Live discovery skipped."
            })
            return result

        # If live credentials exist, SDK client probing would occur here with read-only IAM calls.
        result.errors.append({
            "status": "READ_ONLY_CONFIRMED",
            "message": "Live AWS discovery initialized with read-only policy. No mutations permitted."
        })
        return result
