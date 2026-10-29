#!/usr/bin/env bash
# Launch the 3dATCS demo server.
#   ./run.sh              start the server on http://localhost:8765
#   ./run.sh --port 9000  other port        ./run.sh --host 0.0.0.0   reachable from other PCs on the network
#   ./run.sh benchmark [--all]   headless full-hour comparison of the three controllers (writes results/benchmark_*.json)
#   ./run.sh test [pytest args]  run the test-suite (add -m "not slow" to skip the one-minute full-hour test)
#   ./run.sh install-browser     download a Chromium (+ffmpeg) into .cache/ for the browser tests, record and screenshots
#   ./run.sh record              record output/backup_demo.webm from the running server (Demo Day backup video)
#   ./run.sh screenshots         regenerate docs/images from the running server
#   ./run.sh perf [args]         measure fps / latency / CPU / memory (scripts/measure_perf.py --help)
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
[ -x .venv/bin/python ] || { echo "Run ./setup.sh first"; exit 1; }
export SUMO_HOME="${SUMO_HOME:-/usr/share/sumo}"

case "${1:-}" in
  benchmark) shift; exec .venv/bin/python -m atcs3d.benchmark "$@" ;;
  test)      shift; exec .venv/bin/python -m pytest "$@" ;;
  install-browser) PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright" exec .venv/bin/playwright install chromium ffmpeg ;;
  record)    shift
             PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright" .venv/bin/playwright install ffmpeg >/dev/null
             exec .venv/bin/python scripts/record_backup_video.py "$@" ;;
  screenshots) shift; exec .venv/bin/python scripts/make_screenshots.py "$@" ;;
  perf)      shift; exec .venv/bin/python scripts/measure_perf.py "$@" ;;
  *)         exec .venv/bin/python -m atcs3d.server "$@" ;;
esac
