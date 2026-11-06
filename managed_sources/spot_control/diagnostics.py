"""Structured, read-only operational evidence, separate from acceptance decisions."""
import copy

def build_diagnostics(body,now):
 settings=body.get('settings') or {};proof=body.get('diagnostic_stop') or body.get('last_stop') or {}
 context=proof.get('failure_context') or proof.get('context') or {};health=context.get('health') or {}
 return {'schema_version':1,'checked_at':now,'version':body.get('version'),
  'owner_requested':bool(body.get('automatic_requested',settings.get('requested_automatic'))),
  'operational':bool(settings.get('automatic')),'inhibited':bool(settings.get('inhibited')),
  'mode':body.get('mode'),'stage':body.get('phase'),'reason':body.get('reason'),'error':body.get('error'),
  'last_stop':{'id':proof.get('id'),'mode':proof.get('mode'),'reason':proof.get('original_reason') or proof.get('reason'),
   'cleanup_reason':proof.get('reason'),'at':proof.get('stopped_at'),'failure':proof.get('failure_detail') or proof.get('error'),
   'stop_verified':proof.get('stop_verified') is True,'observed':proof.get('observed') is True,
   'native_expiry_observed':proof.get('native_expiry_observed') is True,
   'native_power_fence':proof.get('native_power_fence') is True,
   'conflicts':copy.deepcopy(proof.get('conflicts') or {}),'issues':copy.deepcopy(health.get('issues') or []),
   'native_mismatches':copy.deepcopy(context.get('native_mismatches') or [])},
  'health':copy.deepcopy(body.get('health_report') or {}),'selected_block':copy.deepcopy(body.get('selected_block')),
  'completed_blocks':copy.deepcopy(settings.get('completed_blocks') or {}),
  'notice':'Historické ukončení přes HA není důkaz nezávislého nativního časovače.'}
