## Phase-2 HLT NanoAOD for the NanoAnalysis framework

Produces a NanoAOD from the Phase-2 HLT menu (`HLT:75e33`) with the branches the
Run-3 NanoAnalysis code (`filterbitmatch_jme.py`) relies on, in particular
`TrigObj_*` with `filterBits` for the `HLT_AK4PFPuppiJet<T>` paths.

The central `NANO:@Phase2HLT` flavour (`HLTrigger/NGTScouting`) has no `TrigObj`
table, and the Run-3 `triggerObjectTable` cannot run on Phase-2 events: it needs
the Stage-2 L1 collections, and its bit patterns (`HLT_PFJet*_v*`, `hltSinglePFJet*`)
do not match Phase-2 names. `Phase2TriggerObjectTableProducer` reads
`hltTriggerSummaryAOD` directly instead.

### Setup
```shell
cd $CMSSW_BASE/src && cmsenv && scram b -j 8
```

### Content of the NanoAOD
| branches | source |
|---|---|
| `TrigObj_id/pt/eta/phi/mass/filterBits` | `hltTriggerSummaryAOD`, jets have `id == 1` |
| `HLT_AK4PFPuppiJet<T>` | 520 from the menu + ladder added by the customization |
| `HLT_*` | all other menu paths |
| `L1_<seed>` | Phase-2 L1 GT decisions (mirrors of the `p<seed>` paths), e.g. `L1_SinglePuppiJet230` |
| `hltAK4PuppiJet_*` | `hltAK4PFPuppiJets` (uncorrected) |
| `hltAK4PuppiJetCorr_*` | `hltAK4PFPuppiJetsCorrected`: what the single-jet filters cut on |
| `GenJet_*` | `ak4GenJetsNoNu`, pT > 10 |
| `Jet_*` | offline `slimmedJetsPuppi`, pT > 15; **empty** unless MINIAOD is in the HLT input |

`TrigObj_filterBits` for jets (layout is also stored in the branch title):

| bit | filter |
|---|---|
| 0 | any `hltSingleAK4PFPuppiJet*` (analogue of Run-3 bit 42 "SinglePFJetX") |
| 1..N | `hltSingleAK4PFPuppiJet<T>`, one per threshold, ascending (default 40 ... 550 → bits 1..13) |

### Workflow
1. **Produce NanoAOD** (`NTuplizers/test`):
   ```shell
   # local: L1 re-emulation + HLT + NANO
   ./runNanoLocally.sh 10                              # 10 events from the default RAW file
   L1_INPUT=file:/eos/user/p/pkatris/output_Phase2_L1.root ./runNanoLocally.sh 50   # reuse an L1 output

   # by hand
   cmsRun jmeTriggerNTuple_L1Only_cfg.py inputFiles=<RAW> maxEvents=10 output=L1_output.root
   cmsRun jmeTriggerNano_cfg.py inputFiles=file:L1_output.root output=nano.root \
          [jetThresholds=40,60,...] [l1SeededLadder=True] [reco=mixedPF] [numThreads=4]

   # CRAB (chunks of 5 events, merged with haddnano.py)
   crab submit -c crab_nano_cfg.py
   ```
   By default the added `HLT_AK4PFPuppiJet<T>` paths are **unseeded**, so the
   turn-on is the HLT alone. With `l1SeededLadder=True` they use the L1 seed of the
   520 path (`pSinglePuppiJet230`); thresholds well below that seed are then
   L1-limited. `HLT_AK4PFPuppiJet520` itself is never changed.

2. **Analyse** (`NanoAnalysis/test`):
   ```shell
   python3 phase2_filterbitmatch_jme.py -F nano.root -o out/                    # MC defaults
   python3 phase2_filterbitmatch_jme.py -F nano.root -o out/ -d lowerpath -t hlt # Run-3-like procedure
   python3 phase2_filterbitmatch_jme.py -f filelist -i 3 -o out/                  # line 3 of filelist.out
   ```
   The histogram names match `filterbitmatch_jme.py`, so the Run-3 plotting scripts
   (`plot_efficiency.py -p obj`, `plot_turnon_eta.py`) work unchanged.

3. **Condor, merging and plots**: see [NanoAnalysis/README.md](../NanoAnalysis/README.md)
   (`submit_phase2.py` → `merge_phase2.py` → `plot_*.py`).
