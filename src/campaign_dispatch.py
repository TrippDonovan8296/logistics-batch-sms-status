"""Turn a batch of shipment events into sent messages with per-message status."""
from typing import Iterable, List

from infrai_client import InfraiError, infrai
from shipment_events import NotNotifiable, Outgoing, ShipmentEvent, to_outgoing


def plan(events: Iterable[ShipmentEvent]):
    """Split a carrier batch into messages to send and events to skip."""
    sending: List[Outgoing] = []
    skipped = []
    for event in events:
        try:
            sending.append(to_outgoing(event))
        except NotNotifiable as why:
            skipped.append((event, str(why)))
    return sending, skipped


def dispatch(sending: Iterable[Outgoing]) -> List[Outgoing]:
    """Send each message, keeping its own outcome on its own record.

    The idempotency key is derived from the tracking code and the event, so
    re-running a batch after a partial run resends nothing twice.
    """
    done = []
    for message in sending:
        try:
            retry_safe = {"Idempotency-Key": message.idempotency_key}
            data = infrai.sms.send({"to": message.to, "body": message.text}, retry_safe)
            message.message_id = data.get("message_id")
            message.status = data.get("status", "queued")
        except InfraiError as rejection:
            # One bad number does not stop the batch; it just carries its reason.
            message.status = "rejected"
            message.failure = rejection.code
        done.append(message)
    return done


def refresh(sent: Iterable[Outgoing]) -> List[Outgoing]:
    """Poll delivery status, and pull the event trail for anything not delivered."""
    updated = []
    for message in sent:
        if message.message_id:
            message.status = infrai.sms.status(message.message_id).get("status")
            if message.status != "delivered":
                message.events = infrai.sms.events(message.message_id).get("events", [])
        updated.append(message)
    return updated
