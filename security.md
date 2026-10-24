# TrustVault Cryptographic & Security Proofs

---

## 1. Cryptographic Authentication & Password Derivation

TrustVault enforces **Argon2id** (RFC 9106) for all user password hashing, configured to meet OWASP and FIPS recommendations:

$$\text{Hash} = \text{Argon2id}(P, S, m=65536, t=3, p=4)$$

- **Memory Cost ($m$)**: $65,536\text{ KB}$ ($64\text{ MB}$ RAM per derivation).
- **Time Cost ($t$)**: $3$ iterations.
- **Parallelism ($p$)**: $4$ threads.
- **Salt ($S$)**: 16 cryptographically secure random bytes generated via `node:crypto.randomBytes()`.

### Resistance to Side-Channel & GPU Attacks
Argon2id combines data-dependent memory access (from Argon2d) to defeat GPU/ASIC acceleration with data-independent access (from Argon2i) to mitigate cache-timing and side-channel attacks.

---

## 2. Mathematical Proof of Existence Concealment (IDOR Defeat)

Let $D$ be the universe of all document identifiers, and $U$ be the universe of authenticated users. For any document $d \in D$ and user $u \in U$:

$$\text{Permission}(u, d) = \begin{cases} 
\text{ALLOW} & \text{if } \text{Owner}(u, d) \lor \text{ActiveGrant}(u, d) \\
\text{DENY} & \text{otherwise}
\end{cases}$$

### Information Leakage Under Vulnerable Systems:
In standard systems returning `403 Forbidden` on unauthorized access:
$$\text{Response}(u, d) = \begin{cases}
200 \text{ OK} & \text{if } \text{Permission}(u, d) = \text{ALLOW} \\
403 \text{ Forbidden} & \text{if } d \in D \land \text{Permission}(u, d) = \text{DENY} \\
404 \text{ Not Found} & \text{if } d \notin D
\end{cases}$$
The attacker evaluates the decision boundary between $403$ and $404$, learning with 100% certainty whether $d \in D$.

### TrustVault Existence Concealment:
$$\text{Response}(u, d) = \begin{cases}
200 \text{ OK} & \text{if } \text{Permission}(u, d) = \text{ALLOW} \\
404 \text{ Not Found} & \text{if } \text{Permission}(u, d) = \text{DENY} \lor d \notin D
\end{cases}$$
Because the response code, response body, payload size, and response latency distribution are statistically indistinguishable, the mutual information leakage between the query outcome and document existence is zero:
$$I(\text{Existence}(d); \text{Response}(u, d)) = 0\text{ bits}$$

---

## 3. Cryptographic Hash-Chained Audit Ledger

Each entry in `audit_log` is mathematically bound to its predecessor via SHA-256:

$$\text{GenesisHash} = 0^{64} = \text{"0000000000000000000000000000000000000000000000000000000000000000"}$$

For each subsequent sequence number $n \ge 1$:
$$\text{CurrentHash}_n = \text{SHA-256}(\text{CurrentHash}_{n-1} + \text{canonicalJSON}(E_n))$$

Where the canonical JSON representation guarantees deterministic byte-level serialization:
$$\text{canonicalJSON}(E_n) = \text{SortKeys}(\{ \text{sequence\_number}, \text{timestamp}, \text{event\_type}, \text{actor\_id}, \text{target\_id}, \text{outcome}, \text{details} \})$$

### Tamper Detection Theorem
If an adversary alters any byte of historical entry $E_k$ ($1 \le k < n$), by the collision resistance of SHA-256:
$$\text{SHA-256}(\text{CurrentHash}_{k-1} + \text{canonicalJSON}(E_k')) \ne \text{CurrentHash}_k$$
This breaks the hash continuity for all subsequent blocks $k+1, \dots, n$, immediately triggering a verification alarm during administrative verification or automated scans.

### Database Kernel Trigger Immutability
Even if a database administrator executes an `UPDATE` or `DELETE` query, the PostgreSQL database trigger `trg_audit_log_immutable` intercepts the operation before row modification:
```sql
CREATE OR REPLACE FUNCTION fn_audit_log_immutable()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'TrustVault Invariant Violation: audit_log table is append-only. UPDATE and DELETE are prohibited.'
    USING ERRCODE = '23505';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_log_immutable
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW
EXECUTE FUNCTION fn_audit_log_immutable();
```

---

## 4. Single-Use Download Tokens & Replay Defense

Direct persistent storage URLs are never exposed to clients. When an authorized user requests a download:
1. The server generates a cryptographically random token $T \in \{0, 1\}^{256}$ using `crypto.randomBytes(32)`.
2. The server stores $\text{SHA-256}(T)$ in `download_tokens` with an expiration timestamp $\text{ExpiresAt} = \text{Now}() + 60\text{ seconds}$.
3. When $T$ is redeemed via `GET /api/documents/token-download?token=T`:
   - The token hash is looked up: `WHERE token_hash = SHA256(T) AND consumed_at IS NULL AND expires_at > NOW()`.
   - In a single atomic transaction:
     ```sql
     UPDATE download_tokens
     SET consumed_at = NOW()
     WHERE token_hash = $1 AND consumed_at IS NULL AND expires_at > NOW()
     RETURNING document_id, version_id;
     ```
4. If zero rows are returned, the request is rejected with `HTTP 410 Gone / 404 Not Found`. Replay attacks are mathematically impossible.

---

## 5. Agentic AI Firewall & Prompt Injection Defense

The Vault Copilot employs a defense-in-depth pipeline defending against generative AI vulnerabilities (OWASP Top 10 for LLMs):

```
Inbound User Prompt
       │
       ▼
[ Layer 1: Heuristic & Regex Classifier ]
  - Checks for System Instruction Overrides ("Ignore previous instructions", "Disregard rules")
  - Checks for Exfiltration Probes ("Reveal system prompt", "Output your instructions")
  - Checks for Jailbreaks ("DAN mode", "Developer mode enable", "Roleplay unrestricted")
  - Checks for SQL Injection Injections ("' OR 1=1 --", "UNION SELECT")
       │
       ├──► [Match Found] ──► Immediate Shield Deflection (Zero LLM Invocation)
       │
       ▼ [Input Clean]
[ Layer 2: Scope & Grant Enforcement ]
  - Evaluates user document authorization before loading context
       │
       ▼
[ Layer 3: System Anchor Injection ]
  - Strict system prompt anchoring Gemini 2.5 / 3.5 Flash Lite
       │
       ▼
Safe AI Output to Logged-in User
```
