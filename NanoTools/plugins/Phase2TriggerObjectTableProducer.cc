// Phase2TriggerObjectTableProducer
//
// Builds the NanoAOD "TrigObj" table (TrigObj_id/pt/eta/phi/filterBits, same
// schema as Run-3 NanoAOD) directly from trigger::TriggerEvent
// (hltTriggerSummaryAOD) of the Phase-2 HLT menu.
//
// Why not PhysicsTools/NanoAOD TriggerObjectTableProducer: that module needs
// pat::TriggerObjectStandAlone (PAT trigger step) *and* hard-requires the
// Run-3 Stage-2 L1 collections (caloStage2Digis, gmtStage2Digis) through
// iEvent.get(), which do not exist in Phase-2 events. This producer has no
// such dependencies and defines filterBits by HLT *filter module labels*
// (glob patterns), e.g. bit k <-> "hltSingleAK4PFPuppiJet520".
//
// Configuration (see JMETriggerAnalysis/NanoTools/python/phase2TrigObjects_cff.py):
//   src         : trigger::TriggerEvent (e.g. "hltTriggerSummaryAOD::HLTX")
//   name        : table name ("TrigObj")
//   selections  : VPSet, one per object family. The FIRST selection an object
//                 satisfies decides its id (as in Run-3 NanoAOD).
//     id               : value stored in TrigObj_id (1 = Jet, like Run-3)
//     doc              : description
//     triggerTypes     : trigger::TriggerObjectType values accepted (85 = TriggerJet)
//     minPt            : pT threshold for storing objects
//     skipObjectsNotPassingQualityBits : store only objects with >= 1 bit set
//     qualityBits      : VPSet {filters = vstring of filter-label globs, doc}
//                        bit index = position in the VPSet (max 64)

#include <algorithm>
#include <cstdint>
#include <regex>
#include <string>
#include <vector>

#include "DataFormats/HLTReco/interface/TriggerEvent.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/EDMException.h"
#include "FWCore/Utilities/interface/RegexMatch.h"

class Phase2TriggerObjectTableProducer : public edm::global::EDProducer<> {
public:
  explicit Phase2TriggerObjectTableProducer(const edm::ParameterSet&);
  void produce(edm::StreamID, edm::Event&, const edm::EventSetup&) const override;
  static void fillDescriptions(edm::ConfigurationDescriptions&);

private:
  struct QualityBit {
    std::vector<std::regex> filters;
  };
  struct Selection {
    uint16_t id;
    std::vector<int> triggerTypes;
    double minPt;
    bool skipObjectsNotPassingQualityBits;
    std::vector<QualityBit> bits;
  };

  static bool labelMatches(std::string_view label, const std::vector<std::regex>& patterns);

  const edm::EDGetTokenT<trigger::TriggerEvent> srcToken_;
  const std::string name_;
  std::vector<Selection> selections_;
  std::string idDoc_;
  std::string bitsDoc_;
};

Phase2TriggerObjectTableProducer::Phase2TriggerObjectTableProducer(const edm::ParameterSet& iConfig)
    : srcToken_(consumes<trigger::TriggerEvent>(iConfig.getParameter<edm::InputTag>("src"))),
      name_(iConfig.getParameter<std::string>("name")) {
  idDoc_ = "ID of the object: ";
  bitsDoc_ = "extra bits of associated information: ";
  for (auto const& sPSet : iConfig.getParameter<std::vector<edm::ParameterSet>>("selections")) {
    Selection sel;
    sel.id = sPSet.getParameter<int>("id");
    sel.triggerTypes = sPSet.getParameter<std::vector<int>>("triggerTypes");
    sel.minPt = sPSet.getParameter<double>("minPt");
    sel.skipObjectsNotPassingQualityBits = sPSet.getParameter<bool>("skipObjectsNotPassingQualityBits");
    const auto doc = sPSet.getParameter<std::string>("doc");
    idDoc_ += std::to_string(sel.id) + " = " + doc + "; ";
    bitsDoc_ += doc + ": ";

    const auto bitPSets = sPSet.getParameter<std::vector<edm::ParameterSet>>("qualityBits");
    if (bitPSets.size() > 64)
      throw cms::Exception("Configuration") << "selection '" << doc << "' has more than 64 qualityBits";
    for (unsigned int i = 0; i < bitPSets.size(); ++i) {
      QualityBit qb;
      for (auto const& pattern : bitPSets[i].getParameter<std::vector<std::string>>("filters"))
        qb.filters.emplace_back(edm::glob2reg(pattern));
      sel.bits.push_back(std::move(qb));
      bitsDoc_ += std::to_string(i) + " => " + bitPSets[i].getParameter<std::string>("doc") + "; ";
    }
    selections_.push_back(std::move(sel));
  }
  produces<nanoaod::FlatTable>();
}

bool Phase2TriggerObjectTableProducer::labelMatches(std::string_view label, const std::vector<std::regex>& patterns) {
  for (auto const& re : patterns)
    if (std::regex_match(label.begin(), label.end(), re))
      return true;
  return false;
}

void Phase2TriggerObjectTableProducer::produce(edm::StreamID, edm::Event& iEvent, const edm::EventSetup&) const {
  edm::Handle<trigger::TriggerEvent> handle;
  iEvent.getByToken(srcToken_, handle);

  std::vector<uint16_t> outId;
  std::vector<float> outPt, outEta, outPhi, outMass;
  std::vector<uint64_t> outBits;

  if (handle.isValid()) {
    const trigger::TriggerEvent& te = *handle;
    const auto& objects = te.getObjects();
    const unsigned int nObj = objects.size();
    const unsigned int nSel = selections_.size();

    // per (selection, object): seen with an accepted trigger type, and its bits
    std::vector<std::vector<char>> seen(nSel, std::vector<char>(nObj, 0));
    std::vector<std::vector<uint64_t>> bits(nSel, std::vector<uint64_t>(nObj, 0));

    for (trigger::size_type f = 0; f < te.sizeFilters(); ++f) {
      const std::string_view label = te.filterLabel(f);
      const auto& keys = te.filterKeys(f);
      const auto& vids = te.filterIds(f);
      for (unsigned int s = 0; s < nSel; ++s) {
        const Selection& sel = selections_[s];
        uint64_t mask = 0;
        for (unsigned int b = 0; b < sel.bits.size(); ++b)
          if (labelMatches(label, sel.bits[b].filters))
            mask |= (uint64_t(1) << b);
        for (unsigned int k = 0; k < keys.size(); ++k) {
          const int type = (k < vids.size()) ? vids[k] : 0;
          if (std::find(sel.triggerTypes.begin(), sel.triggerTypes.end(), type) == sel.triggerTypes.end())
            continue;
          const auto key = keys[k];
          if (key >= nObj)
            continue;
          seen[s][key] = 1;
          bits[s][key] |= mask;
        }
      }
    }

    for (unsigned int i = 0; i < nObj; ++i) {
      for (unsigned int s = 0; s < nSel; ++s) {
        const Selection& sel = selections_[s];
        if (!seen[s][i] || objects[i].pt() < sel.minPt)
          continue;
        if (sel.skipObjectsNotPassingQualityBits && bits[s][i] == 0)
          continue;
        outId.push_back(sel.id);
        outPt.push_back(objects[i].pt());
        outEta.push_back(objects[i].eta());
        outPhi.push_back(objects[i].phi());
        outMass.push_back(objects[i].mass());
        outBits.push_back(bits[s][i]);
        break;  // first matching selection decides the id, as in Run-3 NanoAOD
      }
    }
  }

  auto tab = std::make_unique<nanoaod::FlatTable>(outPt.size(), name_, false, false);
  tab->addColumn<uint16_t>("id", outId, idDoc_);
  tab->addColumn<float>("pt", outPt, "pt", 12);
  tab->addColumn<float>("eta", outEta, "eta", 12);
  tab->addColumn<float>("phi", outPhi, "phi", 12);
  tab->addColumn<float>("mass", outMass, "mass", 10);
  tab->addColumn<uint64_t>("filterBits", outBits, bitsDoc_);
  iEvent.put(std::move(tab));
}

void Phase2TriggerObjectTableProducer::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription bit;
  bit.add<std::vector<std::string>>("filters")->setComment("HLT filter module labels (glob patterns allowed)");
  bit.add<std::string>("doc", "");

  edm::ParameterSetDescription sel;
  sel.add<int>("id");
  sel.add<std::string>("doc", "");
  sel.add<std::vector<int>>("triggerTypes")->setComment("trigger::TriggerObjectType values, e.g. 85 = TriggerJet");
  sel.add<double>("minPt", 0.);
  sel.add<bool>("skipObjectsNotPassingQualityBits", true);
  sel.addVPSet("qualityBits", bit, {});

  edm::ParameterSetDescription desc;
  desc.add<edm::InputTag>("src", edm::InputTag("hltTriggerSummaryAOD"));
  desc.add<std::string>("name", "TrigObj");
  desc.addVPSet("selections", sel, {});
  descriptions.addWithDefaultLabel(desc);
}

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(Phase2TriggerObjectTableProducer);
