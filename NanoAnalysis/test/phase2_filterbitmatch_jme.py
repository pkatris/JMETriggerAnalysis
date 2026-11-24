#!/usr/bin/env python3
"""Phase-2 dijet tag-and-probe single-jet HLT turn-ons from the Phase-2 NanoAOD
(NTuplizers/test/jmeTriggerNano_cfg.py).

Port of NanoAnalysis/test/filterbitmatch_jme.py (Run-3). Output histogram names
are unchanged (h_pfjet<L>_{den,num,objden,objnum}_<var>), so plot_efficiency.py
and plot_turnon_eta.py run on it as-is; <L> is now the HLT_AK4PFPuppiJet<L>
threshold.

What changes w.r.t. Run-3, and why:
  * Reference ("offline") jets: -r GenJet (default, always present) or -r Jet
    (offline slimmedJetsPuppi, only if the input had MINIAOD).
  * No LumiMask / golden JSON: this is MC.
  * TrigObj_filterBits: bit 0 = any hltSingleAK4PFPuppiJet* object (Run-3 bit 42
    analogue), plus ONE BIT PER THRESHOLD. The bit layout is read from the
    TrigObj_filterBits branch title, nothing is hard-coded here.
  * objnum: probe matched (dR < 0.2) to a TrigObj carrying the bit of THIS
    threshold, i.e. the object really passed hltSingleAK4PFPuppiJet<L>. In
    Run-3 the threshold could only be emulated by cutting on TrigObj_pt.
  * Denominator: in MC there are no prescales and every event is "recorded",
    so by default no reference path and no tag requirement are needed
    (-d all, -t none). -d lowerpath / -t hlt reproduce the Run-3 procedure
    (next lower path, tag matched to a single-jet HLT object) for comparison.

Histogram families per leg <L>:
  _den_     dijet tag-and-probe sample (+ reference path if -d lowerpath)
  _num_     den && HLT_AK4PFPuppiJet<L> fired              (event level)
  _objden_  den && probe matched to any single-jet TrigObj (bit 0)
  _objnum_  den && probe matched to a TrigObj with the <L> bit (object level)
plot_efficiency.py -p obj   -> objnum / den   (recommended)
plot_efficiency.py -p event -> num / den

Usage:
  python3 phase2_filterbitmatch_jme.py -F nano.root -o out/
  python3 phase2_filterbitmatch_jme.py -f filelist -i 3 -o out/   # line 3 of filelist.out
"""
import argparse
import os
import re
from array import array

import ROOT

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
src = parser.add_mutually_exclusive_group(required=True)
src.add_argument("-F", "--file", dest="file", help="input NanoAOD (local, /eos, /store or root://)")
src.add_argument("-f", "--filename", dest="filename", help="file list <filename>.out, used with -i")
parser.add_argument("-i", "--index", dest="index", type=int, default=0, help="line of the file list")
parser.add_argument("-o", "--outputdir", dest="outputdir", default=".")
parser.add_argument("-r", "--ref", dest="ref", default="GenJet", choices=["GenJet", "Jet"],
                    help="reference jet collection standing in for offline jets")
parser.add_argument("-d", "--denominator", dest="denominator", default="all", choices=["all", "lowerpath"],
                    help="all = every dijet event (MC default); lowerpath = Run-3 style, "
                         "event must have fired the next lower HLT_AK4PFPuppiJet path")
parser.add_argument("-t", "--tagcut", dest="tagcut", default="none", choices=["none", "hlt"],
                    help="none = no requirement on the tag (unbiased in MC); hlt = tag matched to a "
                         "single-jet TrigObj, and with -d lowerpath above the reference threshold")
parser.add_argument("--dr", dest="dr", type=float, default=0.2, help="TrigObj-to-jet matching cone")
parser.add_argument("--alpha", dest="alpha", type=float, default=0.1, help="third-jet veto, alpha < this")
parser.add_argument("--mt", dest="mt", action="store_true", help="enable ROOT implicit multithreading")
args = parser.parse_args()

if args.mt:
    ROOT.ROOT.EnableImplicitMT()

PI = ROOT.TMath.Pi()

# JME jet-veto-map eta grid (82 bins), identical to filterbitmatch_jme.py.
# Note: Phase-2 calorimeter geometry differs (HGCAL in the endcaps), so this grid
# is kept only so that Run-3 and Phase-2 maps can be overlaid bin by bin.
ETA_BINS = array('d', [
    -5.191, -4.889, -4.716, -4.538, -4.363, -4.191, -4.013, -3.839, -3.664, -3.489,
    -3.314, -3.139, -2.964, -2.853, -2.650, -2.500, -2.322, -2.172, -2.043, -1.930,
    -1.830, -1.740, -1.653, -1.566, -1.479, -1.392, -1.305, -1.218, -1.131, -1.044,
    -0.957, -0.870, -0.783, -0.696, -0.609, -0.522, -0.435, -0.348, -0.261, -0.174,
    -0.087,  0.000,  0.087,  0.174,  0.261,  0.348,  0.435,  0.522,  0.609,  0.696,
     0.783,  0.870,  0.957,  1.044,  1.131,  1.218,  1.305,  1.392,  1.479,  1.566,
     1.653,  1.740,  1.830,  1.930,  2.043,  2.172,  2.322,  2.500,  2.650,  2.853,
     2.964,  3.139,  3.314,  3.489,  3.664,  3.839,  4.013,  4.191,  4.363,  4.538,
     4.716,  4.889,  5.191])
N_PHI = 72
ETA_REGIONS = array('d', [-5.2, -3.0, -1.3, 1.3, 3.0, 5.2])

M_PT = (100, 0., 1000.)
M_ETA = (100, -5., 5.)
M_PHI = (100, -PI, PI)
M_DPHI = (100, 0., PI)
M_ALPHA = (100, 0., 1.)

BASE_VARS = [
    ("pt_lead", "Lead_jet", M_PT),
    ("pt_tag", "pT_tag", M_PT),
    ("pt_probe", "pT_probe", M_PT),
    ("pt_ave", "pT_ave", M_PT),
    ("pt_sub", "Sub_jet", M_PT),
    ("phi_tag", "tag_jet_phi", M_PHI),
    ("phi_probe", "probe_jet_phi", M_PHI),
    ("eta_tag", "tag_jet_eta", M_ETA),
    ("eta_probe", "probe_jet_eta", M_ETA),
    ("dphi", "Delta_phi", M_DPHI),
    ("alpha", "alpha", M_ALPHA),
]
LEG_VARS = [v for v in BASE_VARS if v[0] in ("pt_probe", "pt_ave", "pt_tag", "eta_probe", "phi_probe")]
PROBE_MATCH_VARS = [
    ("hlt_matched_pt_probe", "probe_hlt_pt", M_PT),
    ("hlt_response_probe", "probe_hlt_response", (100, 0., 2.)),
]

ROOT.gInterpreter.Declare(r"""
#include <cmath>
#include <cstdlib>
namespace p2 {
  inline float dphi(float a, float b) {
    float d = std::abs(a - b);
    return d > M_PI ? 2 * M_PI - d : d;
  }
  inline float dr2(float eta1, float phi1, float eta2, float phi2) {
    const float de = eta1 - eta2, dp = dphi(phi1, phi2);
    return de * de + dp * dp;
  }
  // tag/probe assignment of the two leading jets, as filterbitmatch_jme.py:
  // a barrel (|eta| < 1.3) jet is the tag; random if both or neither are.
  ROOT::RVec<int> tnp(float eta1, float eta2) {
    const bool b1 = std::abs(eta1) < 1.3, b2 = std::abs(eta2) < 1.3;
    int t;
    if (b1 && !b2) t = 0;
    else if (!b1 && b2) t = 1;
    else t = std::rand() % 2;
    return {t, 1 - t};
  }
  // index of the closest jet TrigObj (id 1) within dr carrying any bit of mask, -1 if none
  int matchTrigObj(float eta, float phi,
                   const ROOT::RVec<float>& teta, const ROOT::RVec<float>& tphi,
                   const ROOT::RVec<UShort_t>& tid, const ROOT::RVec<ULong64_t>& tbits,
                   ULong64_t mask, float dr) {
    int best = -1;
    float best2 = dr * dr;
    for (size_t j = 0; j < teta.size(); ++j) {
      if (tid[j] != 1 || (tbits[j] & mask) == 0) continue;
      const float d2 = dr2(eta, phi, teta[j], tphi[j]);
      if (d2 < best2) { best2 = d2; best = int(j); }
    }
    return best;
  }
}
""")


def resolve(path):
    if path.startswith("/store/"):
        return "root://xrootd-cms.infn.it/" + path
    return path


def read_bit_layout(path):
    """{threshold: bit} from the TrigObj_filterBits branch title, plus the 'any' bit."""
    f = ROOT.TFile.Open(path)
    tree = f.Get("Events")
    br = tree.GetBranch("TrigObj_filterBits")
    if not br:
        raise RuntimeError("no TrigObj_filterBits in %s: not a jmeTriggerNano_cfg.py output?" % path)
    title = br.GetTitle()
    branches = set(b.GetName() for b in tree.GetListOfBranches())
    # the table producer writes an empty Jet table when slimmedJetsPuppi is not in
    # the input, so the branch existing is not enough
    ref_filled = ("n" + args.ref) in branches and tree.GetMaximum("n" + args.ref) > 0
    f.Close()
    if not ref_filled:
        raise RuntimeError("reference collection %s is empty in %s (offline Jet needs MINIAOD in the "
                           "HLT input); use -r GenJet" % (args.ref, path))
    any_bit = None
    legs = {}
    for bit, label in re.findall(r"(\d+) => ([A-Za-z0-9_]+)", title):
        bit = int(bit)
        m = re.match(r"hltSingleAK4PFPuppiJet(\d+)$", label)
        if m:
            legs[int(m.group(1))] = bit
        elif label == "SingleAK4PFPuppiJetX":
            any_bit = bit
    if any_bit is None:
        raise RuntimeError("SingleAK4PFPuppiJetX bit not found in TrigObj_filterBits doc: %s" % title)
    return any_bit, legs, branches


def veto_map_model(name):
    h = ROOT.TH2D(name, ";#eta;#phi", len(ETA_BINS) - 1, ETA_BINS, N_PHI, -PI, PI)
    h.SetDirectory(0)
    return ROOT.RDF.TH2DModel(h)


def eta_pt_model(name):
    h = ROOT.TH2D(name, ";#eta;p_{T} [GeV]", len(ETA_REGIONS) - 1, ETA_REGIONS, *M_PT)
    h.SetDirectory(0)
    return ROOT.RDF.TH2DModel(h)


def book_stage(node, prefix, varlist):
    booked = [node.Histo1D((prefix + s, ";" + c + ";entries", n, lo, hi), c) for s, c, (n, lo, hi) in varlist]
    booked.append(node.Histo2D(veto_map_model(prefix + "eta_phi_probe"), "probe_jet_eta", "probe_jet_phi"))
    booked.append(node.Histo2D(eta_pt_model(prefix + "eta_pt_probe"), "probe_jet_eta", "pT_probe"))
    return booked


def analysis(inputfile, outname):
    print("input:", inputfile)
    any_bit, bit_of, branches = read_bit_layout(inputfile)
    R = args.ref
    legs = sorted(thr for thr in bit_of if ("HLT_AK4PFPuppiJet%d" % thr) in branches)
    print("legs (threshold:bit): %s ; any-jet bit %d" % (", ".join("%d:%d" % (t, bit_of[t]) for t in legs), any_bit))

    ANY = "0x%xULL" % (1 << any_bit)
    TO = "TrigObj_eta, TrigObj_phi, TrigObj_id, TrigObj_filterBits"

    df = ROOT.RDataFrame("Events", inputfile)
    df = df.Filter("n%s >= 2" % R, "two reference jets")
    df = (df.Define("Lead_jet", "%s_pt[0]" % R).Define("Sub_jet", "%s_pt[1]" % R)
            .Define("Lead_jet_eta", "%s_eta[0]" % R).Define("Sub_jet_eta", "%s_eta[1]" % R)
            .Define("Lead_jet_phi", "%s_phi[0]" % R).Define("Sub_jet_phi", "%s_phi[1]" % R)
            .Define("Delta_phi", "p2::dphi(Lead_jet_phi, Sub_jet_phi)")
            .Define("alpha", "n%s == 2 ? 0.f : 2.f * %s_pt[2] / (Lead_jet + Sub_jet)" % (R, R))
            .Define("tnp", "p2::tnp(Lead_jet_eta, Sub_jet_eta)")
            .Define("pT_ave", "0.5f * (Lead_jet + Sub_jet)")
            .Define("pT_tag", "%s_pt[tnp[0]]" % R).Define("tag_jet_eta", "%s_eta[tnp[0]]" % R)
            .Define("tag_jet_phi", "%s_phi[tnp[0]]" % R)
            .Define("pT_probe", "%s_pt[tnp[1]]" % R).Define("probe_jet_eta", "%s_eta[tnp[1]]" % R)
            .Define("probe_jet_phi", "%s_phi[tnp[1]]" % R)
            .Define("tag_trig_idx", "p2::matchTrigObj(tag_jet_eta, tag_jet_phi, %s, %s, %g)" % (TO, ANY, args.dr))
            .Define("tag_hlt_pt", "tag_trig_idx >= 0 ? TrigObj_pt[tag_trig_idx] : -1.f")
            .Define("probe_trig_idx", "p2::matchTrigObj(probe_jet_eta, probe_jet_phi, %s, %s, %g)" % (TO, ANY, args.dr))
            .Define("probe_hlt_pt", "probe_trig_idx >= 0 ? TrigObj_pt[probe_trig_idx] : -1.f")
            .Define("probe_hlt_response", "probe_hlt_pt / pT_probe"))

    df_dijet = (df.Filter("Delta_phi > 2.7", "back-to-back")
                  .Filter("alpha < %g" % args.alpha, "third-jet veto")
                  .Filter("abs(Lead_jet_eta) < 1.3 || abs(Sub_jet_eta) < 1.3", "one jet in barrel"))
    if args.tagcut == "hlt":
        df_dijet = df_dijet.Filter("tag_trig_idx >= 0", "tag matched to single-jet TrigObj")

    stages = [("h_", df, BASE_VARS), ("h_dijet_", df_dijet, BASE_VARS)]
    leg_reference = []
    for i, thr in enumerate(legs):
        ref = legs[i - 1] if (args.denominator == "lowerpath" and i > 0) else None
        den = df_dijet
        if ref is not None:
            cut = "HLT_AK4PFPuppiJet%d" % ref
            if args.tagcut == "hlt":
                cut += " && tag_hlt_pt > %d" % ref
            den = den.Filter(cut, "reference HLT_AK4PFPuppiJet%d" % ref)
        num = den.Filter("HLT_AK4PFPuppiJet%d" % thr, "HLT_AK4PFPuppiJet%d" % thr)
        objden = den.Filter("probe_trig_idx >= 0", "probe matched (leg %d)" % thr)
        mask = "0x%xULL" % (1 << bit_of[thr])
        objnum = den.Filter("p2::matchTrigObj(probe_jet_eta, probe_jet_phi, %s, %s, %g) >= 0" % (TO, mask, args.dr),
                            "probe matched to hltSingleAK4PFPuppiJet%d object" % thr)
        stages += [("h_pfjet%d_den_" % thr, den, LEG_VARS),
                   ("h_pfjet%d_num_" % thr, num, LEG_VARS),
                   ("h_pfjet%d_objden_" % thr, objden, LEG_VARS + PROBE_MATCH_VARS),
                   ("h_pfjet%d_objnum_" % thr, objnum, LEG_VARS + PROBE_MATCH_VARS)]
        leg_reference.append("%d:%s" % (thr, "all" if ref is None else str(ref)))

    booked = []
    for prefix, node, varlist in stages:
        booked += book_stage(node, prefix, varlist)

    os.makedirs(args.outputdir, exist_ok=True)
    fout = ROOT.TFile.Open(os.path.join(args.outputdir, outname), "RECREATE")
    for h in booked:
        h.Write()
    ROOT.TNamed("pfjet_leg_reference", ",".join(leg_reference)).Write()
    ROOT.TNamed("pfjet_tagcut", "mode=%s;denominator=%s;ref=%s" % (args.tagcut, args.denominator, R)).Write()
    ROOT.TNamed("trigobj_bits", ",".join("%d:%d" % (t, bit_of[t]) for t in legs) + ";any:%d" % any_bit).Write()
    print("wrote %d histograms to %s" % (len(booked), fout.GetName()))
    df_dijet.Report().Print()
    fout.Close()


if __name__ == "__main__":
    if args.file:
        analysis(resolve(args.file), "output_hist.root")
    else:
        with open(args.filename + ".out") as f:
            files = [l.strip() for l in f if l.strip()]
        analysis(resolve(files[args.index]), "output_hist%d.root" % args.index)
