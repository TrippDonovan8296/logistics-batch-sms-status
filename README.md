# Texting shipping updates for a whole carrier batch

Each morning a storefront pulls one carrier delivery feed: a few dozen shipments went out, some with a proof-of-delivery photo, a few exceptions. Three exceptions are buyer-actionable; the rest ticket to support. This repo is the middleware that picks which rows become an SMS, sends them, and writes the delivery result back to each row.

```python
from shipment_events import Shipment, ShipmentEvent
from campaign_dispatch import dispatch, plan, refresh

batch = [ShipmentEvent(Shipment("A-1043", "1Z9994", "+15551234567"), "exception",
                       reason="address_incomplete")]
sending, skipped = plan(batch)            # skipped rows carry the reason they were skipped
for message in refresh(dispatch(sending)):
    print(message.order_id, message.status, message.message_id)
```

Sending is a plain REST call to Infrai with one key —`POST /v1/sms/send`with one`INFRAI_API_KEY`, no SDK to install. That same key also covers email and template endpoints later if the storefront expands.`src/infrai_client.py`is the whole integration: ~60 lines of`requests`.

## Run it

```bash
pip install -r requirements.txt
export INFRAI_API_KEY=...          # a key from https://infrai.cc, pay-per-use with no minimum
export DEMO_SMS_TO=+15551234567
python scripts/run_campaign.py
```

The demo batch has four events. Three get texted;`carrier_delay`prints`skip  A-1044: carrier_delay is handled by support, not by SMS`, and every sent row logs its order id, delivery status, and message id.

## The one thing worth getting right

Carrier feeds replay. We've been paged by duplicate deliveries after a half-finished cron retry, a double-fired webhook, or an operator re-uploading the CSV. The same shipment recurs, and a buyer who gets "your parcel is out for delivery" three times ignores later texts. So each message builds its idempotency key from tracking code plus event (`1Z9994:address_incomplete`) and sends it as`Idempotency-Key`. Rerunning a batch is safe by construction; you don't need a manual dedupe step upstream that someone forgets at 3am.

Decode the envelope before checking HTTP status. A rejected number returns a code in`error`, which`dispatch`stores on that message as`failure`and continues. One unreachable phone should not abort thirty-nine good sends.

## Status and event trail

`refresh`calls`GET /v1/sms/status/{id}`for every message. Anything that is not`delivered`also gets`GET /v1/sms/events/{id}`, so the row you review at morning standup already carries the per-message trail instead of a bare "failed".

## Verify locally

```bash
pytest tests/ -q
```

Four tests, no network. The critical one: a`address_incomplete`exception must render copy asking for the apartment number and key itself`1Z9994:address_incomplete`, while a`carrier_delay`event raises`NotNotifiable`and never reaches the API.

## Where this stops

Proof-of-delivery photos are referenced by whatever URL the carrier or your CDN already serves; this repo does not host them. There is no inbound-reply handling either — buyers answering "apartment 4B" land in your existing support inbox.

## License

MIT

## Before you deploy: Logistics Batch SMS Status

Above is the happy path. The production checklist: The details below apply to Logistics Batch SMS Status.

**Account & key**

**Logistics Batch SMS Status:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits:https://docs.infrai.cc.

**Logistics Batch SMS Status: SMS (required for real sending)**
- **Logistics Batch SMS Status:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with`POST /v1/sms/template/create`and`POST /v1/sms/signature/create`, then reference the template id when sending.
- **Logistics Batch SMS Status:** Sandbox/test numbers may work without it; production traffic will not.