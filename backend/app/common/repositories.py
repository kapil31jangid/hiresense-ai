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
    """Now a pure InMemoryStore. Kept name for compatibility."""
    def __init__(self, collection_name: str, seed_data: Optional[Dict[str, Dict[str, Any]]] = None):
        self.collection_name = collection_name
        self._memory: Dict[str, Dict[str, Any]] = deepcopy(seed_data or {})
        self._runtime = build_runtime_state()

    def __getitem__(self, key: str) -> Dict[str, Any]:
        if key in self._memory:
            return self._memory[key]
        raise KeyError(key)

    def __setitem__(self, key: str, value: Dict[str, Any]) -> None:
        self._memory[key] = deepcopy(value)

    def __delitem__(self, key: str) -> None:
        if key in self._memory:
            del self._memory[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._memory.keys())

    def __len__(self) -> int:
        return len(self._memory)

    def __contains__(self, key: object) -> bool:
        return key in self._memory

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> Iterable[str]:
        return self._memory.keys()

    def values(self) -> Iterable[Dict[str, Any]]:
        return self._memory.values()

    def items(self) -> Iterable[tuple[str, Dict[str, Any]]]:
        return self._memory.items()

    def clear(self) -> None:
        self._memory.clear()

    def replace_all(self, records: Dict[str, Dict[str, Any]]) -> None:
        self._memory = deepcopy(records)


class FirestoreBackedListStore(MutableMapping[str, List[Dict[str, Any]]]):
    """Now a pure InMemoryListStore. Kept name for compatibility."""
    def __init__(self, collection_name: str, seed_data: Optional[Dict[str, List[Dict[str, Any]]]] = None):
        self.collection_name = collection_name
        self._memory: Dict[str, List[Dict[str, Any]]] = deepcopy(seed_data or {})
        self._runtime = build_runtime_state()

    def __getitem__(self, key: str) -> List[Dict[str, Any]]:
        if key in self._memory:
            return self._memory[key]
        raise KeyError(key)

    def __setitem__(self, key: str, value: List[Dict[str, Any]]) -> None:
        self._memory[key] = deepcopy(value)

    def __delitem__(self, key: str) -> None:
        if key in self._memory:
            del self._memory[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._memory.keys())

    def __len__(self) -> int:
        return len(self._memory)

    def __contains__(self, key: object) -> bool:
        return key in self._memory

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> Iterable[str]:
        return self._memory.keys()

    def values(self) -> Iterable[List[Dict[str, Any]]]:
        return self._memory.values()

    def items(self) -> Iterable[tuple[str, List[Dict[str, Any]]]]:
        return self._memory.items()
