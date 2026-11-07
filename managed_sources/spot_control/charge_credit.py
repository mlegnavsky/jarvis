"""Read-only future charging allowance; unknown evidence earns no credit."""
import math

def charge_limit(registers,captured_at,now,voltage,temperature):
 def valid(v):return type(v) in (int,float) and math.isfinite(v)
 if not all(valid(v) for v in (captured_at,now,voltage,temperature)):return 0
 if not 0<=now-captured_at<=90 or not 44<=voltage<=60 or not 5<=temperature<=45:return 0
 limits=[registers.get(k) for k in (108,212,218)]
 if any(type(v) is not int or not 0<v<=500 for v in limits):return 0
 return min(6,min(175,200,*limits)*voltage/1000)
