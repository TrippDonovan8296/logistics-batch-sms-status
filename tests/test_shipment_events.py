import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from campaign_dispatch import plan  # noqa: E402
from shipment_events import NotNotifiable, Shipment, ShipmentEvent, to_outgoing  # noqa: E402

SHIPMENT = Shipment("A-1043", "1Z9994", "+15551234567")


def test_actionable_exception_asks_the_buyer_for_the_missing_piece():
    out = to_outgoing(ShipmentEvent(SHIPMENT, "exception", reason="address_incomplete"))
    assert "apartment or unit number" in out.text
    assert out.idempotency_key == "1Z9994:address_incomplete"


def test_carrier_delay_is_not_texted():
    with pytest.raises(NotNotifiable):
        to_outgoing(ShipmentEvent(SHIPMENT, "exception", reason="carrier_delay"))


def test_delivered_message_carries_the_proof_link():
    out = to_outgoing(
        ShipmentEvent(SHIPMENT, "delivered", proof_of_delivery_url="https://cdn.example.com/pod/1Z9994.jpg")
    )
    assert "https://cdn.example.com/pod/1Z9994.jpg" in out.text


def test_plan_splits_a_batch_into_sendable_and_skipped():
    sending, skipped = plan(
        [
            ShipmentEvent(SHIPMENT, "out_for_delivery"),
            ShipmentEvent(SHIPMENT, "exception", reason="carrier_delay"),
        ]
    )
    assert [m.order_id for m in sending] == ["A-1043"]
    assert len(skipped) == 1
