# 0.2.1 — profile field compatibility

Fixes a verified adapter limitation: TCP/RAW `headerType=none` is now explicitly
serialized instead of rejected. Supports common REALITY/TLS aliases with
conflict checks. Keeps original fields and encryption untouched. Unsupported
features remain blocked rather than silently removed.

Diagnostics identify known unsupported field names without values. For other
fields use Servers → select the row → Parameter names. The local dialog shows
names only and has an explicit Copy names only action. Review before sharing;
never send the original link or secrets.

The supplied error report had 65 ms direct TCP reachability and stopped during
configuration conversion. Its actual unsupported key was not included. This
hotfix is not a claim that the unseen profile is now fully compatible.

Close the app, back up `data/`, and merge the `NekoRayNext` folder from the small
update ZIP over the existing folder. No data, runtime, core or executable is
included in that overlay. Open the existing EXE; the sidebar should show 0.2.1.
The full portable release and source are also supplied. 39 tests passed on Linux;
Windows/remote-profile verification remains outstanding.

Technical references:
https://xtls.github.io/en/config/transports/raw.html
https://github.com/XTLS/Xray-core/discussions/716
