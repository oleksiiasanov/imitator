## 1. Installer And System Configuration
- [ ] 1.1 Add required apt packages for NetworkManager AP mode.
- [ ] 1.2 Add installer constants for AP SSID, password, IP, interface, and connection name.
- [ ] 1.3 Create an idempotent `configure_wifi_ap` installer function using `nmcli`.
- [ ] 1.4 Ensure AP configuration is safe to run multiple times.
- [ ] 1.5 Ensure install success output prints SSID, password, and `http://10.42.0.1:8080`.
- [ ] 1.6 Ensure rollback restores files/services where possible without deleting unrelated user Wi-Fi profiles.

## 2. Runtime Diagnostics
- [ ] 2.1 Add AP/NetworkManager status collection to `app.py`.
- [ ] 2.2 Show AP status on `/system`.
- [ ] 2.3 Log AP status at startup.
- [ ] 2.4 Surface clear errors when AP dependencies are missing.

## 3. Documentation
- [ ] 3.1 Update `README.md` first-time instructions to use the AP after install.
- [ ] 3.2 Update `index.html` Quickstart, full guide, FAQ, and diagnostics.
- [ ] 3.3 Update `PROJECT_CONTEXT.md` as single source of truth.
- [ ] 3.4 Update `RELEASE_CHECKLIST.md` for AP validation.
- [ ] 3.5 Update `TEST_PLAN.md` for AP clean install and reboot tests.

## 4. Validation
- [ ] 4.1 Run `bash -n install.sh`.
- [ ] 4.2 Run Python syntax checks.
- [ ] 4.3 Run Flask route smoke tests where possible.
- [ ] 4.4 Validate OpenSpec change.
- [ ] 4.5 Validate AP on real Raspberry Pi hardware after install and reboot.
