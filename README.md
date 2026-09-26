# Bash-Bookmarks

**Your bookmarks. Your server. In your pocket.**

A self-hosted bookmarks service that keeps every link as a plain markdown file you own, with a web app you can install on your phone and share links to straight from any app.

![Bash-Bookmarks on a phone: search, saving a shared link, and dark mode](docs/pwa-screenshot.png)

## Why self-host your bookmarks?

**Save anything in two taps.** Install the web app on your Android phone and "Bookmarks" shows up in the share sheet, right next to your messaging apps. Found a great article in Chrome, a video on YouTube, a thread on Reddit? Tap **Share**, tap **Bookmarks**, and the link and title are already filled in. Pick a category, hit Save, and get back to what you were doing.

**Your data is just files.** Every bookmark is a small markdown file in a folder named after its category. No database, no proprietary format, no lock-in. Back it up with rsync, version it with git, grep it from a terminal, or open the folder in Obsidian or any editor. If this project vanished tomorrow, your bookmarks would still be perfectly readable.

**No accounts, no ads, no telemetry.** Bookmark services come and go (goodbye, Pocket), and free ones tend to pay for themselves with your reading habits. This one runs on your own hardware and answers only to you.

**One library, every device.** The same server powers the phone app, the [bash-bookmarks](https://github.com/ArtBIT/bash-bookmarks) CLI and its Firefox add-on. Save a link on your phone during the commute, then pull it up from your terminal at your desk.

**Feels like a real app.** It launches full screen from your home screen, follows your phone's light or dark mode, and searches as you type across titles, URLs, categories and tags.

**Bring your history along.** Import browser bookmark exports (HTML), JSON, CSV or a Pocket export, and export everything back out whenever you like.

**Boring to run, in the best way.** A single small Python container that needs nothing beyond the standard library. Deploy it as a Portainer stack straight from this repository, put it behind Nginx Proxy Manager, and forget about it.

> Sharing from other apps works on Android (Chrome). On iPhone you can still add the web app to your home screen and add bookmarks from inside it.

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
   ```

3. **Access the Application**:
   - Web UI: `http://your-server:9080`
   - API: `http://your-server:9080/search?q=query`

### Deploying from this repository in Portainer

Portainer can build the stack straight from GitHub and redeploy when `main` changes:

1. **Stacks** > **Add stack** > **Repository**
2. Repository URL: `https://github.com/ArtBIT/portainer-bookmarks`, reference: `refs/heads/main`, compose path: `docker-compose.yml`
3. Bookmarks, logs and config are stored in host folders under `/portainer/Files/AppData/Config/bookmarks/` (see `docker-compose.yml`); change the paths there if your server uses a different location.
4. Optionally enable **GitOps updates** so Portainer redeploys on new commits.

If a stack with the same `container_name` already runs, stop or remove it first; bind-mounted host folders are not touched.

## Web UI and Android app (PWA)

![Web UI: searching bookmarks, saving a link shared from another app, and dark mode](docs/pwa-screenshot.png)

The server hosts a mobile friendly web UI at `http://your-server:9080/` for searching, adding and removing bookmarks, with links to the import and export pages.

The web UI can be installed as an app on Android, and then shows up in the native share sheet: share any link to "Bookmarks" and it opens the add form prefilled with the URL and title.

Android only installs PWAs served over HTTPS (or `localhost`), so put the server behind HTTPS first:

- **Nginx Proxy Manager:** add a proxy host with scheme `http`, forward host your server and port `9080`, and an SSL certificate the phone trusts. The server itself speaks plain HTTP, so the scheme must be `http`, not `https`.
- [Tailscale](https://tailscale.com/kb/1312/serve): `tailscale serve --bg 9080`, then open `https://<machine>.<tailnet>.ts.net` on the phone.
- Built in TLS: set `BOOKMARKS_TLS_CERT` and `BOOKMARKS_TLS_KEY` to a certificate and key the phone trusts.

Then open the URL in Chrome on Android, tap the menu and choose "Install app" (or "Add to Home screen").

The web UI has no authentication, so do not expose it to the public internet.

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

### With Custom Volume Names
```bash
# Set environment variables for custom volume names
BOOKMARKS_DATA_VOLUME=my_data \
BOOKMARKS_LOGS_VOLUME=my_logs \
BOOKMARKS_CONFIG_VOLUME=my_config \
docker-compose -f docker-compose.yml -f docker-compose.custom-volumes.yml up -d
```

### With External Volumes
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

### Development Setup
```bash
cp docker-compose.override.yml.example docker-compose.override.yml
docker-compose up -d
```

## Data Management

### Host folders
`docker-compose.yml` bind-mounts host folders for data persistence:

- **`/portainer/Files/AppData/Config/bookmarks/data`**: Bookmarks storage (`/data/bookmarks`)
- **`/portainer/Files/AppData/Config/bookmarks/logs`**: Server logs (`/data/logs`)
- **`/portainer/Files/AppData/Config/bookmarks/config`**: Configuration files (`/app/config`)

The options below describe setups with Docker volumes instead.

### Volume Configuration Options

#### **1. Default Volumes (Recommended)**
```bash
# Uses default volume names: bookmarks_data, bookmarks_logs, bookmarks_config
docker-compose up -d
```

#### **2. Custom Volume Names**
```bash
# Use the custom volumes override file
BOOKMARKS_DATA_VOLUME=my_data \
BOOKMARKS_LOGS_VOLUME=my_logs \
BOOKMARKS_CONFIG_VOLUME=my_config \
docker-compose -f docker-compose.yml -f docker-compose.custom-volumes.yml up -d
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
  --data-urlencode "url=https://example.com/?a=1&b=2" \
  --data-urlencode "title=Example" \
  --data-urlencode "category=test" \
  --data-urlencode "tags=example"
```

Parameters are URL-decoded, so values containing `&`, `+` or spaces must be encoded (`--data-urlencode` does that).

### Web UI API

The web UI uses these JSON endpoints:

- `GET /api/search?q=searchterm`
- `POST /api/add` with a JSON body `{url, title, category, tags}`
- `DELETE /api/remove` with a JSON body `{id}`

### Import Bookmarks
```bash
# Use the web interface at http://localhost:9080/import
# Or upload files via the web form
```

## File Structure

```
bookmarks/
├── docker-compose.yml                    # Main compose file (fixed volumes)
├── docker-compose.prod.yml              # Production overrides
├── docker-compose.nginx-proxy.yml       # Nginx Proxy Manager integration
├── docker-compose.custom-volumes.yml    # Custom volume names
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
| `BOOKMARKS_DATA_VOLUME` | `bookmarks_data` | Data volume name (with custom-volumes.yml) |
| `BOOKMARKS_LOGS_VOLUME` | `bookmarks_logs` | Logs volume name (with custom-volumes.yml) |
| `BOOKMARKS_CONFIG_VOLUME` | `bookmarks_config` | Config volume name (with custom-volumes.yml) |

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
