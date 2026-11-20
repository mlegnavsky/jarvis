import gzip,json,numpy as np
from pathlib import Path
p=Path(__file__).parent;d=json.loads((p/'results.json').read_text() if (p/'results.json').exists() else gzip.decompress((p/'results.json.gz').read_bytes()));r=d['rows'];f=d['fit_stats'];out={'rows':len(r),'fits':len(f),'elapsed_s':d['elapsed_s'],'max_rss_kib':d['max_rss_kib'],'groups':{},'controls':{},'fit_groups':{}}
for dsp in ('linear','gain_down','gain_up','gate_future','agc_all'):
 rr=[z for z in r if z.get('case')=='future' and z.get('dsp')==dsp and (z.get('bootstrap')=='none' or dsp=='agc_all')];hh=[z for z in rr if z.get('human_component_gain') is not None]
 out['groups'][dsp]={'n':len(rr),'echo_attenuation_db':[min(z['echo_attenuation_db'] for z in rr),float(np.median([z['echo_attenuation_db'] for z in rr])),max(z['echo_attenuation_db'] for z in rr)],'guard_bypass':sum(z['guard_bypass'] for z in rr)}
 if hh:out['groups'][dsp].update(human_projection_gain=[min(z['human_projection_gain'] for z in hh),max(z['human_projection_gain'] for z in hh)],human_component_gain=[min(z['human_component_gain'] for z in hh),max(z['human_component_gain'] for z in hh)],max_human_component_error_ratio=max(z['human_component_error_ratio'] for z in hh),human_target_snr_db=[min(z['human_target_snr_db'] for z in hh),max(z['human_target_snr_db'] for z in hh)])
for b in ('none','human_half','human_equal','agc_all'):
 ff=[z for z in f if z['bootstrap']==b];out['fit_groups'][b]={'n':len(ff),'ready':sum(z['ready'] for z in ff),'host_ms':[min(z['elapsed_ms'] for z in ff),float(np.median([z['elapsed_ms'] for z in ff])),max(z['elapsed_ms'] for z in ff)],'validation_error':[min(z['validation_error'] for z in ff),max(z['validation_error'] for z in ff)]}
for c in ('stop_from_start','independent','same_envelope','same_F0_phase','silence','dc'):
 rr=[z for z in r if z['case']==c];out['controls'][c]={'n':len(rr),'ready':sum(z['ready'] for z in rr)}
rr=[z for z in r if z['case']=='future' and z['dsp']=='linear' and z['bootstrap']=='none' and z['split']=='holdout' and z['ratio']==0];out['heldout_linear_echo']={'n':len(rr),'min_attenuation_db':min(z['echo_attenuation_db'] for z in rr),'atleast6db':sum(z['echo_attenuation_db']>=6 for z in rr),'atleast12db':sum(z['echo_attenuation_db']>=12 for z in rr)}
(p/'summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
