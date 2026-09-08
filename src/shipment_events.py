"""Shipment events and the copy a customer actually receives."""
from dataclasses import dataclass, field
from typing import Literal, Optional

EventKind = Literal["out_for_delivery", "delivered", "exception"]

# Exceptions the carrier can raise. Only the ones the buyer can act on get a text;
# the rest belong to the support queue, not to a phone at 7am.
ACTIONABLE_EXCEPTIONS = {"address_incomplete", "customer_absent", "customs_hold"}


@dataclass(frozen=True)
class Shipment:
    order_id: str
    tracking_code: str
    phone: str
    store_name: str = "Aster & Fig"


@dataclass(frozen=True)
class ShipmentEvent:
    shipment: Shipment
    kind: EventKind
    reason: Optional[str] = None
    proof_of_delivery_url: Optional[str] = None


@dataclass
class Outgoing:
    """One rendered message plus the id that makes a resend safe to repeat."""

    to: str
    text: str
    order_id: str
    idempotency_key: str
    message_id: Optional[str] = None
    status: Optional[str] = None
    failure: Optional[str] = None
    events: list = field(default_factory=list)


class NotNotifiable(Exception):
    """The event is real but nothing should be sent for it."""


def render(event: ShipmentEvent) -> str:
    s = event.shipment
    if event.kind == "out_for_delivery":
        return (
            f"{s.store_name}: order {s.order_id} is out for delivery today. "
            f"Track it with {s.tracking_code}."
        )
    if event.kind == "delivered":
        line = f"{s.store_name}: order {s.order_id} was delivered."
        if event.proof_of_delivery_url:
            line += f" Photo proof: {event.proof_of_delivery_url}"
        return line
    if event.reason in ACTIONABLE_EXCEPTIONS:
        asks = {
            "address_incomplete": "reply with your apartment or unit number",
            "customer_absent": "reply with a day that works and we will retry",
            "customs_hold": "customs needs your ID number to release the parcel",
        }
        return (
            f"{s.store_name}: delivery of order {s.order_id} is paused - "
            f"{asks[event.reason]} ({s.tracking_code})."
        )
    raise NotNotifiable(f"{event.reason or 'unknown'} is handled by support, not by SMS")


def to_outgoing(event: ShipmentEvent) -> Outgoing:
    """Render an event into a sendable message. Raises NotNotifiable when it is not one."""
    text = render(event)
    suffix = event.reason or event.kind
    return Outgoing(
        to=event.shipment.phone,
        text=text,
        order_id=event.shipment.order_id,
        idempotency_key=f"{event.shipment.tracking_code}:{suffix}",
    )
