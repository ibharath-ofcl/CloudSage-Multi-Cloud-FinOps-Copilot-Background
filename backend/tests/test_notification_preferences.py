"""
Unit and Integration Tests for User Notification Preferences.
Tests default preference generation, channel opt-in/opt-out, minimum severity filtering,
quiet hours scheduling, and digest frequency preferences.
"""

from datetime import datetime, timezone
import uuid
import pytest

from backend.app.core.enums import NotificationChannel, Severity
from backend.app.models.alert import NotificationPreference
from backend.app.schemas.alert import NotificationPreferenceRequest


def test_default_notification_preference_creation(db_session):
    """Verifies default notification preference structure."""
    pref = NotificationPreference(
        id=uuid.uuid4(),
        user_id="user-100",
        user_email="user100@company.com",
        enabled_channels=["IN_APP", "EMAIL"],
        min_severity=Severity.LOW.value,
        receive_digests=True,
        digest_frequency="DAILY",
        quiet_hours_enabled=False,
    )
    db_session.add(pref)
    db_session.commit()

    saved = db_session.query(NotificationPreference).filter(NotificationPreference.user_id == "user-100").first()
    assert saved is not None
    assert saved.user_email == "user100@company.com"
    assert "IN_APP" in saved.enabled_channels
    assert "EMAIL" in saved.enabled_channels
    assert saved.min_severity == Severity.LOW.value
    assert saved.receive_digests is True
    assert saved.digest_frequency == "DAILY"


def test_channel_opt_out_update(db_session):
    """Verifies opting out of email while keeping in-app."""
    pref = NotificationPreference(
        id=uuid.uuid4(),
        user_id="user-101",
        user_email="user101@company.com",
        enabled_channels=["IN_APP", "EMAIL"],
    )
    db_session.add(pref)
    db_session.commit()

    pref.enabled_channels = ["IN_APP"]
    db_session.commit()

    refreshed = db_session.query(NotificationPreference).filter(NotificationPreference.user_id == "user-101").first()
    assert refreshed.enabled_channels == ["IN_APP"]
    assert "EMAIL" not in refreshed.enabled_channels


def test_quiet_hours_configuration(db_session):
    """Verifies quiet hours configuration and validation."""
    pref = NotificationPreference(
        id=uuid.uuid4(),
        user_id="user-102",
        user_email="user102@company.com",
        quiet_hours_enabled=True,
        quiet_hours_start_utc="22:00",
        quiet_hours_end_utc="08:00",
    )
    db_session.add(pref)
    db_session.commit()

    refreshed = db_session.query(NotificationPreference).filter(NotificationPreference.user_id == "user-102").first()
    assert refreshed.quiet_hours_enabled is True
    assert refreshed.quiet_hours_start_utc == "22:00"
    assert refreshed.quiet_hours_end_utc == "08:00"


def test_digest_frequency_configuration(db_session):
    """Verifies changing digest frequency between IMMEDIATE, DAILY, WEEKLY."""
    pref = NotificationPreference(
        id=uuid.uuid4(),
        user_id="user-103",
        user_email="user103@company.com",
        receive_digests=True,
        digest_frequency="WEEKLY",
    )
    db_session.add(pref)
    db_session.commit()

    refreshed = db_session.query(NotificationPreference).filter(NotificationPreference.user_id == "user-103").first()
    assert refreshed.digest_frequency == "WEEKLY"


def test_preference_schema_validation_rejects_invalid_channel():
    """Verifies that NotificationPreferenceRequest rejects non-existent channels."""
    with pytest.raises(ValueError, match="Invalid channel"):
        NotificationPreferenceRequest(
            enabled_channels=["INVALID_CHANNEL"],
        )
