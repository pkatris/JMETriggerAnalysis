"""Phase-2 HLT (HLT:75e33) + NanoAOD for the NanoAnalysis framework.

Second step of the usual chain, replacing jmeTriggerNTuple_cfg.py:
    cmsRun jmeTriggerNTuple_L1Only_cfg.py inputFiles=<GEN-SIM-DIGI-RAW-MINIAOD> output=L1_output.root
    cmsRun jmeTriggerNano_cfg.py        inputFiles=file:L1_output.root     output=nano.root

Output branches: TrigObj_*, hltAK4PuppiJet_*, hltAK4PuppiJetCorr_*, GenJet_*,
Jet_* (offline, if in input), HLT_* and L1_* bits.
See JMETriggerAnalysis/NanoTools/python/customizePhase2HLTNano.py.
"""
import FWCore.ParameterSet.VarParsing as vpo
opts = vpo.VarParsing('analysis')

opts.register('skipEvents', 0, vpo.VarParsing.multiplicity.singleton, vpo.VarParsing.varType.int,
              'number of events to be skipped')
opts.register('numThreads', 1, vpo.VarParsing.multiplicity.singleton, vpo.VarParsing.varType.int,
              'number of threads')
opts.register('numStreams', 0, vpo.VarParsing.multiplicity.singleton, vpo.VarParsing.varType.int,
              'number of streams')
opts.register('reco', 'default', vpo.VarParsing.multiplicity.singleton, vpo.VarParsing.varType.string,
              'HLT reconstruction variant: default, trimmedTracking, mixedPF')
opts.register('jetThresholds', '40,60,80,110,140,200,260,320,400,450,500,520,550',
              vpo.VarParsing.multiplicity.singleton, vpo.VarParsing.varType.string,
              'comma-separated HLT_AK4PFPuppiJet<T> thresholds (520 already exists in the menu)')
opts.register('l1SeededLadder', False, vpo.VarParsing.multiplicity.singleton, vpo.VarParsing.varType.bool,
              'seed the added single-jet paths with the L1 seed of HLT_AK4PFPuppiJet520 (pSinglePuppiJet230)')
opts.register('wantSummary', False, vpo.VarParsing.multiplicity.singleton, vpo.VarParsing.varType.bool,
              'show cmsRun summary at job completion')
opts.register('dumpPython', None, vpo.VarParsing.multiplicity.singleton, vpo.VarParsing.varType.string,
              'path to python file with content of cms.Process')
opts.register('output', 'nano.root', vpo.VarParsing.multiplicity.singleton, vpo.VarParsing.varType.string,
              'path to output NanoAOD file')
opts.parseArguments()

###
### base HLT menu
###
from JMETriggerAnalysis.Common.configs.HLT_75e33_D110_cfg import cms, process

if opts.reco == 'trimmedTracking':
  from HLTrigger.Configuration.customizeHLTforTrimmedTracking import customizeHLTforTrimmedTracking
  process = customizeHLTforTrimmedTracking(process)
elif opts.reco == 'mixedPF':
  from HLTrigger.Configuration.customizeHLTforTrimmedTracking import customizeHLTforTrimmedTrackingMixedPF
  process = customizeHLTforTrimmedTrackingMixedPF(process)
elif opts.reco != 'default':
  raise RuntimeError('invalid argument for option "reco": "'+opts.reco+'"')

###
### input
###
if opts.inputFiles:
  process.source.fileNames = opts.inputFiles
  process.source.secondaryFileNames = opts.secondaryInputFiles if opts.secondaryInputFiles else []
else:
  process.source.fileNames = ['file:L1_output.root']
  process.source.secondaryFileNames = []

process.maxEvents.input = opts.maxEvents
process.source.skipEvents = cms.untracked.uint32(opts.skipEvents)

###
### NanoAOD
###
from JMETriggerAnalysis.NanoTools.customizePhase2HLTNano import customizePhase2HLTNano
thresholds = sorted(set(int(t) for t in opts.jetThresholds.split(',') if t.strip()))
process = customizePhase2HLTNano(process, fileName=opts.output,
                                 thresholds=thresholds, l1Seeded=opts.l1SeededLadder)

###
### job options
###
process.options.numberOfThreads = opts.numThreads
process.options.numberOfStreams = opts.numStreams
process.options.wantSummary = opts.wantSummary

if opts.dumpPython is not None:
  open(opts.dumpPython, 'w').write(process.dumpPython())
  print('>>> process dumped to', opts.dumpPython)

print('>>> HLT_AK4PFPuppiJet thresholds :', thresholds, '(L1-seeded)' if opts.l1SeededLadder else '(unseeded)')
print('>>> output NanoAOD               :', opts.output)
