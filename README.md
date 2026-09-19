# Exact `hex_key_api_python` Railway Deployment

This package contains the **same `server.py`** that was tested successfully in Termux. The source file is unchanged; only Railway runs it using the platform `PORT` variable.

## Redeploy correctly

1. Create a new GitHub repository or replace the files in the repository currently deployed on Railway.
2. Upload exactly these files:
   - `server.py`
   - `Dockerfile`
3. In Railway, deploy from that repository.
4. Trigger a new deployment and wait until the deployment is healthy.
5. Do not leave the old PHP service or old deployment connected to the domain.

The Dockerfile starts:

```text
python3 /app/server.py --host 0.0.0.0 --port ${PORT:-10000}
```

## Confirm the deployed service

Replace the domain with your Railway domain:

```bash
curl -X POST 'https://YOUR-RAILWAY-DOMAIN/?api=challenge' \
  -H 'Content-Type: application/json' \
  -d '{}'
```

Expected response:

```json
{"nonce":"..."}
```

Generate a key with the same API used locally:

```bash
curl -X POST 'https://YOUR-RAILWAY-DOMAIN/?action=create' \
  -H 'Content-Type: application/json' \
  -d '{"hours":10,"max_devices":1}'
```

Activate it using the APK-compatible request:

```bash
curl -X POST 'https://YOUR-RAILWAY-DOMAIN/?api=activate' \
  -H 'Content-Type: application/json' \
  -d '{"license_key":"HEX-PROTOCOL-GGHU","device_pubkey":"railway-test-device"}'
```

The APK uses these exact routes:

```text
POST /?api=challenge
POST /?api=activate
```

## Important storage note

`keys.json` and `requests.log` are written inside the container. Attach a Railway volume mounted at `/app` if keys and device bindings must survive container replacement or redeploy.

The APK must be the Railway build configured for:

```text
https://hexfuckerrrrrr-production.up.railway.app
```

Do not use the Termux APK with the Railway server and do not deploy the older PHP package over this service.
