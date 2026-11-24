#!/bin/bash -e
# Local test of the Phase-2 NanoAOD chain: L1 re-emulation -> HLT:75e33 + NanoAOD.
#   ./runNanoLocally.sh [maxEvents] [skipEvents] [inputFile]
# inputFile: GEN-SIM-DIGI-RAW-MINIAOD (defaults to the one in jmeTriggerNTuple_L1Only_cfg.py).
# Pass an existing L1 output (e.g. file:/eos/user/.../output_Phase2_L1.root) as
# L1_INPUT=<file> to skip the L1 step.

MAXEVENTS=${1:-2}
SKIPEVENTS=${2:-0}
INPUT=${3:-}

if [ -z "${L1_INPUT}" ]; then
  L1ARGS="maxEvents=${MAXEVENTS} skipEvents=${SKIPEVENTS} output=L1_output.root"
  [ -n "${INPUT}" ] && L1ARGS="${L1ARGS} inputFiles=${INPUT}"
  # L1 step (very big output, ~100 MB/event)
  cmsRun jmeTriggerNTuple_L1Only_cfg.py ${L1ARGS}
  L1_INPUT=file:L1_output.root
  NANOARGS="maxEvents=-1"
else
  NANOARGS="maxEvents=${MAXEVENTS} skipEvents=${SKIPEVENTS}"
fi

# HLT step + NanoAOD (TrigObj, HLT/L1 bits, HLT/gen/offline jets)
cmsRun jmeTriggerNano_cfg.py inputFiles=${L1_INPUT} ${NANOARGS} output=nano.root

rm -f L1_output.root
echo "NanoAOD written to nano.root"
