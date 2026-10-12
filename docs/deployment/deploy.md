# Deploy and update (vps2, PM2 + NGINX)

> Last updated: 2026-10-12

The app runs as `my-garmin-mcp` under PM2 behind NGINX with TLS, reachable by Claude (including the phone) as a custom connector. Config templates are in the appendix at the end. The real hostname is not kept in the repo; below it is `mcp.example.com`.

## First deploy

1. **DNS:** a record for the hostname pointing at the server (here a CNAME to the server's own name, TTL 300).
2. **Code:** check the project out under `~/app/my-garmin-mcp`, install [uv](https://docs.astral.sh/uv/) (`~/.local/bin/uv`) and run `uv sync --no-dev`.
3. **`.env`** (mode 600, copy from `.env.example`):
   - `MCP_ACCESS_KEY`: the production key, its own (generate with `uv run rotate-key`).
   - `PORT`: a free port (check with `ss -ltn`); must match PM2 and NGINX.
   - `ALLOWED_HOSTS=mcp.example.com`: the SDK rejects Host headers it does not know, so without this NGINX-proxied requests fail.
   - `GARMIN_EMAIL`, `GARMIN_PASSWORD`, `GARMIN_TOKEN_STORE=./data/garmin-tokens`.
4. **Garmin tokens:** the first Garmin call logs in with the credentials and saves tokens in `data/garmin-tokens/garmin_tokens.json`; later calls reuse them. To avoid any login from the server's IP, copy a working token file there instead (`scp`, directory mode 700, file mode 600).
5. **PM2:** add the entry from [Appendix: PM2 entry](#appendix-pm2-entry) to the ecosystem file, then `pm2 start <ecosystem file> --only my-garmin-mcp` and `pm2 save`. Boot persistence needs the PM2 systemd unit (`pm2 startup`, once per server). Check: `curl -s localhost:<PORT>/health`.
6. **NGINX:** install the config from [Appendix: NGINX](#appendix-nginx) with the real hostname, with the rate-limit zone in `conf.d`. First create the certificate with only the port-80 block in place: `sudo certbot certonly --webroot -w /var/www/html -d mcp.example.com`, then add the 443 block, `sudo nginx -t && sudo systemctl reload nginx`. Certbot renews automatically (timer).
7. **Verify from outside:** `/mcp` without a key gives 401, with a wrong key 401, `/health` 404, plain HTTP redirects to HTTPS.
8. **Claude connector:** add a custom connector with URL `https://mcp.example.com/mcp` and the request header `Authorization: Bearer <MCP_ACCESS_KEY>`.

## Update

Push to `origin/main`, then on the server, from the live checkout:

```
~/app/my-garmin-mcp/deploy/update.sh
```

[deploy/update.sh](../../deploy/update.sh) refuses to run anywhere but production, then:

1. Preflight: pm2 runs the app from this checkout and it is online, the checkout is on `main` and clean, `.env` exists, and the commit on `origin/main` is a fast-forward of the live one.
2. Tests: the new commit is checked out into a throwaway git worktree (`~/app/my-garmin-mcp-build/`) with its own virtualenv and the full test suite runs there. If anything is red, the script stops and the live service, checkout and virtualenv are untouched.
3. Go live (seconds of downtime): `pm2 stop`, fast-forward the live checkout, `uv sync --no-dev --locked`, `pm2 start`, then wait for `/health`.
4. If step 3 fails (install error, or no `/health` answer in 30 s) the checkout is reset to the previous commit, the install is redone and the app is started again.

Redeploying the commit that is already live is allowed (it tests and restarts anyway). After changing `.env` only, `pm2 restart my-garmin-mcp` is enough. Logs: `pm2 logs my-garmin-mcp` (login failures, rejected-token cleanup and Garmin pauses are logged there). Rotating the key: `uv run rotate-key`, restart, update the connector header.

## Notes

- The app only listens on 127.0.0.1; NGINX is the only way in, and only `/mcp` is proxied.
- The NGINX logs use the default format, which has no header fields, so the bearer key never reaches a log.
- If Garmin starts rejecting the saved tokens the app deletes them after 3 rejected calls in a row and logs in again with the credentials; a failed login is not retried for 15 minutes.

## Appendix: NGINX

Replace `mcp.example.com` with the real hostname (keep the real one out of the repo). Install as `/etc/nginx/sites-available/<hostname>` (symlink into `sites-enabled`), get the certificate first (first deploy, step 6), then `sudo nginx -t && sudo systemctl reload nginx`.

```nginx
# http context (e.g. /etc/nginx/conf.d/garmin-mcp-ratelimit.conf): per-IP rate limit.
limit_req_zone $binary_remote_addr zone=garmin_mcp:10m rate=10r/s;
limit_req_status 429;

upstream garmin_mcp_backend {
    server 127.0.0.1:3336;   # the PORT given to the app in ecosystem.config.js
    keepalive 16;
}

server {
    listen 80;
    listen [::]:80;
    server_name mcp.example.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name mcp.example.com;

    ssl_certificate     /etc/letsencrypt/live/mcp.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mcp.example.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Default log format: it has no header fields, so the Authorization bearer key is never written.
    access_log /var/log/nginx/garmin-mcp.access.log;
    error_log  /var/log/nginx/garmin-mcp.error.log;

    client_max_body_size 1m;

    # Only the MCP endpoint is exposed (exactly /mcp, no trailing slash); /health stays internal.
    location = /mcp {
        limit_req zone=garmin_mcp burst=20 nodelay;

        proxy_pass http://garmin_mcp_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;

        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_connect_timeout 10s;
    }

    location / {
        return 404;
    }
}
```

## Appendix: PM2 entry

An entry for the `apps` array of the PM2 ecosystem file (for example `~/.pm2/ecosystem.config.js`). uv is called by absolute path because the PM2 daemon does not have `~/.local/bin` on its PATH.

```js
{
  name: "my-garmin-mcp",
  cwd: "/home/<user>/app/my-garmin-mcp",
  script: "/home/<user>/.local/bin/uv",
  args: "run --no-sync python -m my_garmin_mcp",
  interpreter: "none",
  env: {
    PORT: 3336   // pick a free port; must match the NGINX upstream and .env
  },
  max_memory_restart: "300M"
},
```
