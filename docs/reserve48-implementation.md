# Two-day automatic reserve

Approved scope: HA continuously calculates a48 elapsed-hour trajectory from sale end, displays tomorrow and the following civil day, and limits scheduled battery sales automatically. Owner baseline6kWh/day,20SOC points per full night,25% load cushion,20% PV haircut. Native30% floor,20W grid offset,97% surplus and physical protections stay in force.

Implementation: (1) hourly backward required energy plus forward clipped battery simulation; (2) future charge credit bounded by fresh read-only native/BMS current and fresh voltage/temperature; (3) durable complete canonical-day learning, never extrapolate a partial counter; (4)48h explanation and archived inputs; (5) regressions, review, source publication, CAS deployment and live proof.

Unknown forecast fails closed100%; missing charging proof gives zero future charging credit. Weak second day sets at least75%; two weak days at least90%, exceptionally weak100%; hourly deficits may raise these floors. Preserve old learning records as diagnostic history and learn only from a new versioned verified-day collection.
