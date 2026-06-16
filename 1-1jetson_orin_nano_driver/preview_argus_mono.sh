#!/usr/bin/env bash
# IMX296 mono live preview (Argus / ISP path).
# IMX296 is a global-shutter sensor with a single 1456x1088 mode at 60 fps
# (no HDR, no 4K). The pipeline forces GRAY8 so Argus AWB/CCM does not tint a
# mono module pink/magenta. Works for IMX296LLR mono modules (and gives a clean
# grayscale view from a color module).
#
# Usage:  ./preview_argus_mono.sh [duration_seconds]
#   duration_seconds : 0 (default) = continuous preview; >0 = stop after N seconds.
# Env:
#   SENSOR_ID    : 0 (cam0) or 1 (cam1); default 0. Only meaningful with dual overlay.
#   FRAMERATE    : gstreamer framerate fraction; default 60/1.
#   PREVIEW_SINK : override the auto-selected video sink.
set -euo pipefail

DURATION="${1:-0}"
SENSOR_ID="${SENSOR_ID:-0}"
FRAMERATE="${FRAMERATE:-60/1}"
FRAMES_PER_SECOND_NUM="${FRAMERATE%%/*}"
FRAMES_PER_SECOND_DEN="${FRAMERATE##*/}"
PREVIEW_SINK="${PREVIEW_SINK:-}"

SENSOR_MODE=0
OUT_W=1456
OUT_H=1088

if ! [[ "${DURATION}" =~ ^[0-9]+$ ]]; then
	echo "duration_seconds must be a non-negative integer; use 0 for continuous preview" >&2
	exit 2
fi

if [ -z "${PREVIEW_SINK}" ]; then
	if gst-inspect-1.0 nv3dsink >/dev/null 2>&1; then
		PREVIEW_SINK="nv3dsink"
	elif gst-inspect-1.0 nveglglessink >/dev/null 2>&1; then
		PREVIEW_SINK="nveglglessink"
	else
		PREVIEW_SINK="autovideosink"
	fi
fi

NUM_BUFFERS_ARG=()
if [ "${DURATION}" -gt 0 ]; then
	NUM_BUFFERS=$(((DURATION * FRAMES_PER_SECOND_NUM + FRAMES_PER_SECOND_DEN - 1) / FRAMES_PER_SECOND_DEN))
	NUM_BUFFERS_ARG=(num-buffers="${NUM_BUFFERS}")
fi

echo "IMX296 MONO preview: sensor-id=${SENSOR_ID} ${OUT_W}x${OUT_H} framerate=${FRAMERATE} sink=${PREVIEW_SINK}"
echo "  Pipeline forces GRAY8 to drop Argus AWB/CCM color cast on mono sensor."

gst-launch-1.0 -e \
	nvarguscamerasrc sensor-id="${SENSOR_ID}" "${NUM_BUFFERS_ARG[@]}" \
		sensor-mode="${SENSOR_MODE}" \
	! "video/x-raw(memory:NVMM),width=${OUT_W},height=${OUT_H},format=NV12,framerate=${FRAMERATE}" \
	! nvvidconv \
	! "video/x-raw,format=I420,width=${OUT_W},height=${OUT_H},framerate=${FRAMERATE}" \
	! videoconvert \
	! "video/x-raw,format=GRAY8" \
	! videoconvert \
	! "video/x-raw,format=I420" \
	! fpsdisplaysink video-sink="${PREVIEW_SINK}" text-overlay=false sync=false fps-update-interval=1000
