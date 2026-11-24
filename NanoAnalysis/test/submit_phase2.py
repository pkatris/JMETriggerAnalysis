#!/usr/bin/env python3
"""Run phase2_filterbitmatch_jme.py on HTCondor, one job per Phase-2 NanoAOD file.

Phase-2 counterpart of submit.py. Differences: the input is your own NanoAOD
(CRAB output on EOS, or any list of files) instead of a DAS NANOAOD dataset,
there is no -e era (no lumi mask in MC), the job runs in this CMSSW area's
environment, and the output goes to your own EOS area.

  # all *.root below a CRAB output directory (only that directory is walked)
  python3 submit_phase2.py -n qcdflat_v1 \\
      -d /eos/user/p/pkatris/HLT_Phase2NanoProductions/phase2_qcd_flat
  # or an explicit list, one file per line (/eos/..., /store/..., root://...)
  python3 submit_phase2.py -n qcdflat_v1 -l myfiles.txt
  # extra analysis options, and look before submitting
  python3 submit_phase2.py -n qcdflat_a03 -l myfiles.txt -x "--alpha 0.3" --dry-run

Writes input/<name>.out and Scr/<name>/{run.sh,condor.submit,log/}; job i
writes <outbase>/<name>/output_hist<i>.root. Merge with merge_phase2.py.
"""
import argparse
import os
import subprocess
import sys

USER = os.environ.get("USER", "")
DEFAULT_OUTBASE = "/eos/user/%s/%s/phase2_nano/analysis" % (USER[:1], USER)
EOS_XROOTD = "root://eosuser.cern.ch/"
HERE = os.path.dirname(os.path.abspath(__file__))
PAYLOAD = "phase2_filterbitmatch_jme.py"

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
src = parser.add_mutually_exclusive_group(required=True)
src.add_argument("-d", "--dir", help="directory with the NanoAOD files (e.g. a CRAB output dir); walked recursively")
src.add_argument("-l", "--list", help="text file with one NanoAOD path per line")
parser.add_argument("-n", "--name", required=True, help="production name: input/<name>.out, Scr/<name>, <outbase>/<name>")
parser.add_argument("-o", "--outbase", default=DEFAULT_OUTBASE, help="EOS base directory for the job output")
parser.add_argument("-x", "--extra", default="", help='extra phase2_filterbitmatch_jme.py options, e.g. "--alpha 0.3 -d lowerpath -t hlt"')
parser.add_argument("--maxruntime", type=int, default=7200, help="seconds per job (+MaxRuntime)")
parser.add_argument("--memory", type=int, default=2000, help="request_memory in MB")
parser.add_argument("--dry-run", action="store_true", help="write everything but do not condor_submit")
args = parser.parse_args()


def find_files(top):
    found = []
    for root, dirs, files in os.walk(top):
        dirs[:] = [d for d in dirs if d != "log"]          # CRAB log tarballs
        found += [os.path.join(root, f) for f in files if f.endswith(".root")]
    return sorted(found)


def to_url(path):
    """What the job opens: EOS through xrootd (works on the batch nodes), rest unchanged."""
    path = path.strip()
    if path.startswith("/eos/"):
        return EOS_XROOTD + path
    return path                              # /store/... is resolved by the payload, root:// as is


def main():
    if not os.environ.get("CMSSW_BASE"):
        sys.exit("run cmsenv first: the jobs use this CMSSW area's environment")
    if not args.outbase.startswith("/eos/"):
        sys.exit("--outbase must be on /eos (the job copies its output there with xrdcp)")

    listfile = os.path.join(HERE, "input", args.name + ".out")
    scr = os.path.join(HERE, "Scr", args.name)
    if os.path.exists(listfile):
        sys.exit("input/%s.out already exists: choose another --name or remove it" % args.name)

    files = find_files(args.dir) if args.dir else [l.strip() for l in open(args.list) if l.strip() and not l.startswith("#")]
    if not files:
        sys.exit("no input files found")
    os.makedirs(os.path.dirname(listfile), exist_ok=True)
    with open(listfile, "w") as f:
        f.write("\n".join(to_url(p) for p in files) + "\n")

    outdir = os.path.join(args.outbase, args.name)
    os.makedirs(os.path.join(scr, "log"), exist_ok=True)

    run_sh = os.path.join(scr, "run.sh")
    with open(run_sh, "w") as f:
        f.write("""#!/bin/bash
# job $1 of %(name)s: line $1 of %(name)s.out -> output_hist$1.root
set -e
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd %(cmssw)s/src && eval $(scramv1 runtime -sh)
cd ${_CONDOR_SCRATCH_DIR}
[ -n "${X509_USER_PROXY}" ] && voms-proxy-info -timeleft || true
python3 %(payload)s -f %(name)s -i $1 -o . %(extra)s
xrdcp -f --path output_hist$1.root %(xrd)s%(outdir)s/output_hist$1.root
""" % dict(name=args.name, cmssw=os.environ["CMSSW_BASE"], payload=PAYLOAD,
           extra=args.extra, xrd=EOS_XROOTD, outdir=outdir))
    os.chmod(run_sh, 0o755)

    # a grid proxy is only needed for /store/ inputs; EOS uses the job's Kerberos token
    proxy = os.environ.get("X509_USER_PROXY", "/tmp/x509up_u%d" % os.getuid())
    needs_proxy = any(p.startswith("/store/") for p in files)
    if needs_proxy and not os.path.isfile(proxy):
        sys.exit("inputs are on /store/: run voms-proxy-init -voms cms first")

    sub = os.path.join(scr, "condor.submit")
    with open(sub, "w") as f:
        f.write("universe              = vanilla\n")
        f.write("executable            = %s\n" % run_sh)
        f.write("arguments             = $(ProcId)\n")
        f.write("transfer_input_files  = %s, %s\n" % (os.path.join(HERE, PAYLOAD), listfile))
        f.write("should_transfer_files = YES\n")
        f.write("when_to_transfer_output = ON_EXIT\n")
        if needs_proxy:
            f.write("x509userproxy         = %s\n" % proxy)
        f.write("request_memory        = %d\n" % args.memory)
        f.write("+MaxRuntime           = %d\n" % args.maxruntime)
        f.write("output                = %s/log/$(ProcId).out\n" % scr)
        f.write("error                 = %s/log/$(ProcId).err\n" % scr)
        f.write("log                   = %s/log/$(ProcId).log\n" % scr)
        f.write("queue %d\n" % len(files))

    print("%d input files -> input/%s.out" % (len(files), args.name))
    print("job script     -> Scr/%s/run.sh" % args.name)
    print("output         -> %s/output_hist<i>.root" % outdir)
    if args.dry_run:
        print("dry run: submit with  mkdir -p %s && condor_submit %s" % (outdir, sub))
        return
    os.makedirs(outdir, exist_ok=True)
    subprocess.check_call(["condor_submit", sub])
    print("then: python3 merge_phase2.py -n %s -t <tag>" % args.name)


if __name__ == "__main__":
    main()
