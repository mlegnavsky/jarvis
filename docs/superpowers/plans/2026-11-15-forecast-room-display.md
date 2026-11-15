# Forecast and room display implementation

Goal: match living-room readings to the child's existing labels and display the existing solar forecast independently of published market prices.

Scope: display only. Preserve the owner's automatic-sale OFF state, battery controls, protection thresholds, heating and private configuration.

- [ ] Add a regression covering a full future day of tilted irradiance, missing/stale/partial forecasts and reserve explanations without market prices.
- [ ] Add a pure forecast reader to power-sun.js: same 10.12 kWp and reference factor 0.8054584854081006 as the installed weather reserve. Draw a separately labelled dashed estimate and expose daily kWh, conservative kWh, peak W/m² and locality/orientation.
- [ ] Expose tomorrow's existing forecast and independent price/reserve states in the collapsed Spoty summary; preserve all current controls.
- [ ] Patch only the two existing living-room labels to the child's custom label configuration, and cache-bust touched resources.
- [ ] Run relevant chart and hub suites, publish scoped source with expected Git HEAD, CAS-deploy without restart, read back exact contents and verify sale remains OFF.

Validation: forecast/chart/hub/DOM tests pass. Desktop/mobile browser execution blocked by environment socket permissions; no visual acceptance claimed. Review addressed solar-axis label overlap; YAML parsed and compared using preserved !include tags. Installed weather backend is intentionally preserved. Deployment scope: static assets and two floorplan labels only.
