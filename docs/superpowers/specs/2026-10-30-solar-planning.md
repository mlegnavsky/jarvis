# Solar timing and continuous hourly history

User asked to join disconnected old graph segments, show a daily dot for best panel sunshine, identify weather locality and use clouds for planning. Frontend-only change; no HA restart, no weather API/key addition, no change to heating or inverter.

Join touching retained-hour intervals with a vertical step between hourly means. Preserve null at genuine missing hours and end; don't invent new measurements or use smoothing that changes energy data.

Panel geometry is fixed by owner: southeast (azimuth135deg fromnorth), tilt45deg. Calculate cosincidence using existing SunCalc for Žitenice50.555N14.156E, abovehorizon only; minute search across selected Prague day includingDST. Gold dot on Sun curve marks best geometric incidence, not predicted watts or guaranteed production peak. In week/month, dots are placed in a separate strip below energy-axis baseline; selectionreadout shows thatdate's time. Year aggregates months so no daily dots there.

Use already fetched Open-Meteo cloud_cover and shortwave_radiation for contextual planning. Radiation is GHI (horizontal W/m²), precedinghourmean, so winning interval is timestamp-1h to timestamp. Displayhour andcloud%, don't convertGHI into panelkW or infercloudmotion/satellitetracking. Actual productionpeak can shift withclouds, diffuse light andlocalshadows. Historicalforecastrows absent remainunavailable, not reconstructed. Forecast visiblynamesŽitenice.

Sources: https://pvpmc.sandia.gov/modeling-guide/1-weather-design-inputs/plane-of-array-poa-irradiance/calculating-poa-irradiance/angle-of-incidence-clone/ and https://open-meteo.com/en/docs/gem-api .

Checks: hourlycontiguity/gap regressions, incidencepeakmax andnightzero, DSTdays, radiationforecastwindow; Chromium daily/weeklymarker/locality plus existinghover/mobile tests. DeploytestedJSwithCAS, updateversionedLovelace resource, verifyhistoricalOct9, per-daymarkers andtomorrowforecastlive.
