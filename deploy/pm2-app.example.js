// Entry for the apps array of the PM2 ecosystem file (e.g. ~/.pm2/ecosystem.config.js).
// uv is called by absolute path because the PM2 daemon does not have ~/.local/bin on its PATH.
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
