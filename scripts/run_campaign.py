"""Run one carrier batch end to end: plan, send, then read status back."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from campaign_dispatch import dispatch, plan, refresh  # noqa: E402
from shipment_events import Shipment, ShipmentEvent  # noqa: E402

TO = os.environ.get("DEMO_SMS_TO")
if not TO:
    raise SystemExit("set DEMO_SMS_TO to a phone number in E.164 form, e.g. +15551234567")

batch = [
    ShipmentEvent(Shipment("A-1041", "1Z9992", TO), "out_for_delivery"),
    ShipmentEvent(
        Shipment("A-1042", "1Z9993", TO),
        "delivered",
        proof_of_delivery_url="https://cdn.asterandfig.com/pod/1Z9993.jpg",
    ),
    ShipmentEvent(Shipment("A-1043", "1Z9994", TO), "exception", reason="address_incomplete"),
    ShipmentEvent(Shipment("A-1044", "1Z9995", TO), "exception", reason="carrier_delay"),
]

sending, skipped = plan(batch)
for event, why in skipped:
    print(f"skip  {event.shipment.order_id}: {why}")

for message in refresh(dispatch(sending)):
    print(f"{message.order_id}  {message.status:<10} {message.message_id or message.failure}")
    for event in message.events:
        print(f"    {event}")
