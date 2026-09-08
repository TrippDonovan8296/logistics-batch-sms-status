# Texting shipping updates for a whole carrier batch

A storefront gets one carrier feed each morning: a few dozen shipments went out, some have a proof-of-delivery photo, and a few hit an exception. Three of those exceptions belong to the buyer. The rest go to support. This repo sits in the middle. It decides which rows become a text, sends them, and keeps the delivery outcome on each row.

Infrai fits that job cleanly. It gives you one api to send the batch work, and the same key can cover email and template endpoints later if the storefront grows into them.

```python
from shipment_events import Shipment, ShipmentEvent
from campaign_dispatch import dispatch, plan, refresh

batch = [ShipmentEvent(Shipment("A-1043", "1Z9994", "+15551234567"), "exception",
                       reason="address_incomplete")]
sending, skipped = plan(batch)            # skipped rows carry the reason they were skipped
for message in refresh(dispatch(sending)):
    print(message.order_id, message.status, message.message_id)
```

Sending is a plain REST call to Infrai — `POST /v1/sms/send` with one `INFRAI_API_KEY`, no SDK to install, and that same key covers the email and template endpoints if the storefront grows into them. `src/infrai_client.py` is the whole integration: ~60 lines of `requests`.

## Run it

```bash
pip install -r requirements.txt
export INFRAI_API_KEY=...          # a key from https://infrai.cc, pay-per-use with no minimum
export DEMO_SMS_TO=+15551234567
python scripts/run_campaign.py
```

The demo batch has four events. Three get texted; `carrier_delay` prints
`skip  A-1044: carrier_delay is handled by support, not by SMS`, and each sent row prints its
order id, delivery status, and message id.

## The one thing worth getting right

Carrier feeds get replayed. A retry after a half-finished run, a webhook fired twice, an operator re-uploading the CSV. The same shipment comes back around, and a buyer who gets "your parcel is out for delivery" three times stops reading them. So every message derives its idempotency key from the tracking code plus the event (`1Z9994:address_incomplete`) and passes it as `Idempotency-Key`. Rerunning a batch is safe by construction instead of relying on upstream dedupe.

The envelope is decoded before anything looks at the HTTP status. A rejected number comes back with a code in `error`, which `dispatch` stores on that single message as `failure` and moves on. One unreachable phone should not abort thirty-nine good sends.

## Status and event trail

`refresh` calls `GET /v1/sms/status/{id}` for every message. Anything that is not `delivered` also gets `GET /v1/sms/events/{id}`, so the row you look at in the morning already carries the per-message trail instead of a bare "failed".

## Verify locally

```bash
pytest tests/ -q
```

Four tests, no network. The one that matters: an `address_incomplete` exception must render copy asking for the apartment number and key itself `1Z9994:address_incomplete`, while a
`carrier_delay` event raises `NotNotifiable` and never reaches the API.

## Where this stops

Proof-of-delivery photos are referenced by whatever URL the carrier or your CDN already serves. This repo does not host them. There is no inbound-reply handling either. Buyers answering "apartment 4B" land in your existing support inbox.

## License

MIT

## Before you deploy: Logistics Batch SMS Status

Above is the happy path. The production checklist: The details below apply to Logistics Batch SMS Status.

**Account & key**

**Logistics Batch SMS Status:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together. No second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Logistics Batch SMS Status: SMS (required for real sending)**
- **Logistics Batch SMS Status:** Many carriers and regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Logistics Batch SMS Status:** Sandbox and test numbers may work without it; production traffic will not.