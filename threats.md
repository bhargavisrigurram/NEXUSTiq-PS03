# TrustVault Automated Threat Matrix (T01 - T28)

Every threat vector listed below is automatically verified and asserted via TrustVault's automated security test suite (`npm test`), passing with 100% success rate across 117 tests.

---

## Complete Threat Defense Table

| Threat ID | Threat Vector & Description | TrustVault Defense Mechanism | Test Suite Verification |
|---|---|---|---|
| **T01** | Insecure Direct Object References (IDOR) | Mandatory central `authorize()` kernel. Unauthorized queries strictly return `404 Not Found`. | `tests/security/threat-matrix.test.ts` |
| **T02** | Direct File URL Access / Static Exposure | Files are stored outside the web root as opaque `.bin` blobs. No static routes exist. | `tests/security/threat-matrix.test.ts` |
| **T03** | Path Traversal via Filename / Storage Key | Storage keys are pure UUIDs. Filenames sanitized via `path.basename()`. Slashes rejected. | `tests/security/documents.security.test.ts` |
| **T04** | Disguised Executable Upload (e.g. `.exe` as `.pdf`) | Binary magic byte inspection (`StorageService.detectFileType`). `MZ` and `ELF` rejected. | `tests/security/documents.security.test.ts` |
| **T05** | Stored Cross-Site Scripting (XSS) via Filename | Filenames sanitized against HTML tags. Downloads served with `Content-Disposition: attachment`. | `tests/security/documents.security.test.ts` |
| **T06** | Mass Assignment of Document Metadata | Strict Zod schema validation; `owner_id`, `id`, and timestamps cannot be injected via request body. | `tests/security/documents.security.test.ts` |
| **T07** | Viewer Privilege Escalation to Edit/Share/Delete | Role and permission matrix checks. Viewer grantees strictly restricted to read operations. | `tests/security/authorization.security.test.ts` |
| **T08** | Stale Session Re-use After Logout or Deactivation | Sessions stored in PostgreSQL; destroyed upon logout. Disabled user sessions rejected instantly. | `tests/security/auth.security.test.ts` |
| **T09** | Replay of Expired or Consumed Download Tokens | Tokens are single-use with atomic `consumed_at` updates. Subsequent calls yield `410 Gone / 404`. | `tests/security/documents.security.test.ts` |
| **T10** | Forged or Tampered Download Tokens | Tokens generated with 256 bits of cryptographic entropy and stored as SHA-256 hashes. | `tests/security/documents.security.test.ts` |
| **T11** | Metadata Leakage via Search / Facets | SQL predicate isolation (`getDocumentAuthorizationSqlPredicate`). Unauthorized rows filtered in DB. | `tests/security/authorization.security.test.ts` |
| **T12** | Accessing Soft-Deleted Documents Before Recovery | Soft-deleted files return `404` to non-owners. Only document owner can invoke `recover`. | `tests/security/documents.security.test.ts` |
| **T13** | Unauthorized Version History Access | Version listing and version downloads require identical authorization checks as the parent doc. | `tests/security/documents.security.test.ts` |
| **T14** | Database Tampering of Audit Logs by Admins or DBAs | PostgreSQL trigger `trg_audit_log_immutable` strictly throws exception on any `UPDATE` or `DELETE`. | `tests/security/audit.security.test.ts` |
| **T15** | Race Condition on Revoked Grants | Permissions checked synchronously in the database on every request. Revocation is instantaneous. | `tests/security/authorization.security.test.ts` |
| **T16** | Brute-Force Password Guessing & Credential Stuffing | Memory-hard Argon2id. Automatic 15-minute account lockout after 5 consecutive failed attempts. | `tests/security/auth.security.test.ts` |
| **T17** | Information Leakage in Verbose Error Responses | Central error middleware conceals stack traces, raw SQL queries, and internal database details. | `tests/security/threat-matrix.test.ts` |
| **T18** | Cross-Origin Resource Sharing (CORS) Abuse | Strict origin whitelist in CORS middleware; unauthorized external origins rejected with `403`. | `tests/security/threat-matrix.test.ts` |
| **T19** | Cross-Site Request Forgery (CSRF) | Cryptographic CSRF tokens required in `x-csrf-token` header for all state-changing requests. | `tests/security/auth.security.test.ts` |
| **T20** | Denial of Service via Oversized File Uploads | Express boundary limits file payloads to a maximum of 10 MB, immediately rejecting excess sizes. | `tests/security/documents.security.test.ts` |
| **T21** | Decompression Bombs via Archive Files | Archives (`.zip`, `.tar`, `.gz`) are strictly disallowed at the gateway boundary. | `tests/security/documents.security.test.ts` |
| **T22** | Concurrent Version Overwrite Collisions | Optimistic concurrency control via `version_number` constraint prevents conflicting concurrent edits. | `tests/security/threat-matrix.test.ts` |
| **T23** | Storage Leaks & Dangling Orphan Files | Rollback mechanisms clean up newly written binary files on filesystem if DB transaction fails. | `tests/security/documents.security.test.ts` |
| **T24** | Audit Log Sequence Manipulation | Hash continuity check: $\text{CurrentHash} = \text{SHA256}(\text{PrevHash} + \text{Data})$ anchored at Genesis. | `tests/security/audit.security.test.ts` |
| **T25** | Session Fixation Attacks | Session ID is regenerated on every login; old session identifier is invalidated immediately. | `tests/security/auth.security.test.ts` |
| **T26** | Inactive / Deactivated User Login | User `is_active` flag evaluated at login. Inactive accounts denied immediately without hash verification. | `tests/security/auth.security.test.ts` |
| **T27** | Expired Access Grants | Grants evaluate `expires_at > NOW()`. Expired grants are mathematically equivalent to non-existent. | `tests/security/authorization.security.test.ts` |
| **T28** | Administrator Privilege Overreach (Least Privilege) | Administrators cannot read or download user files without an explicit grant. Probing returns `404`. | `tests/security/audit.security.test.ts` |
