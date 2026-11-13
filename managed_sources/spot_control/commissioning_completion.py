"""Completion compatibility for explicitly requested maintenance tests only."""
def finish(settings,proof,accepted,now):
 result=dict(settings)
 if not settings.get('verification_resume_auto'):return result
 a=dict(settings.get('auto_verification') or {});result['verification_resume_auto']=False
 if settings.get('requested_automatic') is False:
  result.update(automatic=False);return result
 if accepted is True:
  result.update(automatic=True,inhibited=False);a.update(state='verified',reason='Ověření dokončeno; HA obnovilo automatický provoz.')
 else:
  inconclusive=(proof.get('stop_verified') is True and not proof.get('conflicts') and
   (proof.get('reason') in ('recovery','price','reserve') or proof.get('reason')=='deadline' and proof.get('observed') is not True))
  if a.get('kind')=='battery' and inconclusive:
   result.update(automatic=True,inhibited=False);a.update(state='waiting',not_before=now+1800,reason='Obnova je potvrzená; bateriový důkaz zatím chybí. HA počká na další vhodné podmínky.')
  else:
   result.update(automatic=False,inhibited=True);a.update(state='failed',reason='Ověření neprošlo. Prodej je zastavený; HA provedlo ochrannou obnovu a hlásí chybu.')
 result['auto_verification']=a
 return result
