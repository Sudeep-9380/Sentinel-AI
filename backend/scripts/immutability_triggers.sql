-- ============================================================
-- Sentinel — Immutability & Integrity Triggers
-- ============================================================
-- Run this script in pgAdmin or DBeaver AFTER Alembic creates
-- the tables (alembic upgrade head).
--
-- These triggers enforce append-only semantics on audit-critical
-- tables at the database level, preventing accidental or
-- malicious UPDATE/DELETE operations even from application code.
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- 1. CHAIN OF CUSTODY LOG — Absolute Immutability
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION prevent_custody_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        '[SENTINEL] chain_of_custody_log is APPEND-ONLY. '
        'UPDATE and DELETE operations are prohibited to maintain '
        'legal chain-of-custody integrity. Entry ID: %',
        COALESCE(OLD.id::text, 'unknown');
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Drop if exists (idempotent re-runs)
DROP TRIGGER IF EXISTS trg_custody_immutable ON chain_of_custody_log;

CREATE TRIGGER trg_custody_immutable
    BEFORE UPDATE OR DELETE ON chain_of_custody_log
    FOR EACH ROW
    EXECUTE FUNCTION prevent_custody_mutation();

COMMENT ON TRIGGER trg_custody_immutable ON chain_of_custody_log IS
    'Prevents any UPDATE or DELETE on the chain_of_custody_log table '
    'to maintain tamper-evident, legally defensible audit trail.';


-- ────────────────────────────────────────────────────────────
-- 2. AUDIT LOG — Append-Only
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        '[SENTINEL] audit_log is APPEND-ONLY. '
        'UPDATE and DELETE operations are prohibited. Entry ID: %',
        COALESCE(OLD.id::text, 'unknown');
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_log_immutable ON audit_log;

CREATE TRIGGER trg_audit_log_immutable
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_log_mutation();

COMMENT ON TRIGGER trg_audit_log_immutable ON audit_log IS
    'Prevents any UPDATE or DELETE on the audit_log table.';


-- ────────────────────────────────────────────────────────────
-- 3. EVIDENCE CLIP ACCESS LOG — Append-Only
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION prevent_evidence_access_log_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        '[SENTINEL] evidence_clip_access_log is APPEND-ONLY. '
        'UPDATE and DELETE operations are prohibited. Entry ID: %',
        COALESCE(OLD.id::text, 'unknown');
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_evidence_access_log_immutable ON evidence_clip_access_log;

CREATE TRIGGER trg_evidence_access_log_immutable
    BEFORE UPDATE OR DELETE ON evidence_clip_access_log
    FOR EACH ROW
    EXECUTE FUNCTION prevent_evidence_access_log_mutation();

COMMENT ON TRIGGER trg_evidence_access_log_immutable ON evidence_clip_access_log IS
    'Prevents any UPDATE or DELETE on the evidence_clip_access_log table.';


-- ────────────────────────────────────────────────────────────
-- 4. NOTIFICATION LOG — Append-Only (except status updates)
-- ────────────────────────────────────────────────────────────
-- Notification log allows STATUS updates (QUEUED->SENT->DELIVERED)
-- but blocks DELETE and prevents changes to immutable fields.

CREATE OR REPLACE FUNCTION guard_notification_log_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            '[SENTINEL] notification_log DELETE is prohibited. Entry ID: %',
            COALESCE(OLD.id::text, 'unknown');
        RETURN NULL;
    END IF;

    -- Allow only status/delivery timestamp updates
    IF TG_OP = 'UPDATE' THEN
        IF OLD.id              IS DISTINCT FROM NEW.id OR
           OLD.responder_id    IS DISTINCT FROM NEW.responder_id OR
           OLD.channel         IS DISTINCT FROM NEW.channel OR
           OLD.payload::text   IS DISTINCT FROM NEW.payload::text OR
           OLD.created_at      IS DISTINCT FROM NEW.created_at THEN
            RAISE EXCEPTION
                '[SENTINEL] notification_log immutable fields cannot be changed. '
                'Only status, delivered_at, provider_message_id, and error_message '
                'may be updated. Entry ID: %',
                OLD.id::text;
            RETURN NULL;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notification_log_guard ON notification_log;

CREATE TRIGGER trg_notification_log_guard
    BEFORE UPDATE OR DELETE ON notification_log
    FOR EACH ROW
    EXECUTE FUNCTION guard_notification_log_mutation();

COMMENT ON TRIGGER trg_notification_log_guard ON notification_log IS
    'Blocks DELETE and restricts UPDATE to status/delivery fields only.';


-- ────────────────────────────────────────────────────────────
-- 5. HASH CHAIN INTEGRITY CHECK (Utility Function)
-- ────────────────────────────────────────────────────────────
-- Callable function that walks the custody chain for a given
-- entity and returns any rows where prev_hash does not match
-- the preceding row's entry_hash.

CREATE OR REPLACE FUNCTION verify_custody_chain(p_entity_id UUID)
RETURNS TABLE (
    log_id         UUID,
    seq            INTEGER,
    expected_prev  VARCHAR(64),
    actual_prev    VARCHAR(64),
    is_valid       BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    WITH ordered_chain AS (
        SELECT
            c.id,
            c.sequence_number,
            c.entry_hash,
            c.prev_hash,
            LAG(c.entry_hash) OVER (ORDER BY c.sequence_number) AS expected_prev_hash
        FROM chain_of_custody_log c
        WHERE c.entity_id = p_entity_id
        ORDER BY c.sequence_number
    )
    SELECT
        oc.id AS log_id,
        oc.sequence_number AS seq,
        oc.expected_prev_hash AS expected_prev,
        oc.prev_hash AS actual_prev,
        (oc.prev_hash IS NOT DISTINCT FROM oc.expected_prev_hash) AS is_valid
    FROM ordered_chain oc;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION verify_custody_chain(UUID) IS
    'Walks the chain of custody for an entity and checks prev_hash linkage. '
    'Returns rows with is_valid=false if tampering is detected.';


-- ============================================================
-- VERIFICATION: Run after applying triggers
-- ============================================================
-- SELECT * FROM verify_custody_chain('your-entity-uuid-here');
--
-- Test immutability:
--   UPDATE chain_of_custody_log SET action = 'DELETED' WHERE id = '...';
--   → Should raise: "[SENTINEL] chain_of_custody_log is APPEND-ONLY..."
--
--   DELETE FROM audit_log WHERE id = '...';
--   → Should raise: "[SENTINEL] audit_log is APPEND-ONLY..."
-- ============================================================
