## NanoAnalysis: Phase-2 single-jet HLT turn-ons

Dijet tag-and-probe efficiency of the Phase-2 `HLT_AK4PFPuppiJet<T>` paths
(HLT:75e33), measured on MC NanoAOD made with
[NanoTools](../NanoTools/readme.md). It is the Phase-2 port of the Run-3
NanoAnalysis workflow (`filterbitmatch_jme.py` on central JetMET NanoAOD), with the same
histogram names and plotting scripts.

```
RAW (GEN-SIM-DIGI-RAW-MINIAOD)
  └─ NTuplizers/test: jmeTriggerNTuple_L1Only_cfg.py → jmeTriggerNano_cfg.py   (local or CRAB)
       └─ NanoAOD: TrigObj (+per-threshold filterBits), HLT_/L1_ bits, GenJet, HLT jets
            └─ NanoAnalysis/test: submit_phase2.py → phase2_filterbitmatch_jme.py on Condor
                 └─ merge_phase2.py → hadd_phase2/<year>_<tag>_<variant>.root
                      └─ plot_*.py → plots_phase2/<tag>/...
```

### Setup
```shell
cd $CMSSW_BASE/src && cmsenv && scram b -j 8
voms-proxy-init -voms cms -valid 192:00
```

### 1. NanoAOD production (`NTuplizers/test`)
See [NanoTools/readme.md](../NanoTools/readme.md). In short:
```shell
cd $CMSSW_BASE/src/JMETriggerAnalysis/NTuplizers/test
./runNanoLocally.sh 10                 # quick local test -> nano.root
crab submit -c crab_nano_cfg.py        # production: set name, dataset, totalUnits first
```
For turn-ons use flat QCD, e.g.
`/QCD_Pt-15To3000_TuneCP5_Flat_14TeV-pythia8/Phase2Spring24DIGIRECOMiniAOD-PU200_Trk1GeV_140X_mcRun4_realistic_v4-v1/GEN-SIM-DIGI-RAW-MINIAOD`.
About 30% of these events survive the dijet selection. Turn-ons up to the
highest thresholds need O(10k) events. TTbar is not useful here because the
third-jet veto removes almost all of it.

### 2. Analysis (`NanoAnalysis/test`)
Single file, interactively:
```shell
cd $CMSSW_BASE/src/JMETriggerAnalysis/NanoAnalysis/test
python3 phase2_filterbitmatch_jme.py -F /eos/user/<u>/<user>/.../nano.root -o out/
```
All files on HTCondor, one job per NanoAOD file:
```shell
python3 submit_phase2.py -n qcdflat_v1 -d /eos/user/<u>/<user>/HLT_Phase2NanoProductions/phase2_qcd_flat
python3 submit_phase2.py -n qcdflat_v1 -l myfiles.txt              # or an explicit list
python3 submit_phase2.py -n qcdflat_a03 -l myfiles.txt -x "--alpha 0.3" --dry-run
condor_q
```
- **Bookkeeping:** `input/<name>.out` (file list) and `Scr/<name>/` (job script, submit file, logs).
- **Output:** `/eos/user/<u>/<user>/phase2_nano/analysis/<name>/output_hist<i>.root`. Change it with `-o`.
- **Environment:** jobs run in this CMSSW area's environment and read EOS through `root://eosuser.cern.ch`.

Analysis options (pass on Condor with `-x`):

| option | default | meaning |
|---|---|---|
| `-r GenJet\|Jet` | `GenJet` | reference jets; `Jet` (offline) is empty unless MINIAOD was in the HLT input |
| `-d all\|lowerpath` | `all` | denominator: every dijet event (MC has no prescales), or the Run-3 rule (next lower path fired) |
| `-t none\|hlt` | `none` | tag requirement; `hlt` = tag matched to a single-jet HLT object (Run-3 procedure) |
| `--alpha` | `0.1` | third-jet veto, α = 2·pT(jet3)/(pT1+pT2) |
| `--dr` | `0.2` | jet ↔ TrigObj matching cone |

### 3. Merge
```shell
python3 merge_phase2.py -n qcdflat_v1 -t qcdflat                 # reports missing jobs, writes hadd_phase2/2026_qcdflat_A.root
python3 merge_phase2.py -i out/ -t qcdflat                       # from a local output directory
python3 merge_phase2.py -n qcdflat_mixedpf -t qcdflat -v B       # a second variant of the same tag
```
- **File name:** the plotting scripts find their input by the pattern `<YYYY>_<tag>_<letter>.root`.
- **Year and letter are only labels for MC.** Use the letter to put variants side by side, e.g. A = default reco, B = `reco=mixedPF`, C = `l1SeededLadder=True`. They then appear as separate "eras" in overlays and tables.
- **`--year-file`:** also writes `<YYYY>_<tag>.root`, which `plot_year.py` needs.

### 4. Plots
All scripts take `-t <tag> -i hadd_phase2 -o plots_phase2` (those are the defaults for `-i`/`-o`):
```shell
python3 plot_efficiency.py    -t qcdflat -p obj   # turn-on per threshold + overlay, plateau and 99.5% point
python3 plot_turnon_eta.py    -t qcdflat -p obj   # turn-ons per eta region (-HF -HE HB HE HF)
python3 plot_eff_1d_etaphi.py -t qcdflat          # efficiency vs eta and vs phi
python3 plot_etaphi_map.py    -t qcdflat          # eta-phi efficiency maps (no Run-3 veto-map overlay)
python3 plot_year.py          -t qcdflat -y 2026  # |eta|<3 summary, needs merge_phase2.py --year-file
```
`--min-den N` sets the minimum denominator per bin (default 20). Lower it only for small test samples.

Pairings (`-p`):
- **`obj`** (recommended): probe matched to an HLT object carrying the bit of threshold T, divided by the dijet denominator. This is the per-object efficiency of `hltSingleAK4PFPuppiJet<T>`.
- **`event`**: `HLT_AK4PFPuppiJet<T>` fired, divided by the dijet denominator. This includes events where the tag fired the path.

The plotting scripts are copies of the Run-3 ones with these changes, done by `phase2_plotting.py`:
- thresholds read from the `trigobj_bits` entry of the merged file, so 520 and any `jetThresholds` you set are included
- x axis "gen probe jet" or "offline probe jet", depending on `-r`
- header "Phase-2 Simulation Preliminary"
- default directories `hadd_phase2` / `plots_phase2`

The physics code is unchanged.

### What the numbers mean
- **Reference:** with `-r GenJet` the turn-on is against generator-level jet pT. The plateau / 99.5% points therefore include the HLT jet response and resolution. They are not directly comparable to Run-3 offline-jet numbers.
- **Outside the barrel:** check the HLT/gen response there first (`h_pfjet40_objden_hlt_response_probe`, `plot_turnon_eta.py`). A low response shifts the endcap and forward turn-ons to higher pT.
- **Generator weights:** the flat QCD sample is weighted, and histograms are filled unweighted. That is fine for efficiencies in narrow pT bins, but the raw pT spectra are flat, not falling.
- **Not ported:** `plateau.json` holds Run-3 values and is not used by the Phase-2 analysis. `plot_efficiency.py` writes the measured Phase-2 plateaus to `plots_phase2/<tag>/plateau_measured.json`.

### Files
| file | role |
|---|---|
| `phase2_filterbitmatch_jme.py` | analysis (RDataFrame); Phase-2 port of `filterbitmatch_jme.py` |
| `submit_phase2.py` | Condor submission over your NanoAOD files (replaces `submit.py`) |
| `merge_phase2.py` | hadd into the plot-script file pattern (replaces `hadd_condor.py`) |
| `plot_*.py` | Run-3 plotting scripts, adapted as above |
| `phase2_plotting.py` | shared helper for the plotting scripts |
