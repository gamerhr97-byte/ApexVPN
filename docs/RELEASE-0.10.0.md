# Shadow Box 0.10.0

- UTF-8-sig preference/import reads, matching atomic UTF-8 writes; Persian paths survive Windows locale defaults.
- Validated complete form autosave, with core/ports/language/Windows actions and imported batches explicitly saved. Network edits can be persisted during an active session; the active Engine snapshot, ports and recovery lease are retained until reconnect. Advanced drafts are not silently committed by unrelated autosaves.
- Default-on .ir policy migrated once for existing users, with subsequent opt-out preserved. Validated WinINET suffix/apex bypass plus Xray direct routing; exact previous-proxy restoration remains required.
- Source sheet has deliberate Select, quota preview, remaining traffic, per-source refresh and copy/rename/edit/remove. Choice persists; canonical URLs retain source identity. Missing provider quota/expiry remain unknown.
- Settings cards use static depth and soft gradients; background spheres are painted only on normal repaints. Lightweight/high-contrast modes disable extra effects. No layout expansion or permanent animation timer.
- No trusted signing credential was available. Distribution remains unsigned. Optional Windows signing tool accepts an existing certificate-store thumbprint and verifies Authenticode output; it never generates or installs a self-signed trust root.

See UPDATE-0.10.0.md and TEST_RESULTS.md. Modern Windows 10/11 x64 only, not Legacy.
