import os
from CRABClient.UserUtilities import config
config = config()

# === Given by the user ===
name = 'phase2_nano_test'
outputDirName = 'HLT_Phase2NanoProductions'
recoOption = 'default'
# extra jmeTriggerNano_cfg.py options, '+' instead of spaces (e.g. 'l1SeededLadder=True+reco=mixedPF')
nanoOpts = 'reco=' + recoOption
# for jet turn-ons a flat-pT QCD sample is preferable; find it with
#   dasgoclient -query="dataset=/QCD*Flat*14TeV*/Phase2Spring24*/GEN-SIM-DIGI-RAW-MINIAOD"
dataset = '/TT_TuneCP5_14TeV-powheg-pythia8/Phase2Spring24DIGIRECOMiniAOD-PU200_AllTP_140X_mcRun4_realistic_v4-v1/GEN-SIM-DIGI-RAW-MINIAOD'
# =========================

input_file_dir = os.environ['CMSSW_BASE'] + '/src/JMETriggerAnalysis/NTuplizers/test/'

config.section_('General')
config.General.requestName = f'Phase2Nano_{name}_{recoOption}'
config.General.workArea = name
config.General.transferOutputs = True
config.General.transferLogs = True

config.section_('JobType')
config.JobType.pluginName = 'Analysis'
config.JobType.maxMemoryMB = 3000
config.JobType.psetName = 'PSet.py'
config.JobType.allowUndistributedCMSSW = True
config.JobType.scriptExe = 'crabExeNano.sh'
config.JobType.scriptArgs = ['nanoOpts=' + nanoOpts]
config.JobType.inputFiles = [input_file_dir + 'jmeTriggerNTuple_L1Only_cfg.py',
                             input_file_dir + 'jmeTriggerNano_cfg.py']
# the output name comes from PSet.py (out.root); crabExeNano.sh writes the merged NanoAOD there

config.section_('Data')
config.Data.publication = False
config.Data.ignoreLocality = False
config.Data.inputDataset = dataset
config.Data.splitting = 'FileBased'
config.Data.unitsPerJob = 1
config.Data.totalUnits = 1
config.Data.outLFNDirBase = f'/store/user/{os.environ["USER"]}/{outputDirName}/{name}/{recoOption}/'

config.section_('Site')
config.Site.storageSite = 'T3_CH_CERNBOX'
