from datetime import datetime, timezone, timedelta

from src.services.storage_service import StorageService
from src.models.validation_models import (
    EmailNotification,
    ValidationResult,
    ValidationStatus,
)


class _FakeContainer:
    def __init__(self):
        self.items = {}

    def create_item(self, item):
        self.items[item["id"]] = item

    def read_item(self, id, partition_key=None):
        return self.items[id]

    def replace_item(self, id, item):
        self.items[id] = item

    def query_items(self, query, parameters=None, enable_cross_partition_query=None):
        # naive implementation only used by tests
        if "FROM c WHERE c.id = @id" in query:
            vid = next(p["value"] for p in parameters if p["name"] == "@id")
            return [self.items.get(vid)] if vid in self.items else []
        if "FROM c WHERE c.status = 'failed'" in query:
            cutoff = next(p["value"] for p in parameters if p["name"] == "@cutoff")
            # treat cutoff as iso string; return all failed older than cutoff
            out = []
            for item in self.items.values():
                if item.get("status") == "failed" and item.get("timestamp", "") < cutoff:
                    out.append(item)
            return out
        if "FROM c WHERE c.file_id = @file_id" in query:
            fid = next(p["value"] for p in parameters if p["name"] == "@file_id")
            return [it for it in self.items.values() if it.get("file_id") == fid]
        return []


class _FakeDatabase:
    def __init__(self):
        self.containers = {
            "file-metadata": _FakeContainer(),
            "validation-results": _FakeContainer(),
            "email-notifications": _FakeContainer(),
            "change-tracking": _FakeContainer(),
        }

    def get_container_client(self, name):
        return self.containers[name]

    # Cosmos SDK create_if_not_exists compat not used in tests


class _FakeCosmos:
    def __init__(self):
        self.db = _FakeDatabase()

    def get_database_client(self, name):
        return self.db

    # used during init (ignored in tests)
    def create_database_if_not_exists(self, name):
        return self.db


def test_storage_get_email_notification(monkeypatch):
    svc = StorageService()
    fake = _FakeCosmos()
    svc.cosmos_client = fake
    db = fake.get_database_client(svc.database_name)
    emails = db.get_container_client(svc.containers["emails"])

    rec = EmailNotification(
        notification_id="n1",
        file_id="f1",
        validation_id="v1",
        recipient_email="a@b.com",
        subject="s",
        sent_timestamp=datetime.now(timezone.utc),
        delivery_status="sent",
    )
    item = rec.model_dump()
    item["id"] = rec.notification_id
    item["sent_timestamp"] = rec.sent_timestamp.isoformat()
    emails.create_item(item)

    got = svc.get_email_notification("n1")
    assert got and got.notification_id == "n1"


def test_storage_list_failed_validations(monkeypatch):
    svc = StorageService()
    fake = _FakeCosmos()
    svc.cosmos_client = fake
    db = fake.get_database_client(svc.database_name)
    vals = db.get_container_client(svc.containers["validations"])

    ts_old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    vals.create_item({
        "id": "v1",
        "file_id": "f1",
        "status": "failed",
        "timestamp": ts_old,
        "errors": [],
        "warnings": []
    })

    results = svc.list_failed_validations(days_older_than=3, limit=100)
    assert len(results) >= 1


def test_update_validation_status(monkeypatch):
    svc = StorageService()
    fake = _FakeCosmos()
    svc.cosmos_client = fake
    db = fake.get_database_client(svc.database_name)
    vals = db.get_container_client(svc.containers["validations"])
    vals.create_item({"id": "v1", "file_id": "f1", "status": "failed", "timestamp": datetime.now(timezone.utc).isoformat(), "errors": [], "warnings": []})

    ok = svc.update_validation_status("v1", ValidationStatus.CORRECTED)
    assert ok is True
    assert vals.items["v1"]["status"] == "corrected"

