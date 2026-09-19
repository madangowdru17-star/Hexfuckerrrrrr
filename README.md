# HEX-PROTOCOL Railway Server

Minimal Railway-ready Python API for the APK. It provides only the required key generator, challenge, and activation behavior.

## Defaults

- Generated-key validity: **10 hours**
- Generated-key device limit: **1 device**
- Fixed test key: `HEX-PROTOCOL-GGHU`
- Fixed-key validity: **10 hours**
- Fixed-key device limit: **1 device**
- Device binding: enabled
- Request logging: `requests.log`
- Key storage: `keys.json`

## Deploy to Railway

1. Upload `server.py`, `Dockerfile`, and this README to a GitHub repository.
2. Create a Railway project from that repository.
3. Railway will build the included Dockerfile and provide the `PORT` variable automatically.
4. Copy the resulting Railway HTTPS domain into the APK when using a hosted build.

The server listens on `0.0.0.0` and uses Railway's `PORT` automatically.

## Generate a key

The default generator creates a 10-hour, one-device key:

```bash
curl -X POST 'https://YOUR-RAILWAY-DOMAIN/?action=create' \
  -H 'Content-Type: application/json' \
  -d '{}'
```

You may also explicitly send the defaults:

```bash
curl -X POST 'https://YOUR-RAILWAY-DOMAIN/?action=create' \
  -H 'Content-Type: application/json' \
  -d '{"hours":10,"max_devices":1}'
```

## Generate a custom key

Set any validity period and device limit in the request. For example, this creates a **72-hour key for 3 devices**:

```bash
curl -X POST 'https://YOUR-RAILWAY-DOMAIN/?action=create' \
  -H 'Content-Type: application/json' \
  -d '{"hours":72,"max_devices":3}'
```

You can also use days plus hours:

```bash
curl -X POST 'https://YOUR-RAILWAY-DOMAIN/?action=create' \
  -H 'Content-Type: application/json' \
  -d '{"days":2,"hours":12,"max_devices":5}'
```

The response returns the generated key, calculated expiry time, total hours, and device limit. The same values are enforced during activation.

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

## APK routes

The APK-compatible routes are:

```text
POST https://YOUR-RAILWAY-DOMAIN/?api=challenge
POST https://YOUR-RAILWAY-DOMAIN/?api=activate
```

The APK sends `license_key` and its device identifier. Activation returns the token, lease, expiry, and device-limit fields expected by the login flow.

## Test the fixed key

```bash
curl -X POST 'https://YOUR-RAILWAY-DOMAIN/?api=activate' \
  -H 'Content-Type: application/json' \
  -d '{"license_key":"HEX-PROTOCOL-GGHU","device_pubkey":"test-device-1"}'
```

A second device receives `device limit reached`. The server stores keys and device bindings in `keys.json` and logs request/response records in `requests.log`.

## Important Railway storage note

Railway containers can be recreated. For keys to survive redeploys or restarts, attach a persistent Railway volume and mount it at `/app`; otherwise use this as a test server only.
