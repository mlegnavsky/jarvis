"""Read-only capacity basis, house measurement selection and cycle evidence."""
import math


def finite(value):
 if isinstance(value,bool):return None
 try:
  value=float(value)
  return value if math.isfinite(value) else None
 except (ValueError,TypeError,OverflowError):return None


def capacity_basis(configured_ah,soc,reported_kwh=None):
 ah=finite(configured_ah);soc=finite(soc);reported=finite(reported_kwh)
 capacity=round(ah*51.2/1000,3) if ah is not None and 0<ah<=2000 else None
 valid_soc=soc is not None and 0<=soc<=100
 return {'configured_ah':ah,'nominal_voltage_v':51.2,'capacity_kwh':capacity,
         'source':'configured_ah_at_nominal_51_2v','physical_verified':False,
         'reported_capacity_kwh':reported,
         'remaining_kwh':round(capacity*soc/100,5) if capacity is not None and valid_soc else None,
         'above_sale_reserve_kwh':round(capacity*max(0,soc-60)/100,5) if capacity is not None and valid_soc else None,
         'notice':'Výpočet z nastavení měniče při nominálních51,2 V; nejde o měření skutečné kapacity ani zaručené využitelné energie.'}


def house_power(canonical,native,mode):
 canonical=finite(canonical);native=finite(native)
 if canonical is not None and canonical>=0:return canonical
 return native if mode=='Zero Export To CT' and native is not None and native>=0 else None


def cycle_acceptance(proof):
 p=proof if isinstance(proof,dict) else {}
 ha_controlled=p.get('purpose')=='automatic' and p.get('native_power_fence') is False
 verified=bool(p.get('id') and p.get('reason')=='deadline' and p.get('phase')=='complete'
               and all(p.get(k) is True for k in ('observed','stop_verified'))
               and (ha_controlled or p.get('native_expiry_observed') is True)
               and not p.get('conflicts'))
 failed=bool(not ha_controlled and p.get('observed') is True and p.get('id') and p.get('reason')=='deadline' and p.get('phase')=='complete' and p.get('native_expiry_observed') is not True)
 return {'verified':verified,'failed':failed,'sale_id':p.get('id'),'observed':p.get('observed') is True,
         'native_expiry_observed':p.get('native_expiry_observed') is True,
         'stop_verified':p.get('stop_verified') is True,'reason':p.get('reason'),
         'start':p.get('start'),'end':p.get('end'),'purpose':p.get('purpose'),
         'notice':('Prodej a ukončení přes HA potvrzeny měřením.' if ha_controlled else 'Celý cyklus potvrzen měřením.') if verified else 'Celý cyklus zatím není doložen exportem a potvrzeným ukončením.'}
