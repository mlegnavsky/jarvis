"""Prepare exact live views without reserializing the root dashboard."""
import json,sys,yaml
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'managed_sources/spot_control'))
from finance_view import cash_block,offload_cash_blocks
from sale_view import augment_spot,view
root=offload_cash_blocks(Path('/tmp/finishsolar-live-hlavni-prehled.yaml').read_text(),expected=4)
spot=augment_spot(yaml.safe_load(Path('/tmp/finishsolar-live-spot-control-view.yaml').read_text()))
shared=cash_block();shared['grid_options']={'columns':'full'}
outputs={'hlavni-prehled.yaml':root,'solar-cash-summary.yaml':yaml.safe_dump(shared,allow_unicode=True,sort_keys=False),'spot-control-view.yaml':yaml.safe_dump(spot,allow_unicode=True,sort_keys=False),'spot-sales-view.yaml':yaml.safe_dump(view(),allow_unicode=True,sort_keys=False)}
for n,s in outputs.items():Path('/tmp/finishsolar-new-'+n).write_text(s)
print(json.dumps({n:len(s.encode()) for n,s in outputs.items()}))
