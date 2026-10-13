# Hosted assessment demo

The optional demo at `https://solar.nickcloud.dev` shares the existing EC2 host with `api.nickcloud.dev`. Nginx routes it to a separate container bound only to `127.0.0.1:8001`; it does not change the existing API's port, container, or virtual host.

## Runtime

- Build the root Dockerfile locally and transfer the resulting image to the host. The private GitHub repository and its credentials do not need to be present on the server.
- Run `deploy/compose.yaml` from `/opt/solar-sites`. Its named Docker volume holds SQLite data across container replacements. `SOLAR_COOKIE_SECURE=1` requires HTTPS for browser sessions.
- The container runs as the unprivileged image user, with a read-only root filesystem, limited memory, no added Linux capabilities, and a localhost-only published port.
- Add a Cloudflare `A` record for `solar` pointing to the existing Elastic IP, initially **DNS only**. Install the bootstrap `deploy/nginx-solar.conf`, validate with `nginx -t`, then obtain a Let's Encrypt certificate with Certbot's nginx integration and HTTPS redirect. Install `deploy/nginx-solar-tls.conf` as the final virtual host, validate it, and reload nginx. Keep the existing `api.nickcloud.dev` configuration untouched.

## Verification

1. `docker compose -f /opt/solar-sites/compose.yaml ps` shows the container healthy.
2. `curl -f http://127.0.0.1:8001/` works on the host.
3. `curl -I https://solar.nickcloud.dev/` returns a successful response after TLS is installed.
4. In a browser, register a fresh account, add a site, view its PVGIS production and battery comparison, then sign out. PVGIS needs outbound internet access.
5. Confirm `https://api.nickcloud.dev/` still serves the existing Cloud Engineering API.

## Operations

To update, save the new tested image under a new tag, update the image tag in `compose.yaml`, and check health before removing the old image. The database stays in the named volume. Back up that volume before a schema-changing release; keep the image and previous tag for rollback. Do not copy the development SQLite database or test accounts into the demo.
