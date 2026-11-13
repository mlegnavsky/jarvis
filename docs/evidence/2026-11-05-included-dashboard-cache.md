# Included dashboard cache correction

Confirmed against official Home Assistant Core tag2026.6.4 homeassistant/components/lovelace/dashboard.py, LovelaceYAML._load_config: when not forced, cached config is reused based only on os.path.getmtime(self.path), the parent dashboard. Changes to included spot-control-view.yaml alone therefore do not invalidate already cached parent YAML. Earlier exact file readback did not prove served dashboard configuration.

Correction: preserve all existing main dashboard bytes and append a YAML comment to advance its mtime via verified CAS write, so next config fetch reloads includes. Move existing expandable details to second card immediately below Spoty heading. No controller/inverter change or restart. For future included-view changes always refresh the parent dashboard file too, or use an explicitly supported forced Lovelace fetch. Phone visual acceptance still requires a fresh page load; no direct phone verification claimed.
