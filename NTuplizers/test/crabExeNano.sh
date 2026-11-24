#!/bin/bash
# CRAB executable for the Phase-2 NanoAOD chain (crab_nano_cfg.py).
# Same chunking as crabExe.sh (the L1 output is ~100 MB/event, so it is produced
# and consumed in small chunks), but the second step is jmeTriggerNano_cfg.py and
# the chunks are merged with haddnano.py.
set -e

pset_value() {
python3 - "$1" <<'EOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("PSet", "PSet.py")
PSet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PSet)
if sys.argv[1] == 'input':
    print(','.join(PSet.process.source.fileNames))
else:
    print(PSet.process.output.fileName.value())
EOF
}

input_files=$(pset_value input)
out_file=$(pset_value output)
echo "Input files: $input_files"
echo "Output file from PSet: $out_file"

# extra options for jmeTriggerNano_cfg.py (e.g. "l1SeededLadder=True reco=mixedPF"),
# set in crab_nano_cfg.py through config.JobType.scriptArgs = ['nanoOpts=...']
nano_opts=""
for arg in "$@"; do
  case $arg in
    nanoOpts=*) nano_opts="${arg#nanoOpts=}" ;;
  esac
done
nano_opts=${nano_opts//+/ }
echo "Extra NanoAOD options: $nano_opts"

events_per_chunk=5

input_files=$(echo "$input_files" | sed 's#^/store/#root://xrootd-cms.infn.it//store/#')
total_events=$(edmEventSize -v ${input_files%%,*} 2>/dev/null | awk '/Events / {print $NF; exit}')
echo "Total Events: $total_events"

skip=0
chunk_index=0
while [ $skip -lt $total_events ]; do
    echo ">>> Processing chunk: skipEvents=$skip  maxEvents=$events_per_chunk"
    cmsRun jmeTriggerNTuple_L1Only_cfg.py inputFiles=${input_files} \
        skipEvents=$skip maxEvents=$events_per_chunk output=L1_output.root
    cmsRun jmeTriggerNano_cfg.py inputFiles=file:L1_output.root output=nano_chunk_${chunk_index}.root ${nano_opts}
    rm -f L1_output.root
    skip=$((skip + events_per_chunk))
    chunk_index=$((chunk_index + 1))
done

echo "Merging all chunks..."
haddnano.py $out_file nano_chunk_*.root
rm -f nano_chunk_*.root
