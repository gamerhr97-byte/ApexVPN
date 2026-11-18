# Input audit and implementation decision

## Supplied ZIP

- Name: `nekoray-4.0.1-2024-12-12-windows64.zip`.
- SHA256: `a492224792c38bd1a3b7a5438b1431c5cb4260f55e9a121db3b2ce1603f7664a`.
- 43 entries including directories; 109,655,497 expanded bytes.
- Paths and ZIP Unix symlink bits were checked before extraction. No uploaded
  executable was run. All original inputs remain unchanged.
- GUI: `nekobox.exe` (3,322,368 bytes), PE Windows executable. Its embedded
  FileVersion/ProductVersion is **1.0.0.0**, so the filename alone is not a
  cryptographic proof of release identity. The uploaded name matches upstream
  release naming; no upstream release signature was available/verified for it.
- GUI dependencies: Qt6Core/Gui/Widgets/Network/Svg. Qt6Core's embedded resource
  reports **6.7.2.0**. Bundled Windows platform, style, icon/imageformat, TLS and
  network-information plugins are listed in the complete inventory JSON.
- Core: `nekobox_core.exe` (32,555,520 bytes); Go/sing-box symbols are present.
  Embedded Go build metadata records upstream commit
  `adef6cd4af7dffc77235c524086f3dc4100d8457`, timestamp
  `2024-12-12T08:03:36Z`, and `vcs.modified=true`. This anchors the tag comparison
  but does not prove bit-for-bit equivalence to pristine source. The exact
  runtime core version was not established by executing the binary.
- Other dependencies/assets: OpenSSL 3 DLLs, `dxcompiler.dll`, `dxil.dll`,
  `geoip.dat`, `geoip.db`, `geosite.dat`, `geosite.db`, `nekobox.png`, Chinese Qt
  translation, updater executable. No license documents were in the ZIP.
- No C/C++/Go source, user profiles, subscriptions, or runtime configuration
  were present. No user profile had to be modified or migrated from this ZIP.
- Full paths, sizes and individual file hashes: `original-package-inventory.json`.

## Legitimate matching source

Retrieved the official repository using Git at tag `4.0.1`:
https://github.com/MatsuriDayo/nekoray/tree/4.0.1

Commit: `adef6cd4af7dffc77235c524086f3dc4100d8457`.
The `QHotkey` submodule was also retrieved. A source snapshot accompanies the
source deliverable; no original source changes are claimed. Repository README,
CMake, Go modules, bean schemas and database serialization were inspected.
The official repository is archived and identifies a Qt GUI/sing-box backend.
Its GPLv3 license must accompany any derivative distribution and corresponding
source must be made available. The new application is also GPL-3.0-only.

Upstream license: https://github.com/MatsuriDayo/nekoray/blob/4.0.1/LICENSE
Source dependencies/submodule references remain in the snapshot. It is not a
prebuilt, self-contained upstream development toolchain.

## Reuse versus replacement

| Component | Decision |
| --- | --- |
| Original UI and original binaries | Retained for audit; not patched or redistributed as the new program |
| Qt architecture | Retained via native Qt Widgets/PySide6, no web view |
| Original artwork | Not reused; new code-drawn power control and N wordmark |
| Original profile schema | Used to design conservative backup and migration |
| Original sing-box RPC core | Replaced with external Xray subprocess/pipe adapter |
| Modern VLESS encryption | Original string preserved; Xray preflight + genuine traffic checks required |
| Windows proxy manager | New WinINET API implementation with durable ownership-aware recovery lease |
| UI/state/storage/diagnostics/statistics | New source modules, separate responsibilities |

C++/Qt was considered. Modifying the archived frontend would retain its old
sing-box-specific RPC and configuration assumptions. A new Qt/Python frontend
was chosen to implement and exercise current Xray integration within this
Linux build environment. It adds a Python runtime; it is not claimed to have
C++ startup/memory equivalence. The native launcher is C; this is an explicitly
documented technology deviation, not an undisclosed original-source rewrite.

## VLESS ML-KEM compatibility

Official Xray documentation describes `encryption` as a multi-block string and
`mlkem768x25519plus` as the handshake scheme:
https://xtls.github.io/en/config/outbounds/vless.html

The adapter retains the raw URI and exact encryption value, including literal
`+` characters, then passes it to Xray unchanged. It does not implement crypto.
Unrecognized fields are retained and block connection. Core preflight rejects
invalid/unsupported encryption rather than replacing it with `none`.

Bundled and tested baseline: Xray **26.3.27**. That is a **tested sufficient
baseline, not a researched earliest compatible version** for every scheme.
The exact private server configuration was not provided. Only local core-generated
ML-KEM native/0rtt cases with Vision were tested, with X25519 and ML-KEM-768
server authentication. No claim of compatibility with an unseen encryption
string or the user's remote REALITY deployment is made.
