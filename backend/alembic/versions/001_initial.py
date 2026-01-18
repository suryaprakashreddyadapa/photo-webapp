"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('role', sa.String(20), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('nas_path', sa.String(500)),
        sa.Column('storage_quota_bytes', sa.BigInteger(), server_default='107374182400'),  # 100GB default
        sa.Column('storage_used_bytes', sa.BigInteger(), server_default='0'),
        sa.Column('verification_token', sa.String(255)),
        sa.Column('reset_token', sa.String(255)),
        sa.Column('reset_token_expires', sa.DateTime(timezone=True)),
        sa.Column('last_login', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )
    
    # User settings table
    op.create_table(
        'user_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('face_recognition_enabled', sa.Boolean(), server_default='true'),
        sa.Column('clip_enabled', sa.Boolean(), server_default='true'),
        sa.Column('yolo_enabled', sa.Boolean(), server_default='true'),
        sa.Column('auto_index', sa.Boolean(), server_default='true'),
        sa.Column('index_interval_hours', sa.Integer(), server_default='24'),
        sa.Column('nas_paths', postgresql.JSONB(), server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )
    
    # Media table
    op.create_table(
        'media',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('original_path', sa.String(1000), nullable=False),
        sa.Column('storage_path', sa.String(1000)),
        sa.Column('thumbnail_path', sa.String(1000)),
        sa.Column('media_type', sa.String(20), nullable=False),  # photo, video
        sa.Column('mime_type', sa.String(100)),
        sa.Column('file_size', sa.BigInteger()),
        sa.Column('width', sa.Integer()),
        sa.Column('height', sa.Integer()),
        sa.Column('duration', sa.Float()),  # For videos
        sa.Column('file_hash', sa.String(64), index=True),  # SHA-256
        sa.Column('perceptual_hash', sa.String(64), index=True),  # pHash for duplicates
        
        # EXIF data
        sa.Column('taken_at', sa.DateTime(timezone=True), index=True),
        sa.Column('camera_make', sa.String(100)),
        sa.Column('camera_model', sa.String(100)),
        sa.Column('lens_model', sa.String(100)),
        sa.Column('focal_length', sa.Float()),
        sa.Column('aperture', sa.Float()),
        sa.Column('iso', sa.Integer()),
        sa.Column('shutter_speed', sa.String(50)),
        
        # Location
        sa.Column('latitude', sa.Float()),
        sa.Column('longitude', sa.Float()),
        sa.Column('altitude', sa.Float()),
        sa.Column('location_name', sa.String(500)),
        
        # AI data
        sa.Column('clip_embedding', Vector(512)),  # CLIP embedding
        sa.Column('tags', postgresql.ARRAY(sa.String(100))),
        sa.Column('objects', postgresql.JSONB()),  # YOLO detections
        sa.Column('faces_count', sa.Integer(), server_default='0'),
        
        # Status
        sa.Column('is_favorite', sa.Boolean(), server_default='false'),
        sa.Column('is_hidden', sa.Boolean(), server_default='false'),
        sa.Column('is_trashed', sa.Boolean(), server_default='false'),
        sa.Column('trashed_at', sa.DateTime(timezone=True)),
        sa.Column('ai_processed', sa.Boolean(), server_default='false'),
        sa.Column('processing_error', sa.Text()),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )
    
    # Create index for vector similarity search
    op.execute('CREATE INDEX media_clip_embedding_idx ON media USING ivfflat (clip_embedding vector_cosine_ops) WITH (lists = 100)')
    
    # Albums table
    op.create_table(
        'albums',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('cover_media_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('media.id', ondelete='SET NULL')),
        sa.Column('is_shared', sa.Boolean(), server_default='false'),
        sa.Column('share_token', sa.String(64)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )
    
    # Album media junction table
    op.create_table(
        'album_media',
        sa.Column('album_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('albums.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('media_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('media.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('position', sa.Integer(), server_default='0'),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    
    # Smart albums table
    op.create_table(
        'smart_albums',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),  # Natural language query
        sa.Column('filters', postgresql.JSONB()),  # Structured filters
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )
    
    # People table (face clusters)
    op.create_table(
        'people',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255)),
        sa.Column('is_named', sa.Boolean(), server_default='false'),
        sa.Column('cover_face_id', postgresql.UUID(as_uuid=True)),
        sa.Column('face_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )
    
    # Faces table
    op.create_table(
        'faces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('media_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('media.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('people.id', ondelete='SET NULL'), index=True),
        sa.Column('embedding', Vector(128)),  # dlib face embedding
        sa.Column('bounding_box', postgresql.JSONB()),  # {x, y, width, height}
        sa.Column('thumbnail_path', sa.String(1000)),
        sa.Column('confidence', sa.Float()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    
    # Create index for face embedding similarity search
    op.execute('CREATE INDEX faces_embedding_idx ON faces USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)')
    
    # Jobs table
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Integer(), server_default='0'),
        sa.Column('total_items', sa.Integer(), server_default='0'),
        sa.Column('processed_items', sa.Integer(), server_default='0'),
        sa.Column('error_message', sa.Text()),
        sa.Column('metadata', postgresql.JSONB()),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    
    # Create indexes
    op.create_index('ix_media_user_taken', 'media', ['user_id', 'taken_at'])
    op.create_index('ix_media_user_created', 'media', ['user_id', 'created_at'])
    op.create_index('ix_media_tags', 'media', ['tags'], postgresql_using='gin')
    op.create_index('ix_jobs_user_status', 'jobs', ['user_id', 'status'])


def downgrade() -> None:
    op.drop_table('jobs')
    op.drop_table('faces')
    op.drop_table('people')
    op.drop_table('smart_albums')
    op.drop_table('album_media')
    op.drop_table('albums')
    op.drop_table('media')
    op.drop_table('user_settings')
    op.drop_table('users')
