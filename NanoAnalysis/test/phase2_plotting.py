"""Helpers shared by the Phase-2 copies of the NanoAnalysis plotting scripts.

The Run-3 scripts hard-code the HLT_PFJet thresholds and label the x axis
"offline probe jet". phase2_filterbitmatch_jme.py stores both pieces of
information in its output (TNamed "trigobj_bits" and "pfjet_tagcut"), so the
Phase-2 copies read them from the merged files instead.
"""
import glob
import os

import ROOT

DEFAULT_LEGS = [40, 60, 80, 110, 140, 200, 260, 320, 400, 450, 500, 520, 550]
REF_LABELS = {"GenJet": "gen probe jet", "Jet": "offline probe jet"}


def merged_files(indir, tag):
    """<YYYY>_<tag>_<L>.root and <YYYY>_<tag>.root files in indir (not empty)."""
    paths = glob.glob(os.path.join(indir, "*_%s_?.root" % tag)) + \
        glob.glob(os.path.join(indir, "*_%s.root" % tag))
    return sorted(p for p in paths if os.path.getsize(p) >= 1000)


def _named(indir, tag, key):
    for path in merged_files(indir, tag):
        f = ROOT.TFile.Open(path)
        obj = f.Get(key) if f else None
        title = obj.GetTitle() if obj else None
        if f:
            f.Close()
        if title:
            return title
    return None


def legs_from_files(indir, tag, fallback=DEFAULT_LEGS):
    """Thresholds from "trigobj_bits" ("40:1,60:2,...;any:0"), else fallback."""
    title = _named(indir, tag, "trigobj_bits")
    if not title:
        print("phase2_plotting: no trigobj_bits in %s for tag %s, using default legs" % (indir, tag))
        return list(fallback)
    legs = sorted(int(item.split(":")[0]) for item in title.split(";")[0].split(",") if item)
    print("phase2_plotting: legs from file: %s" % ",".join(str(l) for l in legs))
    return legs


def ref_label(indir, tag):
    """x-axis label of the probe jet, from "pfjet_tagcut" ("mode=..;denominator=..;ref=GenJet")."""
    title = _named(indir, tag, "pfjet_tagcut") or ""
    fields = dict(kv.split("=", 1) for kv in title.split(";") if "=" in kv)
    return REF_LABELS.get(fields.get("ref"), "probe jet")
