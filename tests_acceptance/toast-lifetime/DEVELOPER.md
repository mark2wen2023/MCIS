# Toast lifetime developer regression
Base main94d5e38c926fda232bb987b60fa9145e4bcf01a7; independent of case-status UI branch.
Synthetic hook/clock harness loads the actual ToastProvider through esbuild/VM;
no browser, HTTP, API, model, data, paused or refusal tests.
Initial harness incorrectly read CommonJS exports; corrected before reproduction.
On unchanged production source: node tests/toast-lifetime.test.cjs failed
`same success twice`, actual undefined vs expected 已保存 after first timer fired.
Fix ties expiration to object identity instead of text, without changing 3800ms.
After fix: same command from web passed five scenarios (duplicate successes,
duplicate errors, same text/different kind, different messages, single expiry).
`npm run build` passed TypeScript+Vite, 766 modules, >1500kB chunk warning retained.
Reused approved node_modules; no installation. No real React scheduling, browser,
visual or independent acceptance claimed. Synthetic hook state/timers are substitutes.
