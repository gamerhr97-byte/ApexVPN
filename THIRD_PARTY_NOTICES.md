# Third-party notices and corresponding source

NekoRay Next application source and C launcher: Copyright (c) 2026 NekoRay Next
contributors. Licensed under GNU GPL version 3 only. Full text in `LICENSE`.
No license-bypass patching or security-protection bypass was performed.

## Original NekoRay 4.0.1 source snapshot (source delivery only)

Copyright MatsuriDayo and contributors; GPLv3. Matching source commit
`adef6cd4af7dffc77235c524086f3dc4100d8457` is included separately in the source
bundle, with its LICENSE and QHotkey submodule notice. It was inspected for
architecture and legacy data formats. Its C++ GUI and original binaries were
not incorporated into the replacement runtime.

https://github.com/MatsuriDayo/nekoray/tree/4.0.1

## Qt / PySide6-Essentials / Shiboken6 6.8.3

Copyright The Qt Company Ltd. and other contributors. PySide6/Shiboken wheel
metadata specifies `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`. Applicable Qt
modules have their own licenses/notices. This application uses the open-source
license terms, not the commercial license text also present in wheel metadata.
License copies: `licenses/LGPL-3.0.txt`, `licenses/GPL-3.0.txt`,
`licenses/Qt-GPL-exception.txt`. Upstream wheel contents and notices are retained.

These native DLLs remain separate and replaceable under `runtime/PySide6/`.
Do not restrict reverse engineering necessary to debug modifications to these
libraries. Application source and build instructions are included so you can
rebuild/relink the combined application. The source of the exact unmodified
libraries is available alongside these binary directions at:

- PySide6/Shiboken source: https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v6.8.3
- Qt 6.8.3 source archive directory: https://download.qt.io/archive/qt/6.8/6.8.3/single/
- Exact Qt source archive: https://download.qt.io/archive/qt/6.8/6.8.3/single/qt-everywhere-src-6.8.3.tar.xz
- Qt attribution/license index: https://doc.qt.io/qt-6.8/licenses-used-in-qt.html
- Qt for Python terms: https://doc.qt.io/qtforpython-6/licenses.html

Some optional modules carried by the full Essentials wheel may be GPL-only;
the application is GPLv3 and these libraries are unmodified. No Qt WebEngine
wheel is bundled and no embedded browser is instantiated. Source download
locations are upstream-operated third-party servers; preserve these notices
and source-access directions if redistributing the portable ZIP.

## Xray-core 26.3.27

Copyright XTLS/Xray-core contributors. Mozilla Public License 2.0, full text in
`licenses/Xray-MPL-2.0.txt` and `core/LICENSE` in the portable package. The official
binary is unmodified, separate from the GPL GUI, and communicates over a config
pipe and local TCP. Xray has third-party Go dependencies governed by their own
licenses. Source, module manifest and checksums:

- https://github.com/XTLS/Xray-core/tree/v26.3.27
- https://github.com/XTLS/Xray-core/archive/refs/tags/v26.3.27.tar.gz
- https://github.com/XTLS/Xray-core/blob/v26.3.27/go.mod
- https://github.com/XTLS/Xray-core/releases/tag/v26.3.27

Release SHA256 digests were compared to official `.dgst` files; this verifies
integrity against the same upstream source, not an independent release signature.
The portable package excludes upstream Wintun, geodata and helper scripts.

## CPython 3.13.9 embeddable Windows runtime

Copyright Python Software Foundation and contributors. PSF license and bundled
third-party notices: `runtime/LICENSE.txt` and `licenses/Python-3.13.txt`.
Unmodified Windows embeddable distribution, with an application-specific `_pth`.

- https://www.python.org/downloads/release/python-3139/
- https://github.com/python/cpython/tree/v3.13.9

## Development-only tools

Zig 0.13.0 (MIT) compiles the launcher; compiler and headers are not shipped in
the portable runtime. https://github.com/ziglang/zig/tree/0.13.0

pytest 9.1.1 (MIT) runs tests; not required by the portable application.
https://github.com/pytest-dev/pytest

Windows system fonts are requested by name and not redistributed. Linux
screenshots use fallback system fonts. The new power symbol is drawn in code;
no Hiddify/Happ logos or proprietary artwork are included.

## QR import additions in 0.3.0

ZXing-cpp Python binding/core 2.3.0: Apache License 2.0. License copy in
`licenses/ZXing-cpp-2.3.0.txt`; exact source and dependency licenses at
https://github.com/zxing-cpp/zxing-cpp/tree/v2.3.0 . The upstream wheel is
unmodified and its metadata is retained in `runtime/`.

Pillow 11.1.0: HPND/Pillow license and third-party image-codec notices in
`licenses/Pillow-11.1.0.txt` and its retained distribution metadata. Source:
https://github.com/python-pillow/Pillow/tree/11.1.0 . Native image/QR dependencies
are used locally; scanned content is never sent to a recognition service.

## Country flags in 0.3.1

The bundled two-letter 4:3 SVG country flag assets come unmodified from
lipis/flag-icons v7.3.2, commit fe15c16e7463d0c66d6c5730e9d0e832438d98e1.
MIT license, copyright Lipis and contributors; full notice in
`licenses/flag-icons-MIT.txt`. Source: https://github.com/lipis/flag-icons/tree/v7.3.2 .
No emoji-font support or remote flag-image download is needed at runtime.
The optional on-click country response comes from https://country.is/ using
the requested IP only, through the current proxy.


## Added in 0.10.3
- sing-box 1.14.4, SagerNet, GPL-3.0-or-later; LICENSE in licenses/sing-box-LICENSE. Pinned upstream archives and extracted binary SHA-256 values are in sing-box.lock.json. Source: https://github.com/SagerNet/sing-box/tree/v1.14.4 .
- PyYAML 6.0.2, MIT; upstream wheel license/metadata retained in the portable runtime. Source: https://github.com/yaml/pyyaml .
- Service favicons are the respective websites' identification marks, retrieved via the recorded public favicon sources in assets/services/sources.json. Trademark ownership remains with the respective owners; no affiliation is claimed. These are not newly generated official logos.


## 0.10.4 additions
Xray-core 26.10.21 (MPL-2.0) is pinned in dependencies.lock.json. Public Free sources are externally maintained and are not operated by Apex VPN. The public Mahsa static-feed AES-CBC format was independently implemented; format reference: https://github.com/MostafaDadkhah/MahsaNG-Desktop-Bridge . No bridge code or authenticated Android backend is bundled. Windows decryption uses system BCrypt; Linux tests use system libcrypto. The Apex A icon is generated artwork based on the user-supplied reference.
