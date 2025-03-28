# DeepSeek MCP-like Server for Terminal

This project is a prototype implementation of an MCP‑like server using the DeepSeek API. It aims to demonstrate the core concepts behind the Model Context Protocol (MCP) by exposing endpoints that allow AI assistants to:
 
- List available tools.
- Invoke commands on an active shell session.
- Integrate with an AI chat (DeepSeek) that can include special instructions (e.g., `CMD:` lines) to trigger command execution.

> **Note:** While this implementation captures many of the MCP ideas, it is not yet a fully compliant MCP server as defined by Anthropic. It is designed as a proof-of-concept, and further enhancements (e.g., JSON‑RPC protocol support, real‑time updates via SSE, session management, and improved security) would be needed for production use.

## Features

- **Chat Interface:**  
  A simple web-based chat client (using Flask and Tailwind CSS) where users can interact with the server.

- **AI Integration:**  
  Uses the DeepSeek API to generate responses. The AI can instruct the server to execute terminal commands by including lines beginning with `CMD:`.

- **Terminal Command Execution:**  
  Executes shell commands via a persistent Bash session using the `pexpect` library and returns output to the client.

- **MCP Endpoints:**  
  Provides `/mcp/list_tools` and `/mcp/call_tool` endpoints that mimic MCP tool discovery and invocation.

## Getting Started

### Prerequisites

- Python 3.8+
- [pip](https://pip.pypa.io/)
- A valid DeepSeek API key (set in `config.py`)

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

4. **Configure your API key:**

   Update the `DEEPSEEK_API_KEY` in `.env` with your DeepSeek API key.

### Running the Server

Run the Flask server with:

```bash
python server.py
```

Visit [http://127.0.0.1:5000](http://127.0.0.1:5000) to access the chat interface.

## Endpoints

### Chat Endpoint
- **URL:** `/chat`
- **Method:** `POST`
- **Payload:** `{ "message": "your message here" }`
- **Description:**  
  Adds the user message to the conversation, sends it to the DeepSeek API, looks for any command instructions (`CMD:`), executes them, and returns the final response.

### MCP Endpoints

#### List Tools
- **URL:** `/mcp/list_tools`
- **Method:** `POST`
- **Response:**  
  JSON listing available tools (e.g., `write_to_terminal`, `read_terminal_output`, `send_control_character`).

#### Call Tool
- **URL:** `/mcp/call_tool`
- **Method:** `POST`
- **Payload:**  
  ```json
  {
    "name": "tool_name",
    "arguments": { ... }
  }
  ```
- **Description:**  
  Directly invoke a tool command on the server.

## Future Improvements

- **Protocol Standardization:**  
  Implement JSON‑RPC for a more robust and standardized communication protocol.

- **Real-time Communication:**  
  Add Server‑Sent Events (SSE) or WebSockets for live command output streaming.

- **Session & Security Enhancements:**  
  Introduce per‑user sessions, proper authentication, input sanitization, and comprehensive error handling.

- **Modular Code Architecture:**  
  Further separate API logic from business logic for better maintainability and scalability.

## License

This project is open-source and available under the [MIT License](LICENSE).

