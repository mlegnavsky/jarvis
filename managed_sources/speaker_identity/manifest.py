"""Automatically refreshed operational evidence; never copies identity vectors."""
import hashlib
import json
from pathlib import Path

def build_manifest(report,sources,previous,observed_at,wake_slots):
 revision=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest()
 history=(previous or {}).get('change_history',[])
 if not isinstance(history,list):history=[]
 history=[{k:x[k] for k in ('source_revision','observed_at','runtime_version') if k in x}
          for x in history[-29:] if isinstance(x,dict)]
 if not history or history[-1].get('source_revision')!=revision:
  history.append({'source_revision':revision,'observed_at':observed_at,'runtime_version':report.get('runtime_version')})
 return {'schema':1,'scope':'observed_runtime_not_authentication_guarantee','updated_at':observed_at,
  'repository':'mlegnavsky/jarvis','branch':'feat/jarvis-addon','runtime_version':report.get('runtime_version'),
  'source_revision':revision,'source_files':sources,'change_history':history,
  'runtime':{'status':report.get('status'),'authorization':report.get('authorization',{}),'adaptation':report.get('adaptation',{}),'owner_calibration':report.get('owner_calibration',{})},
  'requested_words':{'wake':'Aničko','lights':['rozsviť','zhasni'],'entrance_lock':['zamkni','odemkni']},
  'wake_slots':wake_slots,'targets':{'lights':'microphone_effective_area','lock':'lock.vstup_zamek_vchod'},
  'verification':{'household_accuracy_verified':False,'replay_detection':'not_installed',
                  'wake_models':'requires_firmware_and_household_acceptance','short_command':'longer_explicit_confirmation'},
  'procedures':{'admin':{'entity_id':'jarvis.system','service':'jarvis.admin','read':{'action':'read','query':'file','target':'jarvis_workspace/voice-system-manifest.json'}},
   'owner_calibration_control':'jarvis_workspace/speaker_identity/calibration-control.json',
   'owner_calibration_policy':'authenticated admin file_write; fresh single-use start; 5 samples/600s; unreviewed collection only; no profile promotion',
   'speaker_report':'jarvis_workspace/speaker_identity/report.json','output_report':'jarvis_workspace/homepod_output/report.json',
   'diagnostics':'jarvis_workspace/voice_diagnostics/report.json','runtime_source':'custom_components/jarvis_speaker_identity',
   'recovery_source':'jarvis_workspace/voice_release/files','deployment':'lease -> revision-bound prepare -> backed-up apply -> verified job -> live report -> release',
   'completion':'queued/running/accepted/file_written are not active_verified; never replay unknown with a new request_id'},
  'privacy':{'raw_audio_saved':False,'embeddings_in_manifest':False}}

def refresh_manifest(path,report,source_roots,observed_at,wake_slots):
 path=Path(path);previous=None;sources={}
 if path.exists() and path.stat().st_size<=128000:
  try:previous=json.loads(path.read_text())
  except (OSError,ValueError):pass
 for root in source_roots:
  root=Path(root)
  for source in sorted(root.glob('*.py')):
   if not source.is_symlink():sources[root.name+'/'+source.name]=hashlib.sha256(source.read_bytes()).hexdigest()
 manifest=build_manifest(report,sources,previous,observed_at,wake_slots)
 path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2));tmp.chmod(0o600);tmp.replace(path)
 return manifest['source_revision']
