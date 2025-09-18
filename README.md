# Term MCP DeepSeek - Production-Ready MCP Server

[![Trust Score](https://archestra.ai/mcp-catalog/api/badge/quality/OthmaneBlial/term_mcp_deepseek)](https://archestra.ai/mcp-catalog/othmaneblial__term_mcp_deepseek)

A **complete, production-ready MCP (Model Context Protocol) server** that provides AI-powered terminal access with DeepSeek integration. This server offers full MCP protocol compliance with enterprise-grade security, real-time streaming, and comprehensive tooling for terminal operations.

## ✨ Key Features

- **🔧 Full MCP Protocol Support** - Complete implementation of all MCP features (Tools, Prompts, Resources, Roots, Logging)
- **🔐 Enterprise Security** - OAuth2 authentication, rate limiting, input validation, and security headers
- **⚡ Real-time Streaming** - Server-Sent Events for live command execution and terminal output
- **🚀 Production Ready** - Docker containerization, CI/CD pipeline, comprehensive testing
- **🔄 Multiple Transports** - HTTP REST API and STDIO command-line interface
- **📊 Advanced Monitoring** - Health checks, structured logging, and performance metrics
- **🎨 Modern UI** - Responsive web interface with real-time updates and error handling

## Features

- **Modern Chat Interface:** Responsive web-based chat client with real-time updates, error handling, and session management.

- **AI Integration:** Uses the DeepSeek API to generate intelligent responses with terminal command execution capabilities.

- **Advanced Terminal Command Execution:** Executes shell commands via persistent sessions with real-time output streaming and security controls.

- **Full MCP Protocol Support:** Complete implementation of MCP protocol with tools, prompts, resources, roots, and logging.

- **Multiple Transport Options:** Supports both HTTP and STDIO transports for maximum compatibility.

- **OAuth2 Authentication:** Secure client credentials authentication with configurable access controls.

- **Real-time Streaming:** Server-Sent Events for live command execution updates and terminal output.

- **Comprehensive Security:** Rate limiting, input validation, security headers, and threat detection.

- **Modular Architecture:** Well-organized codebase with separate modules for different concerns.

- **Production Ready:** Docker containerization, CI/CD pipeline, comprehensive testing, and monitoring.

## Project Structure

```
term_mcp_deepseek/
├── config.py                 # Configuration management
├── server.py                 # Main Flask application
├── stdio_server.py          # STDIO transport server
├── mcp_server.py            # MCP protocol implementation
├── api/
│   └── routes.py            # API route handlers
├── models/
│   └── conversation_store.py # Session and conversation management
├── tools/
│   ├── auth.py              # OAuth2 authentication
│   ├── json_rpc.py          # JSON-RPC protocol handling
│   ├── error_handler.py     # Comprehensive error handling
│   ├── rate_limiter.py      # Rate limiting and security
│   ├── sse_manager.py       # Server-Sent Events management
│   ├── input_validator.py   # Input validation and sanitization
│   ├── command_executor.py  # Terminal command execution
│   ├── tty_output_reader.py # Terminal output reading
│   ├── send_control_character.py # Control character handling
│   └── utils.py             # Utility functions
├── static/
│   └── chat.html            # Modern web interface
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Test fixtures and configuration
│   ├── test_input_validator.py    # Input validation tests
│   ├── test_json_rpc.py     # JSON-RPC protocol tests
│   └── test_api_integration.py   # API integration tests
├── .github/
│   └── workflows/
│       └── ci.yml           # CI/CD pipeline
├── Dockerfile               # Docker containerization
├── docker-compose.yml       # Docker Compose configuration
├── requirements.txt         # Python dependencies
├── pytest.ini              # Test configuration
├── startup.sh              # Startup script with port management
├── .env.example            # Environment variables template
└── README.md               # This documentation
```

## Getting Started

### Prerequisites

- Python 3.8+
- [pip](https://pip.pypa.io/)
- A valid DeepSeek API key

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/OthmaneBlial/term_mcp_deepseek.git
   cd term_mcp_deepseek
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install the required dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**

   Copy the example environment file and configure your settings:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set your DeepSeek API key and other configuration options:

   ```bash
   # Required: Set your DeepSeek API key
   DEEPSEEK_API_KEY=your_deepseek_api_key_here

   # Optional: Adjust other settings as needed
   DEBUG=false
   LOG_LEVEL=INFO
   ```

### Running the Server

#### Quick Start (Recommended)

Use the provided startup script for the best experience:

```bash
# Make script executable (first time only)
chmod +x startup.sh

# Start with automatic port detection
./startup.sh

# Start on specific port
./startup.sh -p 8080

# Start with Docker
./startup.sh -m docker

# Start STDIO mode
./startup.sh -m stdio
```

The startup script will:

- ✅ Check Python version compatibility
- ✅ Set up virtual environment automatically
- ✅ Find available ports if default is in use
- ✅ Validate environment configuration
- ✅ Perform health checks
- ✅ Provide helpful status information

#### Manual Startup Options

##### HTTP Transport (Web Interface)

Run the Flask server directly:

```bash
python server.py
```

Visit [http://127.0.0.1:5000](http://127.0.0.1:5000) to access the modern chat interface.

##### STDIO Transport (Command Line)

For command-line integration or MCP clients that prefer STDIO:

```bash
python stdio_server.py
```

This mode is ideal for:

- Command-line tools and scripts
- Integration with other MCP-compatible systems
- Environments where HTTP is not preferred

##### Docker Deployment

Using Docker Compose (recommended for production):

```bash
docker-compose up -d
```

Or using Docker directly:

```bash
docker build -t term-mcp-deepseek .
docker run -p 5000:5000 -e DEEPSEEK_API_KEY=your_key term-mcp-deepseek
```

#### Startup Script Commands

```bash
# Start server (default)
./startup.sh start

# Stop server
./startup.sh stop

# Restart server
./startup.sh restart

# Check status
./startup.sh status

# View logs
./startup.sh logs

# Show help
./startup.sh --help
```

#### Startup Script Options

```bash
# Specify startup mode
./startup.sh -m docker          # Docker mode
./startup.sh -m stdio           # STDIO mode
./startup.sh -m http            # HTTP mode (default)

# Specify host and port
./startup.sh -h 0.0.0.0 -p 8080

# Disable automatic port finding
./startup.sh --no-auto-port

# Verbose output
./startup.sh -v
```

#### Startup Script Features

The `startup.sh` script provides:

- 🔍 **Automatic Port Detection** - Finds available ports if default is in use
- 🐍 **Python Version Check** - Ensures compatible Python version
- 🌐 **Virtual Environment Setup** - Creates and manages venv automatically
- ⚙️ **Environment Validation** - Checks .env configuration
- ❤️ **Health Checks** - Verifies server is running correctly
- 📊 **Status Monitoring** - Shows server status and logs
- 🐳 **Docker Integration** - Handles Docker and Docker Compose
- 🔄 **Process Management** - Proper start/stop/restart functionality
- 📝 **Comprehensive Logging** - Colored output with detailed information
- 🛡️ **Error Handling** - Graceful error handling and recovery

## API Documentation

### Authentication

The server uses OAuth2 client credentials flow for authentication. All API endpoints (except `/health` and `/mcp/info`) require authentication.

#### Getting Access Token

```bash
curl -X POST http://localhost:5000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=mcp_client&client_secret=mcp_secret"
```

Response:

```json
{
  "access_token": "your_access_token_here",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

#### Using Access Token

Include the token in the Authorization header:

```bash
curl -H "Authorization: Bearer your_access_token_here" \
     http://localhost:5000/chat
```

### Endpoints

#### Chat Endpoint

- **URL:** `/chat`
- **Method:** `POST`
- **Authentication:** Required
- **Payload:**
  ```json
  {
    "message": "List files in current directory"
  }
  ```
- **Response:**
  ```json
  {
    "message": "I'll help you list the files in the current directory.\n\n(Ran: ls -la)\ntotal 48\ndrwxr-xr-x  12 user  staff   384 Dec 15 10:30 .\ndrwxr-xr-x   5 user  staff   160 Dec 15 09:45 ..\n-rw-r--r--   1 user  staff  1024 Dec 15 10:25 README.md\n...",
    "session_id": "abc123..."
  }
  ```

#### MCP Endpoints

##### List Tools

- **URL:** `/mcp/list_tools`
- **Method:** `POST`
- **Authentication:** Required
- **Response:**
  ```json
  {
    "tools": [
      {
        "name": "write_to_terminal",
        "description": "Writes text to the active terminal session",
        "inputSchema": {
          "type": "object",
          "properties": {
            "command": {
              "type": "string",
              "description": "The command to run"
            }
          },
          "required": ["command"]
        }
      }
    ]
  }
  ```

##### Call Tool

- **URL:** `/mcp/call_tool`
- **Method:** `POST`
- **Authentication:** Required
- **Payload:**
  ```json
  {
    "name": "write_to_terminal",
    "arguments": {
      "command": "echo 'Hello World'"
    }
  }
  ```
- **Response:**
  ```json
  {
    "content": [
      {
        "type": "text",
        "text": "1 lines were output after sending the command to the terminal..."
      }
    ]
  }
  ```

##### JSON-RPC MCP Endpoint

- **URL:** `/mcp/jsonrpc`
- **Method:** `POST`
- **Authentication:** Required
- **Payload:**
  ```json
  {
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }
  ```

#### Real-time Streaming

- **URL:** `/stream?session_id=your_session_id`
- **Method:** `GET`
- **Authentication:** Required
- **Description:** Server-Sent Events endpoint for real-time command output

#### Session Management

- **URL:** `/sessions`
- **Method:** `GET`
- **Authentication:** Required
- **Description:** Get user's active sessions

- **URL:** `/sessions/{session_id}`
- **Method:** `DELETE`
- **Authentication:** Required
- **Description:** End a specific session

#### Health Check

- **URL:** `/health`
- **Method:** `GET`
- **Authentication:** Not required
- **Response:**
  ```json
  {
    "status": "healthy",
    "service": "term-mcp-deepseek",
    "version": "1.0.0"
  }
  ```

#### Server Information

- **URL:** `/mcp/info`
- **Method:** `GET`
- **Authentication:** Not required
- **Description:** Get server capabilities and information

## Configuration

### Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | - | Your DeepSeek API key (required) |
| `HOST` | `127.0.0.1` | Server host |
| `PORT` | `5000` | Server port |
| `DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FILE` | `logs/term_mcp_deepseek.log` | Log file path |
| `OAUTH_CLIENT_ID` | `mcp_client` | OAuth2 client ID |
| `OAUTH_CLIENT_SECRET` | `mcp_secret` | OAuth2 client secret |
| `SESSION_TIMEOUT` | `3600` | Session timeout in seconds |
| `MAX_COMMAND_LENGTH` | `1000` | Maximum command length |

### OAuth2 Configuration

The server includes built-in OAuth2 support. Default credentials:

- **Client ID:** `mcp_client`
- **Client Secret:** `mcp_secret`

For production, set custom values using environment variables.

## Deployment

### Docker Deployment

1. **Build the image:**

   ```bash
   docker build -t term-mcp-deepseek .
   ```

2. **Run with Docker:**

   ```bash
   docker run -p 5000:5000 \
     -e DEEPSEEK_API_KEY=your_api_key \
     term-mcp-deepseek
   ```

3. **Using Docker Compose:**

   ```bash
   # Set your API key in .env file
   echo "DEEPSEEK_API_KEY=your_api_key" > .env

   # Start the service
   docker-compose up -d
   ```

### Traditional Deployment

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**

   ```bash
   export DEEPSEEK_API_KEY=your_api_key
   export DEBUG=false
   ```

3. **Run the server:**
   ```bash
   python server.py
   ```

### Production Considerations

- Use a reverse proxy (nginx) for SSL termination
- Set up proper logging and monitoring
- Use environment variables for all configuration
- Implement proper backup strategies
- Consider using a database for session storage in high-traffic scenarios

## MCP Protocol Support

This server provides **complete MCP protocol compliance** with all required features:

### ✅ Fully Implemented Features

#### Core MCP Protocol

- **JSON-RPC 2.0** complete implementation
- **Proper error handling** with structured error codes
- **Request/response validation** and sanitization
- **Protocol versioning** and backward compatibility

#### Tools API

- `tools/list` - Discover available tools
- `tools/call` - Execute terminal operations
  - `write_to_terminal` - Execute shell commands
  - `read_terminal_output` - Read terminal buffer
  - `send_control_character` - Send control signals (Ctrl+C, etc.)

#### Prompts API

- `prompts/list` - List available prompt templates
- `prompts/get` - Retrieve specific prompt templates
  - `terminal_help` - General terminal assistance
  - `file_operations` - File and directory operations
  - `system_info` - System information gathering
  - `process_management` - Process control and monitoring

#### Resources API

- `resources/list` - Discover accessible resources
- `resources/read` - Access resource content
  - File system resources (`file://` URIs)
  - Terminal output buffer (`terminal://output`)
  - System information (`system://info`)

#### Roots API

- `roots/list` - Define accessible root directories
  - Current working directory
  - User home directory
  - System root directory
  - Git project root (auto-detected)

#### Logging API

- **Comprehensive logging system** with multiple loggers
- **Security event logging** for audit trails
- **Performance monitoring** and error tracking
- **Configurable log levels** and rotation

### 🔄 Transport Options

#### HTTP Transport

- **RESTful endpoints** for all MCP operations
- **OAuth2 authentication** with client credentials
- **CORS support** for web applications
- **Security headers** and rate limiting
- **Session management** with persistence

#### STDIO Transport

- **Command-line integration** via standard streams
- **Streaming JSON-RPC** messages
- **Background operation** support
- **Process isolation** for security

### 🔒 Security & Authentication

#### OAuth2 Implementation

- **Client credentials flow** for secure authentication
- **Token-based access control** with expiration
- **Configurable client management**
- **Secure token storage** and validation

#### Security Features

- **Rate limiting** with token bucket and sliding window
- **Input validation** and sanitization
- **SQL injection prevention**
- **XSS protection** and content filtering
- **Security headers** (CSP, HSTS, etc.)
- **Request size limits** and payload validation

### 📊 Monitoring & Observability

#### Health Checks

- **Service health monitoring** (`/health` endpoint)
- **Dependency status** checking
- **Performance metrics** collection

#### Logging & Tracing

- **Structured logging** with JSON format
- **Request/response tracing**
- **Error tracking** and alerting
- **Security event monitoring**

### 🚀 Production Features

#### Deployment Ready

- **Docker containerization** with optimized images
- **CI/CD pipeline** with automated testing
- **Environment-based configuration**
- **Graceful shutdown** and cleanup

#### Scalability

- **Session management** with cleanup
- **Connection pooling** for external services
- **Background task processing**
- **Resource usage monitoring**

## Usage Examples

### Basic Chat Interaction

```python
import requests

# Get access token
token_response = requests.post('http://localhost:5000/oauth/token', data={
    'grant_type': 'client_credentials',
    'client_id': 'mcp_client',
    'client_secret': 'mcp_secret'
})
token = token_response.json()['access_token']

# Send chat message
headers = {'Authorization': f'Bearer {token}'}
response = requests.post('http://localhost:5000/chat',
    json={'message': 'What files are in the current directory?'},
    headers=headers
)
print(response.json())
```

### MCP Tool Usage

```python
# List available tools
tools_response = requests.post('http://localhost:5000/mcp/list_tools',
    headers=headers
)
print(tools_response.json())

# Execute a command
tool_response = requests.post('http://localhost:5000/mcp/call_tool',
    json={
        'name': 'write_to_terminal',
        'arguments': {'command': 'ls -la'}
    },
    headers=headers
)
print(tool_response.json())
```

### Real-time Streaming

```javascript
// Connect to SSE stream
const eventSource = new EventSource(
  "/stream?session_id=your_session_id"
)

// Listen for command events
eventSource.addEventListener(
  "command_start",
  (event) => {
    const data = JSON.parse(event.data)
    console.log(
      "Command started:",
      data.command
    )
  }
)

eventSource.addEventListener(
  "command_complete",
  (event) => {
    const data = JSON.parse(event.data)
    console.log(
      "Command completed:",
      data.output
    )
  }
)
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**

   - Verify OAuth2 credentials
   - Check token expiration
   - Ensure proper Authorization header format

2. **Command Execution Failures**

   - Check command syntax
   - Verify file permissions
   - Review server logs for detailed error messages

3. **Connection Issues**

   - Verify server is running on correct host/port
   - Check firewall settings
   - Ensure proper SSL configuration

4. **Performance Issues**
   - Monitor system resources
   - Check concurrent session limits
   - Review command execution timeouts

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
export DEBUG=true
python server.py
```

### Health Checks

Monitor server health:

```bash
curl http://localhost:5000/health
```

### Log Analysis

View recent logs:

```bash
tail -f logs/term_mcp_deepseek.log
```

## Security Considerations

- All sensitive endpoints require OAuth2 authentication
- Input validation prevents command injection attacks
- Dangerous commands are blocked by default
- Session management prevents unauthorized access
- Comprehensive logging for audit trails
- Container security with non-root user
- Dependency vulnerability scanning in CI/CD

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/term_mcp_deepseek.git
cd term_mcp_deepseek

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run tests
pytest

# Start development server
python server.py
```

## License

This project is open-source and available under the [MIT License](LICENSE).
