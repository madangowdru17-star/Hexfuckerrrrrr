# HEX custom key API for Railway

Deploy this folder to Railway. It contains a minimal PHP API with custom validity, device limits, and APK-compatible responses. No admin key and no extra authentication are used.

## Deploy

Push the files to GitHub and deploy the repository to Railway. Railway uses the `Dockerfile` and assigns the `PORT` automatically.

The API stores keys in `keys.json`. Railway’s filesystem is temporary unless a Railway volume is attached.

## Generate a key

```bash
curl -X POST 'https://YOUR-RAILWAY-DOMAIN/?action=create' \
  -H 'Content-Type: application/json' \
  -d '{"days":0,"hours":10,"max_devices":1}'
```

Response:

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

## APK routes

The APK calls these root query routes:

```text
POST https://YOUR-RAILWAY-DOMAIN/?api=challenge
POST https://YOUR-RAILWAY-DOMAIN/?api=activate
```

The challenge response contains `nonce`. Activation checks the key, expiry, and device limit, then returns the token fields expected by the APK.

## Manual activation test

```bash
curl -X POST 'https://YOUR-RAILWAY-DOMAIN/?api=activate' \
  -H 'Content-Type: application/json' \
  -d '{"key":"HEX-CHATS-90EA3A62","device_id":"phone-001"}'
```
