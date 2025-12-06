from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, auto
from typing import Any, Optional
from uuid import uuid4


class QueueTopic(Enum):
    NETWORK = auto()
    PRIMARY = auto()
    INDICATOR = auto()


class MessageKind(Enum):
    COMMAND = auto()
    EVENT = auto()
    RESPONSE = auto()


@dataclass(slots=True)
class QueueMessage:
    """
    DTO umum yang lewat antar worker.
    Ini yang benar-benar dimasukkan ke Queue.
    """
    id: str
    topic: QueueTopic
    kind: MessageKind
    payload: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: Optional[str] = None  # buat request–response kalau perlu

    @staticmethod
    def new(
        topic: QueueTopic,
        kind: MessageKind,
        payload: dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> "QueueMessage":
        return QueueMessage(
            id=str(uuid4()),
            topic=topic,
            kind=kind,
            payload=payload,
            correlation_id=correlation_id,
        )
