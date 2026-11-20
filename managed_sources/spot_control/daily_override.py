"""Dated business-window exception; never edits recurring policy or devices."""
from datetime import datetime
import re
import math
from zoneinfo import ZoneInfo

try:
    from .native_plan import _quarter_prices, _positive_coverage
except ImportError:
    from native_plan import _quarter_prices, _positive_coverage

TZ = ZoneInfo('Europe/Prague')


def today_override(config, rows, now):
    if config is None:
        return None
    if not isinstance(config, dict) or set(config) != {'date','start','end'}:
        raise ValueError('Invalid one-day override fields')
    today = datetime.fromtimestamp(now,TZ).date().isoformat()
    if config['date'] != today:
        return None
    boundaries = []
    for key in ('start','end'):
        value = config[key]
        if not isinstance(value,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',value):
            raise ValueError('Invalid one-day override time')
        boundaries.append(datetime.fromisoformat(today+'T'+value).replace(tzinfo=TZ).timestamp())
    start,end = boundaries
    if end <= start:
        raise ValueError('One-day override must end after its start')
    if now >= end:
        # Preserve the completed window until midnight. Returning None would
        # silently select a second business block after the owner's deadline.
        return {'start':start,'end':end,'day':today,'block_minutes':(end-start)/60,
                'one_day_override':True,'expired':True,'average_net':None,'net':None,
                'reason':'Dnešní jednorázový plán je ukončený.'}
    coverage_start=max(start,now)
    prices=_quarter_prices(rows)
    if not _positive_coverage(prices,coverage_start,math.nextafter(end,-math.inf)):
        raise ValueError('One-day override requires complete positive future prices')
    relevant=[r for r in rows if r['start']<end and r['end']>coverage_start]
    weights=[min(r['end'],end)-max(r['start'],coverage_start) for r in relevant]
    average=sum(r['net']*w for r,w in zip(relevant,weights))/sum(weights)
    return {'start':start,'end':end,'day':today,'block_minutes':(end-start)/60,
            'average_net':average,'net':average,'one_day_override':True,
            'reason':'Jednorázový dnešní plán na výslovný pokyn majitele.',
            'assumptions':{'timezone':'Europe/Prague','all_quarters_positive':True,
                           'average_basis':'remaining_interval'}}
