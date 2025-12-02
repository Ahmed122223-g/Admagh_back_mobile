"""Add challenge and quiz tables

Revision ID: add_challenges_quizzes
Revises: 
Create Date: 2025-11-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_challenges_quizzes'
down_revision = None  # Update this with your latest migration ID
branch_labels = None
depends_on = None


def upgrade():
    # Create quizzes table
    op.create_table('quizzes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('challenge_id', sa.Integer(), nullable=True),
        sa.Column('creator_id', sa.BigInteger(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('passing_score', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quizzes_challenge_id'), 'quizzes', ['challenge_id'], unique=False)
    
    # Create challenges table
    op.create_table('challenges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('creator_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('challenge_type', sa.String(length=20), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('has_quiz', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('quiz_id', sa.Integer(), nullable=True),
        sa.Column('calendar_event_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['calendar_event_id'], ['calendar_events.id'], ),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_challenges_creator_id'), 'challenges', ['creator_id'], unique=False)
    op.create_index(op.f('ix_challenges_challenge_type'), 'challenges', ['challenge_type'], unique=False)
    op.create_index(op.f('ix_challenges_start_time'), 'challenges', ['start_time'], unique=False)
    op.create_index(op.f('ix_challenges_status'), 'challenges', ['status'], unique=False)
    
    # Create quiz_questions table
    op.create_table('quiz_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(length=20), nullable=False),
        sa.Column('question_order', sa.Integer(), nullable=False),
        sa.Column('options', sa.JSON(), nullable=True),
        sa.Column('correct_option_index', sa.Integer(), nullable=True),
        sa.Column('correct_answer_boolean', sa.Boolean(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_questions_quiz_id'), 'quiz_questions', ['quiz_id'], unique=False)
    
    # Create challenge_participants table
    op.create_table('challenge_participants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('challenge_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='invited'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('completion_time_seconds', sa.Integer(), nullable=True),
        sa.Column('quiz_score', sa.Integer(), nullable=True),
        sa.Column('quiz_submitted_at', sa.DateTime(), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('trophy', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['challenge_id'], ['challenges.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_challenge_participants_challenge_id'), 'challenge_participants', ['challenge_id'], unique=False)
    op.create_index(op.f('ix_challenge_participants_user_id'), 'challenge_participants', ['user_id'], unique=False)
    
    # Create challenge_invitations table
    op.create_table('challenge_invitations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('challenge_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.BigInteger(), nullable=False),
        sa.Column('recipient_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['challenge_id'], ['challenges.id'], ),
        sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_challenge_invitations_challenge_id'), 'challenge_invitations', ['challenge_id'], unique=False)
    op.create_index(op.f('ix_challenge_invitations_recipient_id'), 'challenge_invitations', ['recipient_id'], unique=False)
    
    # Create quiz_responses table
    op.create_table('quiz_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('challenge_id', sa.Integer(), nullable=False),
        sa.Column('answers', sa.JSON(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('correct_count', sa.Integer(), nullable=False),
        sa.Column('total_questions', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.Column('time_taken_seconds', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['challenge_id'], ['challenges.id'], ),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_responses_quiz_id'), 'quiz_responses', ['quiz_id'], unique=False)
    op.create_index(op.f('ix_quiz_responses_user_id'), 'quiz_responses', ['user_id'], unique=False)
    op.create_index(op.f('ix_quiz_responses_challenge_id'), 'quiz_responses', ['challenge_id'], unique=False)
    
    # Add challenge statistics to users table
    op.add_column('users', sa.Column('total_challenges', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('users', sa.Column('challenges_won', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('users', sa.Column('individual_challenges_won', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('users', sa.Column('group_challenges_won', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('users', sa.Column('gold_trophies', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('users', sa.Column('silver_trophies', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('users', sa.Column('bronze_trophies', sa.Integer(), nullable=True, server_default='0'))


def downgrade():
    # Drop challenge statistics from users table
    op.drop_column('users', 'bronze_trophies')
    op.drop_column('users', 'silver_trophies')
    op.drop_column('users', 'gold_trophies')
    op.drop_column('users', 'group_challenges_won')
    op.drop_column('users', 'individual_challenges_won')
    op.drop_column('users', 'challenges_won')
    op.drop_column('users', 'total_challenges')
    
    # Drop quiz_responses table
    op.drop_index(op.f('ix_quiz_responses_challenge_id'), table_name='quiz_responses')
    op.drop_index(op.f('ix_quiz_responses_user_id'), table_name='quiz_responses')
    op.drop_index(op.f('ix_quiz_responses_quiz_id'), table_name='quiz_responses')
    op.drop_table('quiz_responses')
    
    # Drop challenge_invitations table
    op.drop_index(op.f('ix_challenge_invitations_recipient_id'), table_name='challenge_invitations')
    op.drop_index(op.f('ix_challenge_invitations_challenge_id'), table_name='challenge_invitations')
    op.drop_table('challenge_invitations')
    
    # Drop challenge_participants table
    op.drop_index(op.f('ix_challenge_participants_user_id'), table_name='challenge_participants')
    op.drop_index(op.f('ix_challenge_participants_challenge_id'), table_name='challenge_participants')
    op.drop_table('challenge_participants')
    
    # Drop quiz_questions table
    op.drop_index(op.f('ix_quiz_questions_quiz_id'), table_name='quiz_questions')
    op.drop_table('quiz_questions')
    
    # Drop challenges table
    op.drop_index(op.f('ix_challenges_status'), table_name='challenges')
    op.drop_index(op.f('ix_challenges_start_time'), table_name='challenges')
    op.drop_index(op.f('ix_challenges_challenge_type'), table_name='challenges')
    op.drop_index(op.f('ix_challenges_creator_id'), table_name='challenges')
    op.drop_table('challenges')
    
    # Drop quizzes table
    op.drop_index(op.f('ix_quizzes_challenge_id'), table_name='quizzes')
    op.drop_table('quizzes')
