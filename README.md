# HEX custom key API

Minimal PHP API for Railway. No admin key and no extra authentication.

## Deploy

Upload this folder to GitHub and deploy the repository to Railway. Railway detects the `Dockerfile` and starts PHP on the assigned `PORT`.

The API stores keys in `keys.json`. Railway’s filesystem is normally temporary; use a Railway volume if keys must survive redeploys.

## Generate a key

```bash
curl -X POST https://YOUR-RAILWAY-DOMAIN/?action=create \
  -H 'Content-Type: application/json' \
  -d '{"days":0,"hours":10,"max_devices":1}'
```

Example response:

```json
{
    "ok": true,
    "key": "HEX-CHATS-90EA3A62",
    "validity": "10 Hours",
    "expires_at": "2026-09-20 00:37:08",
    "max_devices": 1,
    "hours": 10
}
```

The key prefix is `HEX-CHATS-` followed by eight random hexadecimal characters.

## Validity examples

```json
{"days":2,"hours":0,"max_devices":2}
{"days":1,"hours":6,"max_devices":1}
{"days":0,"hours":10,"max_devices":1}
```

## Activate and bind a device

```bash
curl -X POST 'https://YOUR-RAILWAY-DOMAIN/?action=activate' \
  -H 'Content-Type: application/json' \
  -d '{"key":"HEX-CHATS-90EA3A62","device_id":"phone-001"}'
```

The first activation binds the device. A new device is rejected after `max_devices` is reached. The same device may activate again until the key expires.
