"""add colums limit for account

Revision ID: c3894341ba4f
Revises: cd22069b3fc9
Create Date: 2025-01-13 22:56:40.358717

"""
from alembic import op
import models as models
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3894341ba4f'
down_revision = 'cd22069b3fc9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('max_vector_space', sa.Integer(), server_default=sa.text('5'), nullable=False))
        batch_op.add_column(sa.Column('max_annotation_quota_limit', sa.Integer(), server_default=sa.text('10'), nullable=False))
        batch_op.add_column(sa.Column('max_documents_upload_quota', sa.Integer(), server_default=sa.text('50'), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.drop_column('max_documents_upload_quota')
        batch_op.drop_column('max_annotation_quota_limit')
        batch_op.drop_column('max_vector_space')

    # ### end Alembic commands ###
