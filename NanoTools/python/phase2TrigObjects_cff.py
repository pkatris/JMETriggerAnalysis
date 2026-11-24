"""TrigObj table for the Phase-2 HLT menu (HLT:75e33).

Same branch schema as Run-3 NanoAOD (TrigObj_id/pt/eta/phi/filterBits) so that
the Run-3 NanoAnalysis code keeps working, but filterBits are defined from
Phase-2 HLT filter labels.

Jet (TrigObj_id == 1) bit layout, for thresholds T = [t_1 < t_2 < ... < t_N]:
  bit 0      : any hltSingleAK4PFPuppiJet* filter  ("SingleAK4PFPuppiJetX",
               Phase-2 analogue of Run-3 bit 42 "SinglePFJetX")
  bit i>=1   : hltSingleAK4PFPuppiJet<t_i>       (one bit per threshold, so the
               analysis knows *which* threshold an object passed -- Run-3 bit 42
               could not tell)
The layout is also written in the TrigObj_filterBits branch title, and
phase2_filterbitmatch_jme.py reads it from there, so it never has to be
hard-coded in the analysis.
"""
import FWCore.ParameterSet.Config as cms

# AK4 single-jet ladder; 520 is the path shipped in HLT:75e33, the others are
# added by customizePhase2HLTNano.addSingleAK4PFPuppiJetPaths
DEFAULT_SINGLEJET_THRESHOLDS = [40, 60, 80, 110, 140, 200, 260, 320, 400, 450, 500, 520, 550]

TRIGGERJET = 85  # trigger::TriggerObjectType::TriggerJet


def singleJetFilterLabel(threshold):
    return 'hltSingleAK4PFPuppiJet%d' % threshold


def jetQualityBits(thresholds):
    bits = [cms.PSet(filters=cms.vstring('hltSingleAK4PFPuppiJet*'), doc=cms.string('SingleAK4PFPuppiJetX'))]
    for thr in sorted(thresholds):
        bits.append(cms.PSet(filters=cms.vstring(singleJetFilterLabel(thr)),
                             doc=cms.string(singleJetFilterLabel(thr))))
    if len(bits) > 64:
        raise RuntimeError('too many jet thresholds for a 64-bit filterBits word')
    return bits


def makeTrigObjTable(processName, thresholds=DEFAULT_SINGLEJET_THRESHOLDS):
    return cms.EDProducer('Phase2TriggerObjectTableProducer',
        src = cms.InputTag('hltTriggerSummaryAOD', '', processName),
        name = cms.string('TrigObj'),
        selections = cms.VPSet(
            cms.PSet(
                id = cms.int32(1),
                doc = cms.string('Jet'),
                triggerTypes = cms.vint32(TRIGGERJET),
                minPt = cms.double(0.),
                skipObjectsNotPassingQualityBits = cms.bool(True),
                qualityBits = cms.VPSet(*jetQualityBits(thresholds)),
            ),
        ),
    )
