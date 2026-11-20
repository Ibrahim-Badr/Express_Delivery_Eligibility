from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List

from src.infra.abstractions.message_broker import OrderMessageBroker

logger = logging.getLogger(__name__)


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


class RabbitMQOrderBroker(OrderMessageBroker):
    """RabbitMQ adapter implementing OrderMessageBroker using the community Pika client."""

    def __init__(self, url: str, queue_name: str = "live_orders") -> None:
        self.url = url
        self.queue_name = queue_name

    def publish_order(self, order_data: Dict[str, Any]) -> None:
        import pika  # type: ignore[import-not-found]

        connection: Any = None
        try:
            connection = pika.BlockingConnection(pika.URLParameters(self.url))
            channel = connection.channel()
            channel.queue_declare(queue=self.queue_name, durable=True)
            body = json.dumps(order_data, default=_json_default).encode("utf-8")
            channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
            )
        finally:
            if connection is not None and connection.is_open:
                connection.close()

    def consume_orders(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        import pika  # type: ignore[import-not-found]

        messages: List[Dict[str, Any]] = []
        connection: Any = None
        try:
            connection = pika.BlockingConnection(pika.URLParameters(self.url))
            channel = connection.channel()
            channel.queue_declare(queue=self.queue_name, durable=True)
            for _ in range(max_messages):
                method_frame, _, body = channel.basic_get(
                    queue=self.queue_name, auto_ack=True
                )
                if method_frame is None or body is None:
                    break
                payload = json.loads(body.decode("utf-8"))
                if isinstance(payload, dict):
                    messages.append(payload)
            return messages
        except Exception as exc:
            logger.warning("RabbitMQ consume failed: %s", exc)
            return messages
        finally:
            if connection is not None and connection.is_open:
                connection.close()
