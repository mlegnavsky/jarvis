# Private HTTPS backups implementation plan

Goal: native HA WebDAV backups on the owner's Plesk server, outside public webroot.
Architecture: constrained flat WebDAV endpoint in PHP; HA's existing WebDAV integration sends encrypted archives and metadata. No Green code changes or Core restart. SFTP externally times out; chrooted shell cannot inspect host firewall. User explicitly requested autonomous implementation.

- [ ] Write real HTTP contract tests: auth, flat safe paths, listing, streaming upload/download, interrupted/oversize upload, immutable/idempotent writes, symlink rejection, private configuration, deletion disabled.
- [ ] Implement PHP endpoint with authentication before filesystem access, private root derived as sibling of httpdocs, unique temporary writes and atomic no-overwrite publication. 4 GiB per file, 1 GiB free reserve. No secrets/public downloads or client-selected filesystem root.
- [ ] Provide credential generator that only downloads private configuration; no unauthenticated server configuration writes. User places configuration outside webroot and enters password in native HA UI.
- [ ] Add mandatory PHP HTTP tests to CI before publication. Publish endpoint as an explicit allowlist alongside the existing portal; no private configuration in Git.
- [ ] Verify live HTTPS endpoint fails closed before setup, public private-file URLs denied, archive pipeline unchanged. Report pending secret bootstrap and actual encrypted Green upload as unverified.
