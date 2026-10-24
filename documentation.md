# TrustVault Technical Documentation & Production Runbook

---

## 1. System Overview

**TrustVault** is an enterprise-grade, cryptographically verifiable Zero-Trust document management core and secure storage vault. It guarantees zero data and metadata leakage across all states: storage at rest, transmission in flight, multi-tenant database indexing, and interactive AI intelligence.

### Core Architectural Invariants:
1. **Mandatory Central Authorization Kernel**: All document operations evaluate through a single, non-bypassable `authorize()` kernel. Deny by default.
2. **Existence Concealment (Zero-Leakage 404)**: Unauthorized read requests strictly return `HTTP 404 Not Found`, completely preventing resource enumeration and IDOR probing.
3. **Content-Addressable Storage (CAS)**: Binary payloads are indexed by their SHA-256 hash. Files are stored as isolated `.bin` blobs outside the web server root.
4. **Append-Only SHA-256 Audit Chaining**: Every system event calculates its hash based on the previous block's hash and canonical JSON payload:
   $$\text{Hash}_n = \text{SHA-256}(\text{Hash}_{n-1} + \text{canonicalJSON}(E_n))$$
   PostgreSQL database triggers (`trg_audit_log_immutable`) unconditionally reject `UPDATE` and `DELETE` queries.
5. **Agentic AI Copilot Guardrails**: Powered by Google Gemini 2.5 / 3.5 Flash Lite with an active pre-flight prompt injection firewall defending against instruction overrides, jailbreaks, and system prompt exfiltration.

---

## 2. Monorepo Architecture

TrustVault is organized as a production-grade TypeScript workspace monorepo:

```
trustvault/
├── apps/
│   ├── api/                     # Express.js REST API with Central Authorizer Kernel
│   │   ├── src/
│   │   │   ├── db/              # PostgreSQL / Supabase connection & PGlite fallback
│   │   │   ├── middleware/      # Auth, CSRF, security headers, validation
│   │   │   ├── modules/
│   │   │   │   ├── auth/        # Argon2id password hashing, session rotation
│   │   │   │   ├── documents/   # Document lifecycle, CAS, versioning
│   │   │   │   ├── audit/       # Cryptographic hash chain, automated scans
│   │   │   │   └── ai/          # Gemini API integration, prompt injection firewall
│   │   │   └── server.ts        # Server entrypoint & route registry
│   └── web/                     # React 18 + Vite + TailwindCSS Frontend
│       ├── src/
│       │   ├── components/      # Modular security components:
│       │   │   ├── JudgeDemoLoginCard.tsx       # 1-Click Evaluator access
│       │   │   ├── SecurityDemoVisualizer.tsx   # Interactive live exploit visualizer
│       │   │   ├── GlobalSecurityScanModal.tsx  # 1-Click admin automated audit
│       │   │   ├── PreUploadSecurityChecker.tsx # Binary magic byte sniffer
│       │   │   ├── VaultCopilotModal.tsx        # Gemini AI Assistant
│       │   │   └── Navbar.tsx                   # Production navigation bar
│       │   ├── pages/           # HomePage, DashboardPage, AdminAuditPage, AuthPage
│       │   └── services/api.ts  # Type-safe API client
├── database/
│   └── migrations/              # SQL schema, immutable triggers, and indexes
├── packages/
│   └── shared/                  # Common TypeScript interfaces & Zod schemas
└── tests/                       # Automated security verification test suite (117 tests)
```

---

## 3. Evaluator & Demo Accounts

For immediate evaluation, TrustVault automatically seeds three standard role accounts:

| Role | Username | Email | Password | Permissions & Highlight |
|---|---|---|---|---|
| **Administrator** | `admin` | `admin@trustvault.local` | `AdminPass123!` | System health, cryptographic audit verification, anomaly detection, 1-Click Automated Security Scans. *Least Privilege: Cannot view or download private user documents.* |
| **Document Owner** | `alice` | `alice@trustvault.local` | `AlicePass123!` | Full control over owned files, AI summaries & DLP scans, issuing single-use download tokens, managing access grants. |
| **Viewer** | `bob` | `bob@trustvault.local` | `BobPass123!` | Read-only access to documents shared by Alice. Probing unshared files returns strict HTTP 404 (Existence Concealment). |

---

## 4. REST API Specification

### Authentication (`/api/auth`)
- `POST /api/auth/register`: Create a new user account with Argon2id password derivation.
- `POST /api/auth/login`: Authenticate with session rotation; returns HttpOnly cookie and CSRF token.
- `POST /api/auth/logout`: Invalidate session in database and clear cookies.
- `GET /api/auth/me`: Retrieve current authenticated session identity.

### Document Management (`/api/documents`)
- `GET /api/documents`: List authorized documents with SQL predicate filtering (0 metadata leakage).
- `POST /api/documents`: Upload new document; validates file size and binary magic bytes.
- `GET /api/documents/:id`: Fetch document metadata; returns 404 if unauthorized.
- `POST /api/documents/:id/tokens`: Issue a single-use 60-second download token.
- `GET /api/documents/token-download`: Redeem one-time token to download binary payload.
- `POST /api/documents/:id/grants`: Share document with another user (read or edit grant).
- `DELETE /api/documents/:id/grants/:grantId`: Immediately revoke access grant.
- `DELETE /api/documents/:id`: Soft-delete document into trash.
- `POST /api/documents/:id/recover`: Recover soft-deleted document (owner only).

### Admin & Cryptographic Audit (`/api/admin/audit`)
- `GET /api/admin/audit`: Query append-only audit records with filters.
- `GET /api/admin/audit/verify`: Verify SHA-256 hash continuity from Genesis to Head.
- `GET /api/admin/audit/anomalies`: Fetch detected brute-force attempts and IDOR probes.
- `POST /api/admin/audit/scan`: Execute 1-Click full automated system security scan.

### Agentic AI Intelligence (`/api/ai`)
- `GET /api/ai/status`: Check Gemini API key status and active model.
- `POST /api/ai/summarize`: Generate confidential document executive summary.
- `POST /api/ai/security-scan`: Run DLP scan for credentials, private keys, and PII.
- `POST /api/ai/chat`: Interactive chat with Gemini 2.5 / 3.5 Flash Lite with prompt injection defense.

---

## 5. Security & Verification Suite

TrustVault comes with **117 automated security tests** covering all threat vectors (T01 - T28):

```bash
# Run all automated security tests
npm test

# Run build compilation check
npm run build
```

---

## 6. Production Deployment Instructions

### Option A: Railway / Render (Full-Stack Container)
1. Fork or clone this repository to GitHub.
2. In Railway or Render, select **New Project > From GitHub Repo**.
3. Choose the root directory `trustvault/` (or repository root).
4. Supply environment variables:
   - `DATABASE_URL`: Your Supabase connection string (`postgresql://postgres.[REF]:[PASS]@aws-0-[REGION].pooler.supabase.com:6543/postgres`).
   - `GEMINI_API_KEY`: Your Google Gemini API key.
   - `SESSION_SECRET`: A secure 32+ character random hex string.
5. The included `Dockerfile` will compile the shared package, backend API, and Vite web client automatically, exposing port `3000`.

### Option B: Supabase Database + Vercel Frontend + Render Backend
1. **Database**: Use existing Supabase project `hybpqldwblpxluvsqazz`.
2. **Backend**: Deploy `apps/api` to Render or Railway with port 3000.
3. **Frontend**: Deploy `apps/web` to Vercel, pointing `VITE_API_URL` to your deployed backend URL.
