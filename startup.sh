#!/usr/bin/env bash
set -euo pipefail

# project root
cd "$(dirname "$0")"

# create venv if missing
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# activate venv
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# export env
export FLASK_ENV=${FLASK_ENV:-production}
export PYTHONUNBUFFERED=1

# function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # port is in use
    else
        return 1  # port is free
    fi
}

# function to find available port
find_available_port() {
    local port=8000
    while check_port $port; do
        echo "Port $port is in use, trying next port..."
        port=$((port + 1))
        if [ $port -gt 8999 ]; then
            echo "ERROR: No available ports found in range 8000-8999"
            exit 1
        fi
    done
    echo $port
}

# function to kill process on port
kill_port_process() {
    local port=$1
    local pid=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo "Killing process $pid on port $port..."
        kill -9 $pid 2>/dev/null || true
        sleep 2  # wait for process to die
    fi
}

# main port handling logic
DEFAULT_PORT=8000

if check_port $DEFAULT_PORT; then
    echo "Port $DEFAULT_PORT is in use."
    echo "Options:"
    echo "1. Kill existing process and use port $DEFAULT_PORT"
    echo "2. Find next available port"
    echo "3. Exit"

    # Auto-select option 2 for non-interactive mode
    if [ -t 0 ]; then
        # Interactive mode
        read -p "Choose option (1/2/3): " choice
        case $choice in
            1)
                kill_port_process $DEFAULT_PORT
                PORT=$DEFAULT_PORT
                ;;
            2)
                PORT=$(find_available_port)
                ;;
            3)
                echo "Exiting..."
                exit 0
                ;;
            *)
                echo "Invalid choice. Finding available port..."
                PORT=$(find_available_port)
                ;;
        esac
    else
        # Non-interactive mode - auto find available port
        echo "Non-interactive mode: finding available port..."
        PORT=$(find_available_port)
    fi
else
    PORT=$DEFAULT_PORT
fi

echo "Starting server on port $PORT..."

# export port
export PORT=$PORT

# run
exec python server_new.py

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to find an available port
find_available_port() {
    local port=$1
    local max_attempts=100
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if ! check_port $port; then
            echo $port
            return 0
        fi
        print_warning "Port $port is in use, trying next port..."
        port=$((port + 1))
        attempt=$((attempt + 1))
    done

    print_error "Could not find an available port after $max_attempts attempts"
    exit 1
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi

    local python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    local major_version=$(echo $python_version | cut -d. -f1)
    local minor_version=$(echo $python_version | cut -d. -f2)

    if [ "$major_version" -lt 3 ] || ([ "$major_version" -eq 3 ] && [ "$minor_version" -lt 8 ]); then
        print_error "Python 3.8 or higher is required. Current version: $python_version"
        exit 1
    fi

    print_success "Python version check passed: $python_version"
}

# Function to setup virtual environment
setup_venv() {
    if [ ! -d "venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_info "Virtual environment already exists"
    fi

    print_info "Activating virtual environment..."
    source venv/bin/activate

    print_info "Installing/updating dependencies..."
    pip install --quiet -r requirements.txt
    print_success "Dependencies installed"
}

# Function to check environment configuration
check_environment() {
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            print_warning ".env file not found. Copying from .env.example..."
            cp .env.example .env
            print_warning "Please edit .env file and set your DEEPSEEK_API_KEY"
        else
            print_error ".env file not found and .env.example not available"
            exit 1
        fi
    fi

    # Check if DEEPSEEK_API_KEY is set
    if ! grep -q "^DEEPSEEK_API_KEY=" .env || grep -q "^DEEPSEEK_API_KEY=$" .env; then
        print_error "DEEPSEEK_API_KEY is not set in .env file"
        print_info "Please edit .env file and set: DEEPSEEK_API_KEY=your_api_key_here"
        exit 1
    fi

    print_success "Environment configuration check passed"
}

# Function to start HTTP server
start_http_server() {
    local host=$1
    local port=$2

    print_info "Starting HTTP server on $host:$port..."

    # Set environment variables for this session
    export HOST=$host
    export PORT=$port

    # Start the server using virtual environment python
    if [ "$VERBOSE" = true ]; then
        ./venv/bin/python server.py
    else
        ./venv/bin/python server.py > /dev/null 2>&1 &
        local server_pid=$!
        echo $server_pid > .server_pid

        print_success "Server started with PID: $server_pid"
        print_info "Server is running at: http://$host:$port"
        print_info "Web interface: http://$host:$port"
        print_info "API documentation: http://$host:$port (see README.md)"
        print_info "To stop the server, run: kill $server_pid or ./startup.sh stop"
    fi
}

# Function to start STDIO server
start_stdio_server() {
    print_info "Starting STDIO server..."

    if [ "$VERBOSE" = true ]; then
        ./venv/bin/python stdio_server.py
    else
        print_info "STDIO server is designed for command-line integration"
        print_info "Use: echo '{\"jsonrpc\": \"2.0\", \"method\": \"tools/list\", \"id\": 1}' | ./venv/bin/python stdio_server.py"
        ./venv/bin/python stdio_server.py
    fi
}

# Function to start Docker containers
start_docker() {
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    print_info "Starting with Docker Compose..."

    if [ "$VERBOSE" = true ]; then
        docker-compose up
    else
        docker-compose up -d
        print_success "Docker containers started"
        print_info "Web interface: http://localhost:5000"
        print_info "To view logs: docker-compose logs -f"
        print_info "To stop: docker-compose down"
    fi
}

# Function to stop the server
stop_server() {
    if [ -f ".server_pid" ]; then
        local server_pid=$(cat .server_pid)
        if kill -0 $server_pid 2>/dev/null; then
            print_info "Stopping server (PID: $server_pid)..."
            kill $server_pid
            sleep 2
            if kill -0 $server_pid 2>/dev/null; then
                print_warning "Server didn't stop gracefully, force killing..."
                kill -9 $server_pid
            fi
            print_success "Server stopped"
        else
            print_warning "Server process $server_pid not found"
        fi
        rm -f .server_pid
    else
        print_warning "No server PID file found"
    fi

    # Also try to stop Docker containers
    if command_exists docker-compose; then
        if docker-compose ps | grep -q "Up"; then
            print_info "Stopping Docker containers..."
            docker-compose down
            print_success "Docker containers stopped"
        fi
    fi
}

# Function to check server health
check_health() {
    local host=$1
    local port=$2
    local max_attempts=30
    local attempt=1

    print_info "Checking server health..."

    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "http://$host:$port/health" >/dev/null 2>&1; then
            print_success "Server is healthy and responding"
            return 0
        fi

        if [ $attempt -eq 1 ]; then
            print_info "Waiting for server to start..."
        fi

        sleep 1
        attempt=$((attempt + 1))
    done

    print_error "Server health check failed after $max_attempts seconds"
    return 1
}

# Function to show usage
show_usage() {
    cat << EOF
Term MCP DeepSeek Startup Script

USAGE:
    ./startup.sh [OPTIONS] [COMMAND]

COMMANDS:
    start       Start the server (default)
    stop        Stop the running server
    restart     Restart the server
    status      Show server status
    logs        Show server logs

OPTIONS:
    -m, --mode MODE      Startup mode: http, stdio, docker (default: http)
    -h, --host HOST      Server host (default: 127.0.0.1)
    -p, --port PORT      Server port (default: 5000)
    --no-auto-port       Don't automatically find available port
    -v, --verbose        Verbose output
    --help               Show this help message

EXAMPLES:
    ./startup.sh                         # Start HTTP server with auto port
    ./startup.sh -m docker               # Start with Docker
    ./startup.sh -m stdio                # Start STDIO server
    ./startup.sh -p 8080                 # Start on port 8080
    ./startup.sh stop                    # Stop the server
    ./startup.sh restart                 # Restart the server
    ./startup.sh status                  # Show status

ENVIRONMENT:
    Make sure to set DEEPSEEK_API_KEY in .env file
    Copy .env.example to .env and edit as needed

For more information, see README.md
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            STARTUP_MODE="$2"
            shift 2
            ;;
        -h|--host)
            DEFAULT_HOST="$2"
            shift 2
            ;;
        -p|--port)
            DEFAULT_PORT="$2"
            shift 2
            ;;
        --no-auto-port)
            AUTO_PORT=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        start|stop|restart|status|logs)
            COMMAND="$1"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Set default command
COMMAND=${COMMAND:-start}

# Main logic
case $COMMAND in
    start)
        print_info "=== Term MCP DeepSeek Startup ==="
        print_info "Mode: $STARTUP_MODE"

        # Pre-flight checks
        check_python_version

        case $STARTUP_MODE in
            http)
                # Setup environment
                setup_venv
                check_environment

                # Handle port conflicts
                if [ "$AUTO_PORT" = true ]; then
                    FINAL_PORT=$(find_available_port $DEFAULT_PORT)
                else
                    if check_port $DEFAULT_PORT; then
                        print_error "Port $DEFAULT_PORT is already in use"
                        print_info "Use --no-auto-port to disable auto port selection"
                        exit 1
                    fi
                    FINAL_PORT=$DEFAULT_PORT
                fi

                # Start HTTP server
                start_http_server $DEFAULT_HOST $FINAL_PORT

                # Health check
                if [ "$VERBOSE" = false ]; then
                    check_health $DEFAULT_HOST $FINAL_PORT
                fi
                ;;

            stdio)
                setup_venv
                check_environment
                start_stdio_server
                ;;

            docker)
                check_environment
                start_docker
                ;;

            *)
                print_error "Invalid startup mode: $STARTUP_MODE"
                print_info "Valid modes: http, stdio, docker"
                exit 1
                ;;
        esac
        ;;

    stop)
        print_info "=== Stopping Term MCP DeepSeek ==="
        stop_server
        ;;

    restart)
        print_info "=== Restarting Term MCP DeepSeek ==="
        stop_server
        sleep 2
        exec "$0" start "$@"
        ;;

    status)
        print_info "=== Server Status ==="
        if [ -f ".server_pid" ]; then
            local server_pid=$(cat .server_pid)
            if kill -0 $server_pid 2>/dev/null; then
                print_success "Server is running (PID: $server_pid)"
                # Try to get port information
                local port_info=$(lsof -i -P -n | grep LISTEN | grep $server_pid | head -1 | awk '{print $9}')
                if [ -n "$port_info" ]; then
                    print_info "Listening on: $port_info"
                fi
            else
                print_warning "Server PID file exists but process is not running"
                rm -f .server_pid
            fi
        else
            print_info "No server PID file found"
        fi

        # Check Docker status
        if command_exists docker-compose; then
            if docker-compose ps | grep -q "Up"; then
                print_success "Docker containers are running"
                docker-compose ps
            else
                print_info "No Docker containers running"
            fi
        fi
        ;;

    logs)
        print_info "=== Server Logs ==="
        if [ -f "logs/term_mcp_deepseek.log" ]; then
            tail -f logs/term_mcp_deepseek.log
        else
            print_warning "Log file not found: logs/term_mcp_deepseek.log"
            print_info "Server may not have been started yet, or logs are disabled"
        fi
        ;;

    *)
        print_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac

print_success "Done!"