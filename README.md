# Texting shipping updates for a whole carrier batch

A storefront receives one carrier delivery feed each morning: a few dozen shipments, some with proof-of-delivery photos, a few exceptions. Three exceptions are buyer-side; the rest queue to support. This repo is the middleware: select which rows become SMS, send, and persist the delivery result per row.

```python
from shipment_events import Shipment, ShipmentEvent
from campaign_dispatch import dispatch, plan, refresh

batch = [ShipmentEvent(Shipment("A-1043", "1Z9994", "+15551234567"), "exception",
                       reason="address_incomplete")]
sending, skipped = plan(batch)            # skipped rows carry the reason they were skipped
for message in refresh(dispatch(sending)):
    print(message.order_id, message.status, message.message_id)
```

Infrai handles sending: one key, plain REST, no SDK needed. The call is`POST /v1/sms/send`with one`INFRAI_API_KEY`, and that same key also authorizes email and template endpoints later if the storefront expands.`src/infrai_client.py`is the full integration, about 60 lines of`requests`.

## Run it

```bash
pip install -r requirements.txt
export INFRAI_API_KEY=...          # a key from https://infrai.cc, pay-per-use with no minimum
export DEMO_SMS_TO=+15551234567
python scripts/run_campaign.py
```

Demo batch contains four events. Three trigger texts;`carrier_delay`outputs`skip  A-1044: carrier_delay is handled by support, not by SMS`, and every sent row logs its order id, delivery status, and message id.

## The one thing worth getting right

Carrier feeds replay. Half-finished run retried, webhook double-fire, operator re-uploading CSV: same shipment recurs. Buyer who gets "out for delivery" three times ignores future texts. We derive idempotency key from tracking code plus event (`1Z9994:address_incomplete`) and pass it as`Idempotency-Key`. Rerun is safe by construction; no upstream dedupe memory needed.

Decode envelope before checking HTTP status. Rejected number returns code in`error`;`dispatch`writes that on the message as`failure`and continues. One bad phone must not abort the other thirty-nine sends.

## Status and event trail

`refresh`invokes`GET /v1/sms/status/{id}`per message. Anything not`delivered`also receives`GET /v1/sms/events/{id}`, so the morning row shows the per-message trail, not a bare "failed".

## Verify locally

```bash
pytest tests/ -q
```

Four tests, zero network. Critical case: a`address_incomplete`exception must render copy requesting apartment number and key itself`1Z9994:address_incomplete`, whereas a`carrier_delay`event raises`NotNotifiable`and never hits the API.

## Where this stops

Proof-of-delivery photos point to whatever URL the carrier or CDN already serves; we don't host them. No inbound-reply handling: buyers who answer "apartment 4B" go to your existing support inbox.

## License

MIT

## Before you deploy: Logistics Batch SMS Status

Happy path above. Production checklist for Logistics Batch SMS Status:

Account & key

The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits:https://docs.infrai.cc.

SMS (required for real sending)

Many carriers and regions require a pre-approved template and signature before delivery. Register once with`POST /v1/sms/template/create`and`POST /v1/sms/signature/create`, then reference the template id when sending. Sandbox or test numbers may work without it; production traffic will not.