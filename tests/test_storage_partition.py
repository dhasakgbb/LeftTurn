from src.services.storage_service import StorageService


class _TrackingContainer:
    def __init__(self) -> None:
        self.last_partition = None

    def read_item(self, tracking_id, partition_key=None):
        return {"id": tracking_id, "file_id": partition_key}

    def query_items(self, *args, **kwargs):  # pragma: no cover - not used here
        return []

    def replace_item(self, doc_id, item, partition_key=None):
        self.last_partition = partition_key


class _FakeDatabase:
    def __init__(self, container):
        self._container = container

    def get_container_client(self, name):
        return self._container


class _FakeCosmos:
    def __init__(self, container):
        self._db = _FakeDatabase(container)

    def get_database_client(self, name):
        return self._db


def test_update_change_tracking_uses_partition_key():
    container = _TrackingContainer()
    svc = StorageService()
    svc.cosmos_client = _FakeCosmos(container)

    ok = svc.update_change_tracking("track-1", "hash-2", file_id="file-123")
    assert ok is True
    assert container.last_partition == "file-123"
