# Performance targets and measurements

Initial development targets for Windows 11 x64 on a mid-range machine, to be
refined after testing on the actual target hardware:

| Measure | Initial target, not a measured Windows claim |
| --- | --- |
| Cold start to interactive UI | under 2 seconds on SSD |
| GUI-only idle working set | under 120 MiB |
| Combined GUI/core connected working set | under 220 MiB |
| GUI idle CPU | under 0.5% of one logical CPU averaged over 60 seconds |
| Idle network requests | zero |
| Dashboard counters | every 2 seconds while connected |
| Optional health request | every 60 seconds while connected |
| Bulk test concurrency | 4 default, configurable 1–16 |
| Traffic history | at most 120 samples |
| Diagnostic error history | at most 50 messages |

`benchmark-linux.json` records a **single short 0.1.0 baseline development-host run**, using
Linux x86_64 and the offscreen Qt plugin, empty profiles and no networking core.
Import-to-first-render time and peak RSS include Python/Qt imports. The idle
CPU interval is approximately five seconds; it is not a sustained benchmark or
a leak test and must not be compared directly with Windows working-set figures.

Reproduce on Linux: `python tools/benchmark.py`. For Windows, use Task Manager /
Process Explorer and Windows Performance Recorder with normal and worst-case
profiles. Record CPU model, memory, graphics, storage type, DPI, Windows build,
startup condition, sample interval and all process working sets. Run 30 cold
and warm starts; a 60-minute connected idle test; and 100 connect/disconnect
cycles. Record failures and peak memory, not only successful medians.

No unnecessary UI animations, disk log stream or idle network polling is
implemented. Profile-test writes are coalesced. Runtime configuration is sent
to stdin rather than written to disk. A stdlib-only crash watcher is used in
System Proxy mode; it waits on a Windows handle instead of polling.
