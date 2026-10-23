# Source attribution

`bootstrap_keys.py` and `capture_keys.py` are vendored from:
https://github.com/DaneelOlivaw1/macos-wechat-export

Pinned commit: 88ca1bef06279f3bc9fa27a379b417f71b6e88a5

The upstream project attributes its foundation to acmerfight's MIT-licensed gist:
https://gist.github.com/acmerfight/0a01249ef72970d07a2603dbb629e80f

The accompanying LICENSE is retained from upstream. These two source files are
included for the temporary-copy setup workflow; this exporter does not use the
upstream UI message-sending or automatic reply tools.

Local changes: temporary bundles are kept outside iCloud-synced Documents;
FinderInfo is cleared only on that copy before signing. An optional
`--prepared-copy` reuses a verified bundle in this tool's private temporary
directory after the user grants its macOS privacy permission. It rejects the
installed executable and does not grant or reset permissions programmatically.
