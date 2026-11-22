"""audit_logs append-only

Makes audit_logs tamper-resistant at the database level. Application code only ever INSERTs,
but a bug, a stray SQL console or a compromised endpoint could still rewrite history. These
triggers refuse UPDATE, DELETE and TRUNCATE, with two exceptions the schema itself needs:

* ON DELETE SET NULL (deleting a user): allowed only if actor_id is the one column changing,
  and only to NULL, so history survives the user.
* ON DELETE CASCADE (deleting a whole organization): allowed only once the parent
  organization row is already gone.

Alembic does not track triggers, so `alembic check` is unaffected by this migration.

Revision ID: 0002
Revises: 0001
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION audit_logs_guard() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF EXISTS (SELECT 1 FROM organizations WHERE id = OLD.organization_id) THEN
                    RAISE EXCEPTION 'audit_logs is append-only: rows cannot be deleted';
                END IF;
                RETURN OLD;
            END IF;

            IF OLD.actor_id IS NOT NULL AND NEW.actor_id IS NULL
               AND (NEW.id, NEW.organization_id, NEW.action, NEW.resource_type,
                    NEW.resource_id, NEW.details, NEW.ip_address, NEW.created_at)
                   IS NOT DISTINCT FROM
                   (OLD.id, OLD.organization_id, OLD.action, OLD.resource_type,
                    OLD.resource_id, OLD.details, OLD.ip_address, OLD.created_at)
            THEN
                RETURN NEW;
            END IF;

            RAISE EXCEPTION 'audit_logs is append-only: rows cannot be modified';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_logs_append_only
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit_logs_guard()
        """
    )
    op.execute(
        """
        CREATE FUNCTION audit_logs_block_truncate() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only: table cannot be truncated';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_logs_no_truncate
        BEFORE TRUNCATE ON audit_logs
        FOR EACH STATEMENT EXECUTE FUNCTION audit_logs_block_truncate()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER audit_logs_no_truncate ON audit_logs")
    op.execute("DROP FUNCTION audit_logs_block_truncate()")
    op.execute("DROP TRIGGER audit_logs_append_only ON audit_logs")
    op.execute("DROP FUNCTION audit_logs_guard()")
