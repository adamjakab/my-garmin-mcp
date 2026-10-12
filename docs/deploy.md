# Deploy and update (vps2, PM2 + NGINX)

The app runs as `my-garmin-mcp` under PM2 behind NGINX with TLS, reachable by Claude (including the phone) as a custom connector. Templates: [deploy/nginx.conf.example](../deploy/nginx.conf.example) and [deploy/pm2-app.example.js](../deploy/pm2-app.example.js). The real hostname is not kept in the repo; below it is `mcp.example.com`.

## First deploy

1. **DNS:** a record for the hostname pointing at the server (here a CNAME to the server's own name, TTL 300).
2. **Code:** check the project out under `~/app/my-garmin-mcp`, install [uv](https://docs.astral.sh/uv/) (`~/.local/bin/uv`) and run `uv sync --no-dev`.
3. **`.env`** (mode 600, copy from `.env.example`):
   - `MCP_ACCESS_KEY`: the production key, its own (generate with `uv run rotate-key`).
   - `PORT`: a free port (check with `ss -ltn`); must match PM2 and NGINX.
   - `ALLOWED_HOSTS=mcp.example.com`: the SDK rejects Host headers it does not know, so without this NGINX-proxied requests fail.
   - `GARMIN_EMAIL`, `GARMIN_PASSWORD`, `GARMIN_TOKEN_STORE=./data/garmin-tokens`.
4. **Garmin tokens:** the first Garmin call logs in with the credentials and saves tokens in `data/garmin-tokens/garmin_tokens.json`; later calls reuse them. To avoid any login from the server's IP, copy a working token file there instead (`scp`, directory mode 700, file mode 600).
5. **PM2:** add the entry from `deploy/pm2-app.example.js` to the ecosystem file, then `pm2 start <ecosystem file> --only my-garmin-mcp` and `pm2 save`. Boot persistence needs the PM2 systemd unit (`pm2 startup`, once per server). Check: `curl -s localhost:<PORT>/health`.
6. **NGINX:** install the template with the real hostname, with the rate-limit zone in `conf.d`. First create the certificate with only the port-80 block in place: `sudo certbot certonly --webroot -w /var/www/html -d mcp.example.com`, then add the 443 block, `sudo nginx -t && sudo systemctl reload nginx`. Certbot renews automatically (timer).
7. **Verify from outside:** `/mcp` without a key gives 401, with a wrong key 401, `/health` 404, plain HTTP redirects to HTTPS.
8. **Claude connector:** add a custom connector with URL `https://mcp.example.com/mcp` and the request header `Authorization: Bearer <MCP_ACCESS_KEY>`.

## Update

```
cd ~/app/my-garmin-mcp && git pull && uv sync --no-dev && pm2 restart my-garmin-mcp
```

After changing `.env` only the restart is needed. Logs: `pm2 logs my-garmin-mcp` (login failures, rejected-token cleanup and Garmin pauses are logged there). Rotating the key: `uv run rotate-key`, restart, update the connector header.

## Notes

- The app only listens on 127.0.0.1; NGINX is the only way in, and only `/mcp` is proxied.
- The NGINX logs use the default format, which has no header fields, so the bearer key never reaches a log.
- If Garmin starts rejecting the saved tokens the app deletes them after 3 rejected calls in a row and logs in again with the credentials; a failed login is not retried for 15 minutes.
