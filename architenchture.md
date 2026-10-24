# TrustVault Architecture (architenchture.md)

Please see the comprehensive system architecture documentation in [architecture.md](file:///d:/nexus%20tiq24/trustvault/architecture.md).

### Quick Architectural Summary:
- **Central Authorization Kernel**: Single `authorize()` checkpoint. Deny by default.
- **Existence Concealment**: Strict HTTP 404 on unauthorized reads to defeat IDOR.
- **Content-Addressable Storage (CAS)**: SHA-256 payload indexing with binary magic byte validation.
- **Append-Only Cryptographic Audit Log**: SHA-256 hash chaining anchored at Genesis with PostgreSQL kernel trigger `trg_audit_log_immutable`.
- **Agentic AI Copilot**: Powered by Gemini 3.5 / 2.5 Flash Lite with hardened Prompt Injection Firewall.
- **Database Synchronization**: Connected to Supabase real-time PostgreSQL project `hybpqldwblpxluvsqazz`.
