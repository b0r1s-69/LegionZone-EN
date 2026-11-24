# Build pipeline (reference)

These are the exact scripts used to produce the two APKs. Paths are from the build host
(`/home/admin1/Documents/deepseek-harness/Workspace2/lz`); adjust `DEC`, `work/` and the APK path
before running.

Order of operations:

1. `apktool d -f -o dec orig.apk` — decode resources + smali (apktool 3.0.3, aapt2 2.19).
2. `extract.py` — pull every Chinese string out of `res/values*`, layouts, smali `const-string`
   lines and arrays into `work/units.json` (1,742 unique values).
3. Translation (the batches under `work/batches`, results in `work/en_map.json`, `work/out/*.json`).
4. `apply_smali.py` — write the English values back into the `const-string` sites.
5. `smali.jar assemble -a 33 dec/smali -o classes.dex`, same for `smali_classes2`.
6. `build_variant.py v1|v2 out.apk` — re-zip the original APK, replacing:
   * `resources.arsc` and every binary `res/*.xml` through `arsc_patch.patch_bytes`
     (rebuilds the `ResStringPool`, keeps indices, fixes chunk sizes),
   * locale `ResTable_type` chunks (`arsc_patch.strip_locale_configs`),
   * `classes.dex` / `classes2.dex`,
   * the bundled H5 page; for `v2`, `classes2` also carries `com/zui/legion/en/EnUi`.
7. `zipalign -f -p 4`, then `apksigner sign` (v3 scheme).

Why not `apktool b`: this APK references private framework attributes
(`notificationHeaderTextAppearance`, `screen_action_bar`, …), so `aapt2 link` fails with
"failed linking references". Patching the compiled resource table in place keeps every resource ID
and every byte that does not need to change.

`en.js` is the V2 WebView translator: ~230 exact-match entries, 9 count/date regex rules, a
MutationObserver, and guards that skip inputs, canvases, editable regions and code blocks.
