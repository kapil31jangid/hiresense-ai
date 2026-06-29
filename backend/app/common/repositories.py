from __future__ import annotations

from collections.abc import MutableMapping
from copy import deepcopy
from enum import Enum
from typing import Any, Dict, Iterable, Iterator, List, Optional

from app.common.runtime import build_runtime_state


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize_value(v) for v in value]
    if isinstance(value, tuple):
        return [_serialize_value(v) for v in value]
    return value


def _deserialize_value(value: Any) -> Any:
    return deepcopy(value)


class FirestoreBackedStore(MutableMapping[str, Dict[str, Any]]):
    def __init__(self, collection_name: str, seed_data: Optional[Dict[str, Dict[str, Any]]] = None):
        self.collection_name = collection_name
        self._memory: Dict[str, Dict[str, Any]] = deepcopy(seed_data or {})
        self._runtime = build_runtime_state()

    def _client(self):
        runtime = self._runtime
        return runtime.firestore_client if runtime.firestore_ready else None

    def _collection(self):
        client = self._client()
        if client is None:
            return None
        return client.collection(self.collection_name)

    def _sync_from_remote(self) -> None:
        collection = self._collection()
        if collection is None:
            return
        try:
            for snapshot in collection.stream():
                data = _deserialize_value(snapshot.to_dict() or {})
                if snapshot.id:
                    self._memory[snapshot.id] = data
        except Exception as exc:
            import logging
            logging.getLogger("hiresense_api").warning(
                f"Firestore collection.stream() failed for '{self.collection_name}': {exc}"
            )
            return

    def _sync_set(self, key: str, value: Dict[str, Any]) -> None:
        collection = self._collection()
        if collection is not None:
            try:
                collection.document(key).set(_serialize_value(value), merge=True)
            except Exception as exc:
                import logging
                logging.getLogger("hiresense_api").warning(
                    f"Firestore document.set() failed for '{self.collection_name}/{key}': {exc}"
                )

    def _sync_delete(self, key: str) -> None:
        collection = self._collection()
        if collection is not None:
            try:
                collection.document(key).delete()
            except Exception as exc:
                import logging
                logging.getLogger("hiresense_api").warning(
                    f"Firestore document.delete() failed for '{self.collection_name}/{key}': {exc}"
                )

    def __getitem__(self, key: str) -> Dict[str, Any]:
        if key in self._memory:
            return self._memory[key]
        collection = self._collection()
        if collection is not None:
            try:
                snapshot = collection.document(key).get()
                if snapshot.exists:
                    data = _deserialize_value(snapshot.to_dict() or {})
                    self._memory[key] = data
                    return data
            except Exception as exc:
                import logging
                logging.getLogger("hiresense_api").warning(
                    f"Firestore document.get() failed for '{self.collection_name}/{key}': {exc}"
                )
        raise KeyError(key)

    def __setitem__(self, key: str, value: Dict[str, Any]) -> None:
        self._memory[key] = deepcopy(value)
        self._sync_set(key, value)

    def __delitem__(self, key: str) -> None:
        if key in self._memory:
            del self._memory[key]
        self._sync_delete(key)

    def __iter__(self) -> Iterator[str]:
        self._sync_from_remote()
        return iter(self._memory.keys())

    def __len__(self) -> int:
        self._sync_from_remote()
        return len(self._memory)

    def __contains__(self, key: object) -> bool:
        return key in self._memory

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> Iterable[str]:
        self._sync_from_remote()
        return self._memory.keys()

    def values(self) -> Iterable[Dict[str, Any]]:
        self._sync_from_remote()
        return self._memory.values()

    def items(self) -> Iterable[tuple[str, Dict[str, Any]]]:
        self._sync_from_remote()
        return self._memory.items()

    def clear(self) -> None:
        for key in list(self._memory.keys()):
            self.__delitem__(key)

    def replace_all(self, records: Dict[str, Dict[str, Any]]) -> None:
        self._memory = deepcopy(records)
        collection = self._collection()
        if collection is not None:
            try:
                for key, value in records.items():
                    collection.document(key).set(_serialize_value(value), merge=True)
            except Exception as exc:
                import logging
                logging.getLogger("hiresense_api").warning(
                    f"Firestore replace_all failed for '{self.collection_name}': {exc}"
                )


class FirestoreBackedListStore(MutableMapping[str, List[Dict[str, Any]]]):
    def __init__(self, collection_name: str, seed_data: Optional[Dict[str, List[Dict[str, Any]]]] = None):
        self.collection_name = collection_name
        self._memory: Dict[str, List[Dict[str, Any]]] = deepcopy(seed_data or {})
        self._runtime = build_runtime_state()

    def _client(self):
        runtime = self._runtime
        return runtime.firestore_client if runtime.firestore_ready else None

    def _collection(self):
        client = self._client()
        if client is None:
            return None
        return client.collection(self.collection_name)

    def _sync_from_remote(self) -> None:
        collection = self._collection()
        if collection is None:
            return
        try:
            for snapshot in collection.stream():
                data = snapshot.to_dict() or {}
                items = list(data.get("items", []))
                if snapshot.id:
                    self._memory[snapshot.id] = items
        except Exception as exc:
            import logging
            logging.getLogger("hiresense_api").warning(
                f"Firestore collection.stream() failed for list store '{self.collection_name}': {exc}"
            )
            return

    def __getitem__(self, key: str) -> List[Dict[str, Any]]:
        if key in self._memory:
            return self._memory[key]
        collection = self._collection()
        if collection is not None:
            try:
                snapshot = collection.document(key).get()
                if snapshot.exists:
                    data = snapshot.to_dict() or {}
                    items = list(data.get("items", []))
                    self._memory[key] = items
                    return items
            except Exception as exc:
                import logging
                logging.getLogger("hiresense_api").warning(
                    f"Firestore document.get() failed for list store '{self.collection_name}/{key}': {exc}"
                )
        raise KeyError(key)

    def __setitem__(self, key: str, value: List[Dict[str, Any]]) -> None:
        self._memory[key] = deepcopy(value)
        collection = self._collection()
        if collection is not None:
            try:
                collection.document(key).set({"items": _serialize_value(value)}, merge=True)
            except Exception as exc:
                import logging
                logging.getLogger("hiresense_api").warning(
                    f"Firestore document.set() failed for list store '{self.collection_name}/{key}': {exc}"
                )

    def __delitem__(self, key: str) -> None:
        if key in self._memory:
            del self._memory[key]
        collection = self._collection()
        if collection is not None:
            try:
                collection.document(key).delete()
            except Exception as exc:
                import logging
                logging.getLogger("hiresense_api").warning(
                    f"Firestore document.delete() failed for list store '{self.collection_name}/{key}': {exc}"
                )

    def __iter__(self) -> Iterator[str]:
        self._sync_from_remote()
        return iter(self._memory.keys())

    def __len__(self) -> int:
        self._sync_from_remote()
        return len(self._memory)

    def __contains__(self, key: object) -> bool:
        return key in self._memory

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> Iterable[str]:
        self._sync_from_remote()
        return self._memory.keys()

    def values(self) -> Iterable[List[Dict[str, Any]]]:
        self._sync_from_remote()
        return self._memory.values()

    def items(self) -> Iterable[tuple[str, List[Dict[str, Any]]]]:
        self._sync_from_remote()
        return self._memory.items()
