# Daily graph spacing and solar horizon

Owner requested headroom above curves, tighter lower space, forecast adjacent to graph, and corrected solar placement. Preserves the exact live1.2.2 chart width and HTML after reconciling newer remote backend-only changes; only the chart script gets a fresh cache key.

Power extent reserves8% above and2% below measured range rather than rounding both bounds to a grid interval. SOC and price reserve10 SVG units above/4below. Grid ticks retain round values within that range. Forecast moves after scales and zoom tools, immediately before the plot, with a smaller weather strip. SVG footer shrinks30to24 units.

Solar altitude is still SunCalc at the same coordinates/time. Zero degrees now shares the zero-watt horizon. A single linear degrees scale fits the entire daily solar curve to the asymmetric space above/below that horizon; desktop degree labels derive from that exact mapping. The mobile label explicitly identifies0° as horizon. Never interpret solar degrees as watts.

Observed failing regression for horizon alignment before fix, followed by passing math/render/gesture tests for common horizon, fitted solar bounds, top headroom and forecast order. No inverter settings, sale controller, HA Core restart or physical test required. Exact live static readback is required after CAS deployment; browser pixel acceptance is separate from math/DOM verification.
