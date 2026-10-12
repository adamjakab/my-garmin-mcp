#!/usr/bin/env bash
# Update the production install on vps2: fetch the new commit, prove it in a build
# directory of its own (own virtualenv, full test suite), and only when that is green
# stop the service, fast-forward the live checkout, install, and start it again.
#
# One rule: NOTHING IS CHANGED UNDER A LIVE PROCESS UNTIL THE NEW COMMIT HAS PASSED.
# The tests run in a throwaway git worktree, so a red test run leaves the live
# checkout, its virtualenv and the running service exactly as they were. Downtime is
# only the stop -> merge -> install -> start window (seconds). If that window fails
# (install error, or the app does not answer /health), the live checkout is reset to
# the commit it was on and the service is started again.
#
# Run it from the live checkout on vps2:   ~/app/my-garmin-mcp/deploy/update.sh
# It deploys origin/main, so push first. PRODUCTION ONLY: it refuses to run on any
# other host.
#
# The whole body is a function, called on the last line: `git merge` replaces this very
# file while it runs, and bash reads a script incrementally, so a half-read file would
# execute garbage. A function is parsed completely before it starts. Its variables are
# deliberately global: the EXIT trap runs after main has returned and still needs them.

set -euo pipefail

main() {
	PRODUCTION_HOST="vps2"
	APP_NAME="${APP_NAME:-my-garmin-mcp}"      # the pm2 app, not the repository
	REMOTE_NAME="${REMOTE_NAME:-origin}"
	BRANCH_NAME="${BRANCH_NAME:-main}"
	LIVE="${LIVE:-${HOME}/app/my-garmin-mcp}"  # what pm2 runs from
	BUILD_ROOT="${HOME}/app/my-garmin-mcp-build"
	HEALTH_WAIT_SECONDS=30

	if [[ "$#" -ne 0 ]]; then
		echo "Usage: deploy/update.sh"
		echo "Deploys ${REMOTE_NAME}/${BRANCH_NAME} to ${LIVE} on ${PRODUCTION_HOST}, and nowhere else."
		echo
		echo "Environment:"
		echo "  APP_NAME=${APP_NAME}   the pm2 app to restart"
		echo "  REMOTE_NAME=${REMOTE_NAME}      the git remote to pull from"
		echo "  BRANCH_NAME=${BRANCH_NAME}        the branch to deploy"
		exit 2
	fi

	say() { echo "[${APP_NAME}] $*"; }
	fail() { echo "[${APP_NAME}] $*" >&2; exit 1; }

	# pm2 and uv are often not on PATH in a non-interactive shell (pm2 lives under nvm).
	for dir in "${HOME}/.local/bin" "$(ls -d "${HOME}"/.nvm/versions/node/*/bin 2>/dev/null | sort -V | tail -1)"; do
		[[ -n "${dir}" && -d "${dir}" && ":${PATH}:" != *":${dir}:"* ]] && PATH="${dir}:${PATH}"
	done
	export PATH

	BEFORE="" TARGET="" BUILD="" PORT=""
	ARMED=0          # set the moment the service is stopped; cleared once it is healthy again

	# --- Cleanup and rollback ----------------------------------------------------
	cleanup() {
		local code=$?
		if [[ "${code}" -ne 0 && "${ARMED}" -eq 1 ]]; then
			# Best effort and loud: each step may fail without stopping the rest.
			echo >&2
			say "FAILED after the service was stopped, putting ${BEFORE:0:7} back" >&2
			if [[ "$(git -C "${LIVE}" rev-parse HEAD)" != "${BEFORE}" ]]; then
				git -C "${LIVE}" reset --hard "${BEFORE}" >&2 || say "  rollback: git reset failed" >&2
			fi
			(cd "${LIVE}" && uv sync --no-dev --locked >&2) || say "  rollback: uv sync failed" >&2
			pm2 start "${APP_NAME}" >&2 || say "  rollback: pm2 start failed, the app is DOWN" >&2
			say "Rolled back: ${LIVE} is on ${BEFORE:0:7} again. Check: pm2 logs ${APP_NAME}" >&2
		fi
		if [[ -n "${BUILD}" && -d "${BUILD}" ]]; then
			git -C "${LIVE}" worktree remove --force "${BUILD}" >/dev/null 2>&1 || rm -rf "${BUILD}"
			git -C "${LIVE}" worktree prune >/dev/null 2>&1 || true
		fi
		# Only an empty folder goes (rmdir refuses otherwise), so a build that is still running is never touched.
		rmdir "${BUILD_ROOT}" 2>/dev/null || true
		exit "${code}"
	}
	trap cleanup EXIT

	# --- Preflight: everything that can refuse the update refuses it here --------
	[[ "$(hostname -s)" == "${PRODUCTION_HOST}" ]] \
		|| fail "This is $(hostname -s), not ${PRODUCTION_HOST}. deploy/update.sh only ever runs on production."

	for tool in git uv pm2 curl python3; do
		command -v "${tool}" >/dev/null 2>&1 || fail "${tool} is not on PATH."
	done

	[[ -d "${LIVE}/.git" ]] || fail "${LIVE} is not a git checkout."
	[[ -f "${LIVE}/.env" ]] || fail "${LIVE}/.env is missing: the app has no access key or Garmin credentials."

	# pm2 must run the app from the live checkout, be online, and know its port.
	PM2_INFO="$(pm2 jlist 2>/dev/null | python3 -c '
import json, sys
app = next((p for p in json.load(sys.stdin) if p["name"] == sys.argv[1]), None)
if app:
    env = app.get("pm2_env", {})
    print(env.get("pm_cwd", ""))
    print(env.get("status", ""))
    print(env.get("PORT", ""))
' "${APP_NAME}")" || true
	[[ -n "${PM2_INFO}" ]] || fail "pm2 knows no app named ${APP_NAME}. Set APP_NAME, or start it first."
	{ read -r PM2_CWD; read -r PM2_STATUS; read -r PORT; } <<<"${PM2_INFO}"
	[[ "$(realpath "${PM2_CWD}")" == "$(realpath "${LIVE}")" ]] \
		|| fail "pm2 runs ${APP_NAME} from \"${PM2_CWD}\", not ${LIVE}."
	[[ "${PM2_STATUS}" == "online" ]] \
		|| fail "${APP_NAME} is ${PM2_STATUS}, not online. Refusing to start something that was stopped on purpose."
	[[ "${PORT}" =~ ^[0-9]+$ ]] || fail "pm2 has no numeric PORT for ${APP_NAME} (set it in the ecosystem file); cannot health check."

	[[ "$(git -C "${LIVE}" symbolic-ref --short HEAD)" == "${BRANCH_NAME}" ]] \
		|| fail "${LIVE} is not on ${BRANCH_NAME}."
	# A dirty tree is refused rather than carried: the merge below would fail on it or hide the edit.
	[[ -z "$(git -C "${LIVE}" status --porcelain)" ]] \
		|| fail "${LIVE} has uncommitted changes. Commit, stash or remove them first."

	# --- Fetch and prove the new commit, out of the way --------------------------
	say "Fetching ${REMOTE_NAME}/${BRANCH_NAME}"
	git -C "${LIVE}" fetch --quiet "${REMOTE_NAME}" "${BRANCH_NAME}"
	TARGET="$(git -C "${LIVE}" rev-parse FETCH_HEAD)"
	BEFORE="$(git -C "${LIVE}" rev-parse HEAD)"
	git -C "${LIVE}" merge-base --is-ancestor "${BEFORE}" "${TARGET}" \
		|| fail "${REMOTE_NAME}/${BRANCH_NAME} (${TARGET:0:7}) does not contain the live commit ${BEFORE:0:7}: not a fast-forward."
	if [[ "${BEFORE}" == "${TARGET}" ]]; then
		say "Already at ${TARGET:0:7}, testing and restarting it anyway"
	else
		say "Deploying ${BEFORE:0:7} -> ${TARGET:0:7}"
		git -C "${LIVE}" --no-pager log --oneline "${BEFORE}..${TARGET}"
	fi

	mkdir -p "${BUILD_ROOT}"
	BUILD="${BUILD_ROOT}/$(date -u +%Y%m%dT%H%M%SZ)-${TARGET:0:7}"
	git -C "${LIVE}" worktree add --detach "${BUILD}" "${TARGET}" >/dev/null

	(
		cd "${BUILD}"
		say "  [test] Installing locked dependencies (with dev tools) in ${BUILD}"
		uv sync --locked --quiet
		say "  [test] Running the test suite"
		uv run --no-sync pytest -q
	) || fail "Tests failed for ${TARGET:0:7}. Nothing was changed: the live service is untouched."

	say "${TARGET:0:7} is green"

	# --- Go live ------------------------------------------------------------------
	say "Stopping pm2 app: ${APP_NAME}"
	pm2 stop "${APP_NAME}" >/dev/null
	ARMED=1

	if [[ "${BEFORE}" != "${TARGET}" ]]; then
		say "Fast-forwarding ${LIVE}"
		git -C "${LIVE}" merge --ff-only --quiet "${TARGET}"
	fi
	say "Installing production dependencies"
	(cd "${LIVE}" && uv sync --no-dev --locked --quiet)

	say "Starting pm2 app: ${APP_NAME}"
	pm2 start "${APP_NAME}" >/dev/null

	waited=0
	until curl -fs -m 3 "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; do
		waited=$((waited + 1))
		[[ "${waited}" -le "${HEALTH_WAIT_SECONDS}" ]] \
			|| fail "${APP_NAME} did not answer on http://127.0.0.1:${PORT}/health within ${HEALTH_WAIT_SECONDS}s."
		sleep 1
	done
	ARMED=0

	VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "${LIVE}/pyproject.toml" | head -1)"
	say "Healthy on port ${PORT}. Update completed: ${BEFORE:0:7} -> ${TARGET:0:7}"
	say "You have now deployed version ${VERSION:-unknown}."
}

main "$@"; exit $?
