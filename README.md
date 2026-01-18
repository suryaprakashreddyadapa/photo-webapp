# PhotoVault

A production-ready, self-hosted photo management system with local AI capabilities, optimized for Synology NAS deployment. Think Google Photos, but running entirely on your own hardware with complete privacy.

![PhotoVault](https://img.shields.io/badge/version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

## Features

### 🔒 Authentication & Users
- Email signup with verification
- Admin approval workflow before account activation
- JWT-based authentication with role-based access (admin/user)
- Per-user NAS folder mapping
- Admin dashboard for user management

### 🤖 Local AI Features (No Cloud Required)
- **Face Recognition**: Powered by dlib - detect, embed, and group faces automatically
- **Semantic Tagging**: CLIP-based auto-tagging for intelligent photo categorization
- **Object Detection**: YOLO-powered object detection in photos
- **Natural Language Search**: Search photos using natural language ("Show me photos from the beach")
- All AI processing runs locally on your hardware

### 🗂️ Media & NAS Integration
- Synology NAS integration via SMB/CIFS
- Automatic scanning and indexing of user folders
- Background job queue for processing
- Duplicate detection using perceptual hashing
- Scales to 1M+ photos and 100K+ videos
- PostgreSQL with pgvector for efficient vector search

### 🧠 Ask Tab (AI Assistant)
- Natural language photo search
- Voice-like commands:
  - "Create folder Summer 2024"
  - "Delete album Old"
  - "Find photos with dogs"
- Save queries as smart albums

### ⚙️ Settings
- NAS path configuration
- Re-index controls
- AI feature toggles (Face/CLIP/YOLO)
- Performance and advanced options

### 🎨 Frontend
- Modern React + TypeScript interface
- Clean, aesthetic UI with dark mode
- Collapsible sidebar navigation
- Tabs: Home, Photos, Albums, People, Ask, Timeline, Map, Settings
- Admin tab (admins only)
- Responsive design

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PhotoVault                               │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (React + TypeScript + TailwindCSS)                    │
│  ├── Home Dashboard                                              │
│  ├── Photo Gallery with Grid/Timeline views                     │
│  ├── Albums & Smart Albums                                       │
│  ├── People (Face Recognition)                                   │
│  ├── Ask (AI Assistant)                                          │
│  ├── Map View                                                    │
│  ├── Settings                                                    │
│  └── Admin Panel                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + Python)                                      │
│  ├── REST API                                                    │
│  ├── JWT Authentication                                          │
│  ├── Media Processing                                            │
│  └── AI Services (CLIP, dlib, YOLO)                             │
├─────────────────────────────────────────────────────────────────┤
│  Workers (Celery)                                                │
│  ├── NAS Scanning                                                │
│  ├── Thumbnail Generation                                        │
│  ├── Face Recognition                                            │
│  ├── CLIP Embedding                                              │
│  └── Object Detection                                            │
├─────────────────────────────────────────────────────────────────┤
│  Database (PostgreSQL + pgvector)                                │
│  └── Redis (Task Queue & Cache)                                  │
├─────────────────────────────────────────────────────────────────┤
│  Storage                                                         │
│  ├── Synology NAS (via SMB/CIFS)                                │
│  ├── Thumbnails                                                  │
│  └── AI Model Cache                                              │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- 8GB+ RAM recommended (for AI processing)
- Synology NAS or local photo storage

### One-Command Startup

```bash
# Clone the repository
git clone https://github.com/yourusername/photovault.git
cd photovault

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings (especially NAS_PATH and passwords)

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### First-Time Setup

1. Access the application at http://localhost:3000
2. Log in with the default admin credentials (from .env):
   - Email: admin@photovault.local
   - Password: admin123
3. Change the admin password immediately
4. Configure NAS paths in Admin > Settings
5. Trigger initial scan

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | Database password | `photovault_secret` |
| `SECRET_KEY` | JWT signing key | (generate one!) |
| `NAS_PATH` | Path to NAS mount | `/path/to/nas` |
| `FIRST_ADMIN_EMAIL` | Initial admin email | `admin@photovault.local` |
| `FIRST_ADMIN_PASSWORD` | Initial admin password | `admin123` |
| `FACE_RECOGNITION_ENABLED` | Enable face detection | `true` |
| `CLIP_ENABLED` | Enable CLIP tagging | `true` |
| `YOLO_ENABLED` | Enable object detection | `true` |

See `.env.example` for all options.

### Synology NAS Setup

#### Option 1: Direct Mount (Recommended)
Mount your Synology NAS share on the Docker host:

```bash
# Create mount point
sudo mkdir -p /mnt/nas/photos

# Mount NAS (add to /etc/fstab for persistence)
sudo mount -t cifs //NAS_IP/photos /mnt/nas/photos -o username=USER,password=PASS

# Update .env
NAS_PATH=/mnt/nas/photos
```

#### Option 2: SMB in Container
Configure SMB credentials in `.env`:

```env
SMB_SERVER=192.168.1.100
SMB_SHARE=photos
SMB_USERNAME=your_user
SMB_PASSWORD=your_password
```

## Development

### Local Development Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
pnpm install
pnpm dev

# Workers
celery -A app.workers.celery_app worker --loglevel=info
```

### Project Structure

```
photovault/
├── backend/
│   ├── app/
│   │   ├── api/           # API routes
│   │   ├── core/          # Config, security
│   │   ├── db/            # Database session
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   │   ├── ai/        # AI services (CLIP, dlib, YOLO)
│   │   │   ├── media/     # Media processing
│   │   │   └── nas/       # NAS integration
│   │   └── workers/       # Celery tasks
│   ├── alembic/           # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── services/      # API client
│   │   ├── store/         # Zustand stores
│   │   └── types/         # TypeScript types
│   ├── Dockerfile
│   └── package.json
├── docker/
│   └── init-db.sql
├── docker-compose.yml
├── .env.example
└── README.md
```

## API Documentation

Interactive API documentation is available at `/docs` (Swagger UI) or `/redoc` (ReDoc).

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | POST | User login |
| `/api/auth/register` | POST | User registration |
| `/api/media` | GET | List media |
| `/api/media/{id}` | GET | Get media details |
| `/api/albums` | GET/POST | List/create albums |
| `/api/people` | GET | List detected people |
| `/api/search` | GET | Search media |
| `/api/search/ask` | POST | AI assistant query |
| `/api/admin/users` | GET | List users (admin) |

## Performance Tuning

### For Large Libraries (100K+ photos)

1. **Increase worker memory**:
   ```yaml
   # docker-compose.yml
   worker:
     deploy:
       resources:
         limits:
           memory: 16G
   ```

2. **Add more workers**:
   ```bash
   docker-compose up -d --scale worker=4
   ```

3. **Optimize PostgreSQL**:
   ```sql
   -- Increase work_mem for vector operations
   ALTER SYSTEM SET work_mem = '256MB';
   ALTER SYSTEM SET maintenance_work_mem = '512MB';
   ```

### Hardware Recommendations

| Library Size | RAM | CPU | Storage |
|-------------|-----|-----|---------|
| < 10K photos | 4GB | 2 cores | SSD recommended |
| 10K-100K | 8GB | 4 cores | SSD required |
| 100K-1M | 16GB+ | 8+ cores | NVMe SSD |
| 1M+ | 32GB+ | 16+ cores | NVMe RAID |

## Troubleshooting

### Common Issues

**AI processing is slow**
- Ensure adequate RAM (8GB minimum)
- Check if models are cached (`model_cache` volume)
- Consider disabling unused AI features

**NAS connection fails**
- Verify NAS is accessible from Docker host
- Check SMB credentials
- Ensure proper permissions on NAS share

**Database connection errors**
- Wait for PostgreSQL to fully start
- Check `docker-compose logs db`

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f worker
```

## Security Considerations

1. **Change default passwords** in production
2. **Use HTTPS** with a reverse proxy (nginx, Traefik)
3. **Secure your NAS** with proper permissions
4. **Regular backups** of PostgreSQL data
5. **Keep Docker images updated**

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [dlib](http://dlib.net/) - Face recognition
- [OpenAI CLIP](https://github.com/openai/CLIP) - Semantic understanding
- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) - Object detection
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity search
