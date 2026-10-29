#!/usr/bin/env bash
# One-time setup. Creates the project-local virtualenv (nothing is installed system-wide) and checks for SUMO.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

say() { printf '\033[1m%s\033[0m\n' "$*"; }

command -v sumo >/dev/null 2>&1 || { echo "SUMO is not installed (need 'sumo' on PATH, version 1.18 or newer). On Ubuntu: sudo apt install sumo sumo-tools"; exit 1; }
say "SUMO: $(sumo --version | head -1)"
export SUMO_HOME="${SUMO_HOME:-/usr/share/sumo}"

if [ ! -d .venv ]; then
  say "Creating .venv (with access to the system SUMO python tools: traci, sumolib)"
  python3 -m venv --system-site-packages .venv
fi
.venv/bin/python -c "import traci, sumolib" 2>/dev/null || { echo "traci/sumolib are not importable. Install them with: .venv/bin/pip install traci sumolib"; exit 1; }
say "Installing python dependencies into .venv"
.venv/bin/pip install -q -r "${1:-requirements-dev.txt}"   # dev file = runtime deps + pytest + playwright (tests, screenshots, video)

# Third-party browser code is vendored in web/vendor (three.js, MIT), so no internet is needed at run time.
[ -f web/vendor/three/three.module.min.js ] || { echo "web/vendor/three is missing"; exit 1; }

say "Self-check: running one simulated minute through the bridge"
.venv/bin/python scripts/smoke_worker.py queue_based | tail -3
say "Setup complete. Start the demo with ./run.sh"
