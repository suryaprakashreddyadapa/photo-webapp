# PhotoVault System Requirements

## Hardware Requirements

### Minimum Requirements
| Component | Specification |
|-----------|---------------|
| CPU | 4 cores (x86_64) |
| RAM | 8 GB |
| Storage | 50 GB SSD for application + NAS storage for photos |
| Network | Gigabit Ethernet (for NAS access) |

### Recommended Requirements
| Component | Specification |
|-----------|---------------|
| CPU | 8+ cores with AVX2 support |
| RAM | 16 GB or more |
| GPU | NVIDIA GPU with 4GB+ VRAM (optional, for faster AI) |
| Storage | 100 GB NVMe SSD + NAS |
| Network | 2.5 Gigabit Ethernet |

### For Large Libraries (1M+ photos)
| Component | Specification |
|-----------|---------------|
| CPU | 16+ cores |
| RAM | 32 GB or more |
| GPU | NVIDIA RTX 3060 or better |
| Storage | 500 GB NVMe SSD |
| Database | Dedicated PostgreSQL server recommended |

## Software Requirements

### Host System
- **Operating System**: Linux (Ubuntu 22.04 LTS recommended), macOS 12+, or Windows 11 with WSL2
- **Docker**: Version 24.0 or later
- **Docker Compose**: Version 2.20 or later

### For Synology NAS
- **DSM Version**: 7.0 or later
- **Packages**: Container Manager (Docker)
- **RAM**: 8 GB minimum (16 GB recommended)

## Network Requirements

### Ports Used (Internal Only)
| Port | Service | Description |
|------|---------|-------------|
| 3000 | Frontend | React web interface |
| 8000 | Backend | FastAPI REST API |
| 5432 | PostgreSQL | Database (internal) |
| 6379 | Redis | Task queue (internal) |

### Network Isolation
PhotoVault is designed to run in **complete network isolation**:
- No outbound internet connections required
- No telemetry or analytics
- No cloud dependencies
- All AI models run locally
- No external API calls

## Storage Requirements

### Application Storage
| Directory | Purpose | Size Estimate |
|-----------|---------|---------------|
| `/data/thumbnails` | Generated thumbnails | ~10% of original photos |
| `/data/cache` | AI model cache | 2-5 GB |
| `/data/db` | PostgreSQL data | 1 GB per 100K photos |
| `/data/redis` | Redis persistence | 100 MB |

### NAS Storage
- Supports SMB/CIFS protocol
- Read access required for photo scanning
- Write access required for organization features
- Recommended: Dedicated photo share with proper permissions

## Performance Considerations

### AI Processing Speed (per photo)
| Feature | CPU Only | With GPU |
|---------|----------|----------|
| Face Detection | 2-5 sec | 0.1-0.3 sec |
| CLIP Embedding | 1-3 sec | 0.05-0.1 sec |
| YOLO Detection | 3-8 sec | 0.1-0.5 sec |
| Thumbnail Generation | 0.5-1 sec | 0.5-1 sec |

### Concurrent Users
| RAM | Recommended Users |
|-----|-------------------|
| 8 GB | 1-5 users |
| 16 GB | 5-20 users |
| 32 GB | 20-50 users |

## Security Requirements

### Data Privacy
- All data stored locally on your hardware
- No data transmitted to external servers
- Encrypted database connections (internal)
- JWT-based authentication with configurable expiry

### Backup Recommendations
- Regular PostgreSQL backups
- NAS snapshot support
- Configuration file backups
