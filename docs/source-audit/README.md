# Source Audit

This directory is the public-page audit record for the njupt-search Source-Channel Graph.

Rules:

- inspect public pages only;
- do not log in;
- do not bypass campus IP or identity restrictions;
- do not save personal data from detail pages or attachments;
- record structure, selectors, URL patterns, XHR/API observations, risks, and student value;
- write usable channels to `config/source_channels.json`.

Coverage as of 2026-05-24:

- P0 audited and deepened: `jwc`, `xsc`, `pg`, `ygb`, `youth`, `cxcy`, `job`, `lib`, `bwc`, `hqc`;
- P1 audited or probed with Chrome DevTools MCP: `njupt_notice`, `news`, `xxgk`, `exchange`, `yzb`, `xxb`, `cwc`, `archives`, `pe`;
- P2 college channels are configured as production skeletons for later deep audit.

Every audit file follows the same minimum contract: `base_url`, audit time, navigation, student channels, list URLs, pagination, detail selector, attachment selector, XHR/fetch status, access limits, sensitive risks, keep keywords, and filter keywords.
