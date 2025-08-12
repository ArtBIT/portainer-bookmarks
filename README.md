# Bash-Bookmarks

A small plain text bookmarks manager with a Python HTTP server, Docker support, and web interface.

## Features

- **Bookmark Management**: Add, search, and organize bookmarks
- **Web Interface**: Modern web UI for managing bookmarks
- **Import/Export**: Support for HTML, JSON, CSV, and Pocket exports
- **Docker Ready**: Full Docker containerization with Portainer support
- **API**: RESTful API for programmatic access
- **Search**: Full-text search across bookmarks
- **Categories & Tags**: Organize bookmarks with categories and tags

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd bookmarks

# Start the server
docker-compose up -d

# Access the web interface
open http://localhost:9080
```

### Using Portainer

1. **Upload to Portainer**:
   - In Portainer, go to "Stacks" → "Add stack"
   - Upload the `docker-compose.yml` file
   - Set environment variables if needed
   - Deploy the stack

2. **Environment Variables** (optional):
   ```bash
   PORT=9080                    # Server port
   DEBUG=INFO                   # Log level
   DOMAIN=bookmarks.yourdomain.com  # For Nginx Proxy Manager integration
   
   # Volume Configuration (optional)
   BOOKMARKS_DATA_VOLUME=my_bookmarks_data    # Custom data volume name
   BOOKMARKS_LOGS_VOLUME=my_bookmarks_logs    # Custom logs volume name
   BOOKMARKS_CONFIG_VOLUME=my_bookmarks_config # Custom config volume name
   ```

3. **Access the Application**:
   - Web UI: `http://your-server:9080`
   - API: `http://your-server:9080/search?q=query`

## Docker Compose Variants

### Basic Setup
```bash
docker-compose up -d
```

### Production Setup
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### With Nginx Proxy Manager
```bash
docker-compose -f docker-compose.yml -f docker-compose.nginx-proxy.yml up -d
```

### With External Volumes
```bash
# Pre-create volumes
docker volume create my_bookmarks_data
docker volume create my_bookmarks_logs
docker volume create my_bookmarks_config

# Deploy with external volumes
docker-compose -f docker-compose.yml -f docker-compose.external-volumes.yml up -d
```

### Development Setup
```bash
cp docker-compose.override.yml.example docker-compose.override.yml
docker-compose up -d
```

## Data Management

### Docker Volumes
The application uses Docker volumes for data persistence:

- **`bookmarks_data`** (default): Bookmarks storage (`/data/bookmarks`)
- **`bookmarks_logs`** (default): Server logs (`/data/logs`)
- **`bookmarks_config`** (default): Configuration files (`/app/config`)

### Volume Configuration Options

#### **1. Default Volumes (Recommended)**
```bash
# Uses default volume names: bookmarks_data, bookmarks_logs, bookmarks_config
docker-compose up -d
```

#### **2. Custom Volume Names**
```bash
# Set environment variables for custom volume names
BOOKMARKS_DATA_VOLUME=my_data \
BOOKMARKS_LOGS_VOLUME=my_logs \
BOOKMARKS_CONFIG_VOLUME=my_config \
docker-compose up -d
```

#### **3. Stack Name-Based Volumes**
```bash
# Use template for stack name-based volumes
cp docker-compose.template.yml docker-compose.yml
# Edit docker-compose.yml and set STACK_NAME=your-stack-name
docker-compose up -d
```

#### **4. External Volumes**
```bash
# Pre-create volumes
docker volume create my_bookmarks_data
docker volume create my_bookmarks_logs
docker volume create my_bookmarks_config

# Deploy with external volumes
BOOKMARKS_DATA_VOLUME=my_bookmarks_data \
BOOKMARKS_LOGS_VOLUME=my_bookmarks_logs \
BOOKMARKS_CONFIG_VOLUME=my_bookmarks_config \
docker-compose -f docker-compose.yml -f docker-compose.external-volumes.yml up -d
```

### Setting Up Configuration (After Deployment)

After deploying in Portainer, set up your configuration:

```bash
# Run the setup script (replace 'bookmarks' with your stack name)
./setup-volumes.sh bookmarks

# Or manually create configuration
docker run --rm -v bookmarks_bookmarks_config:/config alpine sh -c \
  'echo "BOOKMARKS_DIR=/data/bookmarks" > /config/.bookmarks.env'
```

### Managing Data

**View bookmarks data:**
```bash
docker run --rm -v bookmarks_bookmarks_data:/data alpine ls -la /data
```

**View logs:**
```bash
docker run --rm -v bookmarks_bookmarks_logs:/data alpine ls -la /data
```

**Edit configuration:**
```bash
docker run --rm -v bookmarks_bookmarks_config:/config -it alpine sh -c \
  'apk add --no-cache nano && nano /config/.bookmarks.env'
```

## API Usage

### Search Bookmarks
```bash
# Search by query
curl "http://localhost:9080/search?q=python&format=json"

# Search with different formats
curl "http://localhost:9080/search?q=python&format=html"
curl "http://localhost:9080/search?q=python&format=text"
```

### Add Bookmark
```bash
curl -X POST "http://localhost:9080/add" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "url=https://example.com&title=Example&category=test&tags=example"
```

### Import Bookmarks
```bash
# Use the web interface at http://localhost:9080/import
# Or upload files via the web form
```

## File Structure

```
bookmarks/
├── docker-compose.yml                    # Main compose file
├── docker-compose.prod.yml              # Production overrides
├── docker-compose.nginx-proxy.yml       # Nginx Proxy Manager integration
├── docker-compose.external-volumes.yml  # External volumes configuration
├── docker-compose.template.yml          # Template for stack name-based volumes
├── docker-compose.override.yml          # Development overrides
├── env.example                          # Environment variables template
├── setup-volumes.sh                     # Volume setup script
├── docker/                              # Docker build context
│   ├── Dockerfile                       # Container definition
│   ├── bookmarks-server.py              # Python HTTP server
│   ├── bookmarks_manager.py             # Bookmark management logic
│   ├── bookmarks_importer.py            # Import functionality
│   ├── config.py                        # Configuration
│   ├── static/                          # Web assets
│   ├── data/                            # Bookmarks data (not in container)
│   └── logs/                            # Server logs (not in container)
├── NGINX_PROXY_GUIDE.md                # Nginx Proxy Manager guide
└── README.md                            # This file
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `9080` | Server port |
| `DEBUG` | `INFO` | Log level |
| `BOOKMARKS_DIR` | `/data/bookmarks` | Bookmarks data directory |
| `LOG_FILE` | `/data/logs/bookmarks-server.log` | Log file path |
| `BOOKMARKS_DATA_VOLUME` | `bookmarks_data` | Data volume name |
| `BOOKMARKS_LOGS_VOLUME` | `bookmarks_logs` | Logs volume name |
| `BOOKMARKS_CONFIG_VOLUME` | `bookmarks_config` | Config volume name |

### Port Configuration

Change the server port:

```bash
# Using environment variable
PORT=9090 docker-compose up -d

# Using the set-port script
cd docker
./set-port.sh 9090
```

## Development

### Local Development
```bash
# Clone and setup
git clone <repository-url>
cd bookmarks

# Start development environment
cp docker-compose.override.yml.example docker-compose.override.yml
docker-compose up -d

# View logs
docker-compose logs -f bookmarks-server
```

### Building from Source
```bash
cd docker
docker build -t bookmarks-server .
docker run -p 9080:9080 bookmarks-server
```

## Troubleshooting

### Port Conflicts
```bash
# Check if port is in use
netstat -tlnp | grep :9080

# Change port
PORT=9090 docker-compose up -d
```

### Permission Issues
```bash
# Fix data directory permissions
sudo chown -R 1000:1000 docker/data docker/logs
```

### Health Check Failures
```bash
# Check container logs
docker-compose logs bookmarks-server

# Restart container
docker-compose restart bookmarks-server
```

### Volume Issues
```bash
# Check volume status
docker volume ls | grep bookmarks

# Inspect volume contents
docker run --rm -v bookmarks_bookmarks_data:/data alpine ls -la /data

# Create missing volumes
docker volume create bookmarks_bookmarks_data
docker volume create bookmarks_bookmarks_logs
docker volume create bookmarks_bookmarks_config
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Docker
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
