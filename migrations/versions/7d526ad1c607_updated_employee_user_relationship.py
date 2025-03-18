from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7d526ad1c607'
down_revision = 'f9cda1f57552'
branch_labels = None
depends_on = None


def upgrade():
    # Ensure the unique constraint has a proper name
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_user_employee_id", ['employee_id'])  # Added constraint name


def downgrade():
    # Drop the unique constraint using the same name
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint("uq_user_employee_id", type_='unique')  # Used the same constraint name
