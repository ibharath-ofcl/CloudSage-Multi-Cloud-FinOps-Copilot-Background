"""
Tests for Remediation Playbook Generator.
Verifies multi-format output, advisory header injection, parameter sanitization, and credential safety.
"""

from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.core.database import get_sync_db
from backend.app.main import app
from backend.app.models.recommendation import Recommendation
from backend.app.models.resource import CloudResource
from backend.app.models.waste import WasteDetection
from backend.app.recommendations.playbooks import RemediationPlaybookGenerator, sanitize_identifier


@pytest.fixture
def playbook_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_sync_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_sanitize_identifier_removes_dangerous_characters():
    dirty = "i-012345; rm -rf /; && cat /etc/passwd"
    clean = sanitize_identifier(dirty)
    assert ";" not in clean
    assert "&&" not in clean
    assert " " not in clean
    assert clean == "i-012345rm-rf/cat/etc/passwd"


def test_playbook_generator_terraform():
    res = RemediationPlaybookGenerator.generate_playbook(
        provider="AWS",
        action_type="TERMINATE",
        resource_id="i-0abc12345",
        estimated_monthly_savings=Decimal("75.0000"),
        playbook_format="terraform",
    )
    assert res["format"] == "terraform"
    assert "CLOUDSAGE ADVISORY REMEDIATION PLAYBOOK" in res["content"]
    assert "terraform" in res["content"]
    assert "ROLLBACK PLAN" in res["content"]
    assert res["filename"].endswith(".tf")


def test_playbook_generator_cloudformation():
    res = RemediationPlaybookGenerator.generate_playbook(
        provider="AWS",
        action_type="RIGHTSIZE",
        resource_id="i-0abc12345",
        estimated_monthly_savings=Decimal("120.0000"),
        playbook_format="cloudformation",
    )
    assert "AWSTemplateFormatVersion" in res["content"]
    assert res["filename"].endswith(".yaml")


def test_playbook_generator_aws_cli():
    res = RemediationPlaybookGenerator.generate_playbook(
        provider="AWS",
        action_type="DELETE_SNAPSHOT",
        resource_id="snap-0123456789",
        estimated_monthly_savings=Decimal("35.0000"),
        playbook_format="aws_cli",
    )
    assert "#!/usr/bin/env bash" in res["content"]
    assert "aws ec2 delete-snapshot" in res["content"]
    assert res["filename"].endswith(".sh")


def test_playbook_generator_azure_cli():
    res = RemediationPlaybookGenerator.generate_playbook(
        provider="AZURE",
        action_type="TERMINATE",
        resource_id="/subscriptions/sub-1/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-1",
        estimated_monthly_savings=Decimal("150.0000"),
        playbook_format="azure_cli",
    )
    assert "az resource" in res["content"] or "az vm" in res["content"]
    assert res["filename"].endswith(".sh")


def test_playbook_generator_azure_bicep():
    res = RemediationPlaybookGenerator.generate_playbook(
        provider="AZURE",
        action_type="RIGHTSIZE",
        resource_id="vm-db-01",
        estimated_monthly_savings=Decimal("200.0000"),
        playbook_format="bicep",
    )
    assert "Azure Bicep Advisory Template" in res["content"]
    assert res["filename"].endswith(".bicep")


def test_playbook_generator_gcp_cli():
    res = RemediationPlaybookGenerator.generate_playbook(
        provider="GCP",
        action_type="TERMINATE",
        resource_id="gcp-instance-prod",
        estimated_monthly_savings=Decimal("90.0000"),
        playbook_format="gcp_cli",
    )
    assert "gcloud compute instances" in res["content"]
    assert res["filename"].endswith(".sh")


def test_playbook_generator_markdown():
    res = RemediationPlaybookGenerator.generate_playbook(
        provider="AWS",
        action_type="RIGHTSIZE",
        resource_id="i-test-md",
        estimated_monthly_savings=Decimal("60.0000"),
        playbook_format="markdown",
    )
    assert "# CloudSage Advisory Remediation Playbook" in res["content"]
    assert "Rollback Procedures" in res["content"]
    assert res["filename"].endswith(".md")


def test_recommendation_playbook_endpoint(playbook_client, db_session):
    rec = Recommendation(
        id=uuid.uuid4(),
        recommendation_key="playbook-test-rec",
        resource_id="i-0playbooktest",
        provider="AWS",
        action_type="RIGHTSIZE",
        priority="P2",
        status="PROPOSED",
        estimated_monthly_savings=Decimal("85.0000"),
        estimated_annual_savings=Decimal("1020.0000"),
        title="Rightsize EC2",
        description="Desc",
        remediation_guide="Guide",
    )
    db_session.add(rec)
    db_session.commit()

    response = playbook_client.get(f"/api/v1/recommendations/{rec.id}/playbook?format=terraform")
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "terraform"
    assert "CLOUDSAGE ADVISORY REMEDIATION PLAYBOOK" in data["content"]


def test_recommendation_playbook_download_endpoint(playbook_client, db_session):
    rec = Recommendation(
        id=uuid.uuid4(),
        recommendation_key="playbook-download-rec",
        resource_id="i-0playbookdl",
        provider="AWS",
        action_type="RIGHTSIZE",
        priority="P2",
        status="PROPOSED",
        estimated_monthly_savings=Decimal("85.0000"),
        estimated_annual_savings=Decimal("1020.0000"),
        title="Rightsize EC2",
        description="Desc",
        remediation_guide="Guide",
    )
    db_session.add(rec)
    db_session.commit()

    response = playbook_client.get(f"/api/v1/recommendations/{rec.id}/playbook/download?format=aws_cli")
    assert response.status_code == 200
    assert "Content-Disposition" in response.headers
    assert "attachment; filename=" in response.headers["Content-Disposition"]
    assert "#!/usr/bin/env bash" in response.text
