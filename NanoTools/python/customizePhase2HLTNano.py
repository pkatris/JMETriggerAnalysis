"""Turn the Phase-2 HLT config (HLT:75e33, e.g. Common/configs/HLT_75e33_D110_cfg.py)
into a job that writes a NanoAOD usable by the Run-3 NanoAnalysis framework.

What it adds, in the same cmsRun process as the HLT (so the HLT products are
still in memory and nothing big is written to disk):

  1. HLT_AK4PFPuppiJet<T> paths for a ladder of thresholds (clones of
     HLT_AK4PFPuppiJet520, only the HLT1PFJet MinPt differs).
  2. L1_<seed> bits mirroring the Phase-2 L1 GT paths (p<seed>), because
     NanoAODOutputModule only writes trigger bits named HLT*/L1*/Flag*.
  3. Flat tables:
       TrigObj_*            HLT objects + filterBits      (phase2TrigObjects_cff)
       hltAK4PuppiJet_*     hltAK4PFPuppiJets            (uncorrected)
       hltAK4PuppiJetCorr_* hltAK4PFPuppiJetsCorrected   (what the filters cut on)
       GenJet_*             ak4GenJetsNoNu
       Jet_*                slimmedJetsPuppi (offline), only if present in input
  4. A NanoAODOutputModule writing those tables plus HLT_*/L1_* bits, replacing
     the FEVTDEBUGHLT EDM output.
"""
import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import Var, P4Vars

from JMETriggerAnalysis.NanoTools.phase2TrigObjects_cff import (
    DEFAULT_SINGLEJET_THRESHOLDS, singleJetFilterLabel, makeTrigObjTable)

REFERENCE_PATH = 'HLT_AK4PFPuppiJet520'
REFERENCE_FILTER = 'hltSingleAK4PFPuppiJet520'
L1SEED_FILTER = 'hltL1SeedsForPuppiJetFilter'


def _insertBeforeFinalPath(process, path):
    """New paths must sit before HLTriggerFinalPath, which runs hltTriggerSummaryAOD."""
    sched = process.schedule
    names = [p.label_() for p in sched]
    idx = names.index('HLTriggerFinalPath') if 'HLTriggerFinalPath' in names else len(sched)
    sched.insert(idx, path)


def addSingleAK4PFPuppiJetPaths(process, thresholds=DEFAULT_SINGLEJET_THRESHOLDS, l1Seeded=False):
    """Clone HLT_AK4PFPuppiJet520 for each threshold.

    l1Seeded=False (default): the new paths run on every event, so the turn-on
    measures the HLT alone. With l1Seeded=True they keep the 520 path's L1 seed
    (pSinglePuppiJet230), and low thresholds are fully L1-limited.
    HLT_AK4PFPuppiJet520 itself is never modified.
    """
    ref = getattr(process, REFERENCE_FILTER)
    for thr in sorted(thresholds):
        pathName = 'HLT_AK4PFPuppiJet%d' % thr
        if hasattr(process, pathName):
            continue
        filt = ref.clone(MinPt = float(thr))
        setattr(process, singleJetFilterLabel(thr), filt)
        seq = process.HLTBeginSequence
        if l1Seeded:
            seq = seq + getattr(process, L1SEED_FILTER)
        seq = (seq + process.HLTRawToDigiSequence + process.HLTLocalrecoSequence
               + process.HLTTICLLocalRecoSequence + process.HLTTrackingSequence
               + process.HLTMuonsSequence + process.HLTParticleFlowSequence
               + process.HLTAK4PFPuppiJetsReconstruction + filt + process.HLTEndSequence)
        path = cms.Path(seq)
        setattr(process, pathName, path)
        _insertBeforeFinalPath(process, path)
    return process


def addL1SeedBits(process):
    """L1_<X> path for every Phase-2 L1 GT path p<X> (cheap PathStatusFilter)."""
    l1paths = [name for name in process.paths_()
               if len(name) > 1 and name[0] == 'p' and name[1].isupper()]
    for name in l1paths:
        bitName = 'L1_' + name[1:]
        if hasattr(process, bitName):
            continue
        mod = cms.EDFilter('PathStatusFilter', logicalExpression = cms.string(name))
        setattr(process, 'l1BitMirror' + name[1:], mod)
        path = cms.Path(mod)
        setattr(process, bitName, path)
        _insertBeforeFinalPath(process, path)
    return process


def _candTable(src, name, cut, doc, extraVars=None):
    variables = cms.PSet(P4Vars)
    if extraVars:
        for k, v in extraVars.items():
            setattr(variables, k, v)
    return cms.EDProducer('SimpleCandidateFlatTableProducer',
        src = cms.InputTag(src),
        name = cms.string(name),
        cut = cms.string(cut),
        doc = cms.string(doc),
        singleton = cms.bool(False),
        extension = cms.bool(False),
        skipNonExistingSrc = cms.bool(True),
        variables = variables,
    )


def addNanoTables(process, thresholds=DEFAULT_SINGLEJET_THRESHOLDS,
                  hltJetPtMin=10., genJetPtMin=10., offlineJetPtMin=15.):
    pname = process.name_()
    process.jmeTrigObjTable = makeTrigObjTable(pname, thresholds)

    process.jmeHltAK4PuppiJetTable = _candTable(
        'hltAK4PFPuppiJets', 'hltAK4PuppiJet', 'pt > %g' % hltJetPtMin,
        'HLT AK4 PUPPI jets, uncorrected (hltAK4PFPuppiJets)')
    process.jmeHltAK4PuppiJetCorrTable = _candTable(
        'hltAK4PFPuppiJetsCorrected', 'hltAK4PuppiJetCorr', 'pt > %g' % hltJetPtMin,
        'HLT AK4 PUPPI jets, JEC applied (hltAK4PFPuppiJetsCorrected, input of the single-jet filters)')
    process.jmeGenJetTable = _candTable(
        'ak4GenJetsNoNu', 'GenJet', 'pt > %g' % genJetPtMin, 'AK4 gen jets (no neutrinos)')
    process.jmeOfflineJetTable = _candTable(
        'slimmedJetsPuppi', 'Jet', 'pt > %g' % offlineJetPtMin,
        'offline AK4 PUPPI jets (slimmedJetsPuppi), written only if present in the input')

    process.jmeNanoTablesTask = cms.Task(
        process.jmeTrigObjTable,
        process.jmeHltAK4PuppiJetTable,
        process.jmeHltAK4PuppiJetCorrTable,
        process.jmeGenJetTable,
        process.jmeOfflineJetTable,
    )
    return process


def addNanoOutput(process, fileName='nano.root', dropEDMOutput=True):
    pname = process.name_()
    process.jmeNanoOutput = cms.OutputModule('NanoAODOutputModule',
        fileName = cms.untracked.string(fileName),
        compressionAlgorithm = cms.untracked.string('LZMA'),
        compressionLevel = cms.untracked.int32(9),
        saveProvenance = cms.untracked.bool(True),
        fakeNameForCrab = cms.untracked.bool(True),
        outputCommands = cms.untracked.vstring(
            'drop *',
            'keep nanoaodFlatTable_jme*Table_*_' + pname,
            # only this process's bits: the input also carries the TriggerResults of
            # the original (sim) HLT process, whose path names would clash
            'keep edmTriggerResults_*_*_' + pname,
        ),
    )
    process.jmeNanoEndPath = cms.EndPath(process.jmeNanoOutput, process.jmeNanoTablesTask)
    if dropEDMOutput:
        edmOutputs = [n for n in process.outputModules_() if n != 'jmeNanoOutput']
        for name in list(process.endpaths_()):
            ep = getattr(process, name)
            if set(ep.moduleNames()) & set(edmOutputs) and ep in process.schedule:
                process.schedule.remove(ep)
        for name in edmOutputs:
            delattr(process, name)
    process.schedule.append(process.jmeNanoEndPath)
    return process


def customizePhase2HLTNano(process, fileName='nano.root',
                           thresholds=DEFAULT_SINGLEJET_THRESHOLDS, l1Seeded=False):
    addSingleAK4PFPuppiJetPaths(process, thresholds, l1Seeded)
    addL1SeedBits(process)
    addNanoTables(process, thresholds)
    addNanoOutput(process, fileName)
    return process
