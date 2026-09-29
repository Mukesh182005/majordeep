# Technology Stack

| Category | Technology | Where Used | Why |
|---|---|---|---|
| **Frontend Framework** | React 18 | Web UI | Component-based UI with hooks, large ecosystem, real-time WebSocket integration |
| **Build Tool** | Vite 5 | Frontend bundling | Fast HMR in development, optimized production builds with code splitting |
| **CSS Framework** | Tailwind CSS 3 | Styling | Utility-first CSS for rapid, consistent UI development |
| **Charts** | Recharts | Data visualization | React-native charting library for signal plots and confidence displays |
| **Animation** | Framer Motion, GSAP | UI transitions | Smooth page transitions and interactive forensic visualizations |
| **Routing** | React Router 6 | Frontend navigation | Client-side routing with nested layouts |
| **Backend Framework** | FastAPI | REST API | Async Python web framework with automatic OpenAPI docs, Pydantic validation |
| **Python** | 3.11+ | Backend runtime | Type hints, performance improvements, required by dependencies |
| **ORM** | SQLAlchemy 2 | Database access | Mature Python ORM with async support and migration tooling |
| **Migrations** | Alembic | Schema management | Database schema versioning and migration |
| **Validation** | Pydantic 2 | Request/response schemas | Data validation, serialization, and settings management |
| **Auth** | python-jose + passlib | JWT + password hashing | Industry-standard JWT token generation and bcrypt password hashing |
| **Task Queue** | Celery 5 | Background jobs | Distributed task queue for long-running ML inference jobs |
| **Message Broker** | Redis 7 | Queue backend | Fast in-memory message broker for Celery (optional — runs inline without it) |
| **Deep Learning** | PyTorch 2 | Neural inference | Leading DL framework with GPU acceleration, model loading, and inference |
| **Image Model** | EfficientNet-B4 | Image classification | High-accuracy CNN with efficient parameter scaling; fine-tuned for deepfake detection |
| **Audio Model** | LCNN (Light CNN) | Audio classification | Lightweight CNN effective for audio spoofing detection |
| **Face Detection** | MTCNN (facenet-pytorch) | Face extraction | Multi-task CNN for face detection, alignment, and cropping |
| **Computer Vision** | OpenCV | Video/image processing | Frame extraction, optical flow, edge detection, image analysis |
| **Reporting** | ReportLab | PDF generation | Programmatic PDF creation for forensic reports |
| **Plotting** | Matplotlib | Evidence charts | Signal visualizations and calibration curves embedded in reports |
| **Image Processing** | Pillow + pillow-heif | Image I/O | Image loading including HEIF/HEIC format support |
| **Database (dev)** | SQLite | Local development | Zero-configuration embedded database |
| **Database (prod)** | PostgreSQL 16 | Production | ACID-compliant relational database with concurrent write support |
| **Containerization** | Docker + Docker Compose | Deployment | Reproducible multi-service deployment (API + Worker + Frontend + DB + Redis) |
| **Web Server (prod)** | Nginx | Frontend serving | Static file serving and reverse proxy in Docker deployment |
| **ASGI Server** | Uvicorn | Backend serving | High-performance ASGI server for FastAPI |
| **Testing** | pytest + Vitest | Backend + Frontend tests | Standard testing frameworks for Python and JavaScript |
| **Linting** | Ruff + ESLint | Code quality | Fast Python linter and JavaScript/React linter |
