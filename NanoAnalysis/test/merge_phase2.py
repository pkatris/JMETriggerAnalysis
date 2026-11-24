#!/usr/bin/env python3
"""Merge the output_hist*.root of one Phase-2 production into the file the
plotting scripts read: <hadd dir>/<year>_<tag>_<variant>.root

Phase-2 counterpart of hadd_condor.py. The plotting scripts identify a
"merged era file" by the pattern <YYYY>_<tag>_<one letter>.root. For MC the
year and the letter are only labels: use the letter to keep several variants
of the same tag side by side (e.g. A = default reco, B = mixedPF), they then
show up as separate "eras" in the plots and tables.

  python3 merge_phase2.py -n qcdflat_v1 -t qcdflat                  # Condor output of submit_phase2.py
  python3 merge_phase2.py -i out_qcd -t qcdflat                     # local output directory
  python3 merge_phase2.py -n qcdflat_mixedpf -t qcdflat -v B        # second variant
  python3 merge_phase2.py -n qcdflat_v1 -t qcdflat --year-file      # also <year>_<tag>.root for plot_year.py
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

USER = os.environ.get("USER", "")
DEFAULT_OUTBASE = "/eos/user/%s/%s/phase2_nano/analysis" % (USER[:1], USER)  # as in submit_phase2.py
HERE = os.path.dirname(os.path.abspath(__file__))

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
src = parser.add_mutually_exclusive_group(required=True)
src.add_argument("-n", "--name", help="production name given to submit_phase2.py")
src.add_argument("-i", "--indir", help="any directory containing output_hist*.root")
parser.add_argument("-t", "--tag", required=True, help="tag used by the plotting scripts (-t)")
parser.add_argument("--outbase", default=DEFAULT_OUTBASE, help="as in submit_phase2.py")
parser.add_argument("-o", "--outdir", default="hadd_phase2", help="where the merged file goes")
parser.add_argument("-y", "--year", default="2026", help="4-digit label (plots show <year><variant>)")
parser.add_argument("-v", "--variant", default="A", help="one capital letter")
parser.add_argument("--year-file", action="store_true", help="also write <year>_<tag>.root (plot_year.py)")
args = parser.parse_args()


def main():
    if len(args.year) != 4 or not args.year.isdigit() or len(args.variant) != 1 or not args.variant.isupper():
        sys.exit("--year must be 4 digits and --variant one capital letter (plot-script file pattern)")
    indir = args.indir or os.path.join(args.outbase, args.name)
    inputs = sorted(glob.glob(os.path.join(indir, "output_hist*.root")))
    if not inputs:
        sys.exit("no output_hist*.root in %s" % indir)

    if args.name:  # compare with the number of submitted jobs
        listfile = os.path.join(HERE, "input", args.name + ".out")
        if os.path.isfile(listfile):
            njobs = sum(1 for l in open(listfile) if l.strip())
            have = set(os.path.basename(p) for p in inputs)
            missing = [i for i in range(njobs) if "output_hist%d.root" % i not in have]
            print("%d/%d job outputs present" % (njobs - len(missing), njobs))
            if missing:
                print("missing jobs (check Scr/%s/log/<i>.err): %s" % (args.name, ",".join(map(str, missing))))

    os.makedirs(args.outdir, exist_ok=True)
    target = os.path.join(args.outdir, "%s_%s_%s.root" % (args.year, args.tag, args.variant))
    subprocess.check_call(["hadd", "-f", target] + inputs)
    print("merged %d files -> %s" % (len(inputs), target))
    if args.year_file:
        yfile = os.path.join(args.outdir, "%s_%s.root" % (args.year, args.tag))
        shutil.copyfile(target, yfile)
        print("year file      -> %s" % yfile)
    print("plots: python3 plot_efficiency.py -t %s -i %s" % (args.tag, args.outdir))


if __name__ == "__main__":
    main()
