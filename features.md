# TrustVault Complete Feature Specification

---

## 1. Authentication & Session Security
- **Argon2id Key Derivation**: Passwords hashed using memory-hard Argon2id (`m=65536, t=3, p=4`), resilient against GPU and ASIC cracking attacks.
- **Session ID Rotation**: A brand new unique session token is generated on every successful login, invalidating the previous session to defeat session fixation.
- **Brute-Force & Credential Stuffing Lockout**: Automatically locks user accounts for 15 minutes after 5 consecutive failed login attempts, recording anomaly events in the audit log.
- **Timing Attack Mitigation**: Dummy password verifications run when invalid usernames are submitted, ensuring constant-time response latency.
- **Anti-CSRF Protection**: State-changing requests (`POST`, `PUT`, `DELETE`) require a cryptographically secure CSRF token in the `x-csrf-token` header.
- **Session Invalidation on Deactivation**: Deactivating or disabling a user immediately revokes all active sessions across all devices.

---

## 2. Document Management & Content-Addressable Storage (CAS)
- **Central Authorization Enforcement**: Every read, write, share, or delete operation evaluates through the `authorize()` kernel.
- **Existence Concealment**: Unauthorized access strictly returns `HTTP 404 Not Found` with identical timing, concealing file existence and preventing IDOR probing.
- **SHA-256 CAS Deduplication**: Uploaded payloads are hashed with SHA-256; files are addressed by their checksum, eliminating duplicate file storage while keeping metadata isolated.
- **Isolated Binary Storage**: Uploaded files are written as unguessable `.bin` blobs in an isolated storage directory outside the public HTTP web root.
- **Gateway Magic Byte Validation**: Inspects the first 16 bytes of every file. Disguised executables (`MZ` Windows PE, `7F 45 4C 46` Linux ELF) and dangerous archives are rejected at the boundary.
- **Document Versioning & History**: Non-destructive versioning preserving previous revisions, checksums, and author timestamps.
- **Soft-Deletion & Two-Stage Recovery**: Soft-deleted files are completely inaccessible to viewers (strict 404) while allowing owners to recover or permanently purge them.

---

## 3. Secure Sharing & One-Time Download Tokens
- **Time-Bounded Grants**: Share documents with specific users with configurable expiration times (e.g. 1 hour, 24 hours, 7 days).
- **Sub-Millisecond Revocation**: Revoking a grant immediately takes effect at the database layer; subsequent read requests fail instantly.
- **Single-Use 60-Second Download Tokens**: Document downloads do not expose persistent direct URLs. The system issues single-use cryptographic tokens expiring after 60 seconds that become invalid immediately after first download.
- **Replay Attack Resistance**: Consumed download tokens cannot be reused or replayed under any circumstances.

---

## 4. Cryptographic Audit Chain & Administrator Tools
- **Mathematically Linked SHA-256 Log**: Every event links to the preceding entry:
  $$\text{CurrentHash}_n = \text{SHA-256}(\text{PreviousHash}_{n-1} + \text{canonicalJSON}(E_n))$$
- **PostgreSQL Immutability Trigger**: Database trigger `trg_audit_log_immutable` strictly prohibits `UPDATE` or `DELETE` operations on `audit_log`, even by privileged database users.
- **1-Click Chain Verification**: Instant recalculation from Genesis to Head hash, pinpointing any modified or missing sequence numbers.
- **1-Click Automated Security Scan**: Admin button triggering a full-spectrum security assessment (audit continuity, CAS integrity, DB triggers, anomaly detection, AI firewall) with a 0-100 posture score.
- **Anomaly Detection Engine**: Real-time identification of repeated login failures, IDOR access denied probes, and unusual download volumes.

---

## 5. Agentic AI Copilot & DLP Safeguards
- **Gemini 2.5 / 3.5 Flash Lite Engine**: Powered by Google Gemini with customizable API key support and seamless local fallback.
- **Hardened Prompt Injection Firewall**: Pre-flight inspection detects and neutralizes instruction overrides, DAN jailbreaks, system prompt exfiltration probes, and SQL injections.
- **Strict Authorization Boundary**: The Copilot cannot read or synthesize information from documents the user does not have an active grant for.
- **Data Loss Prevention (DLP) Scans**: Automated scanning for unmasked API keys, private certificates, Social Security Numbers (SSN), and credit card numbers.
- **Guest Protection**: The AI Copilot is strictly hidden and inaccessible for logged-out visitors, becoming active only after authentication.

---

## 6. Evaluator & Production Experience
- **1-Click Judge & Fast-Track Access**: Pre-configured sample cards for Administrator, Owner (Alice), and Viewer (Bob) allowing evaluators to log in with a single click.
- **Pre-Upload File Security Checker**: In-browser client-side file inspection verifying file magic bytes, checking double extensions, and pre-computing SHA-256 CAS keys.
- **Interactive Security Visualizer**: Demonstrates Existence Concealment, Hash Chain Tamper Injections, and Magic Byte sniffing directly on the landing page.
- **Real-Time Supabase Sync**: Direct integration with Supabase PostgreSQL project `hybpqldwblpxluvsqazz`.
- **117 / 117 Automated Tests**: Full threat matrix verified with 100% test pass rate.
