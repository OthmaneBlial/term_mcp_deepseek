import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

import re
import json
import asyncio
import requests
from flask import Flask, request, jsonify, send_from_directory
import pexpect

from tools.command_executor import CommandExecutor
from tools.tty_output_reader import TtyOutputReader
from tools.send_control_character import SendControlCharacter
from tools.utils import sleep

app = Flask(__name__)

#######################################
# Global Shell + Conversation Storage
#######################################

# A single shell session for demonstration
shell = pexpect.spawn('/bin/bash', encoding='utf-8', echo=False)

# We'll keep a conversation list in memory
# (In real usage, you might store it per user, or in a DB.)
# For DeepSeek, we need a "messages" array, each with {role, content}.
# We'll start with a system message instructing the model how to run commands.
conversation = [
    {
        "role": "system",
        "content": (
            "You are a helpful AI assistant with terminal access. "
            "If you need to run a shell command to answer the user, include a line in your assistant message:\n"
            "CMD: the_command_here\n\n"
            "The server will intercept that line, run the command, and append the actual output to your final message. "
            "Only use 'CMD:' if you truly need to run a command."
        )
    }
]

#######################################
# Helper: run a command behind the scenes
#######################################
async def run_shell_command(cmd: str) -> str:
    """
    2-step approach behind the scenes:
     1) write_to_terminal => run the command
     2) read_terminal_output => retrieve newly produced lines
    Return the actual lines as a string
    """
    # We'll do it similarly to the 'call_tool' approach
    from tools.command_executor import CommandExecutor
    executor = CommandExecutor(shell)

    before_buffer = TtyOutputReader.get_buffer()
    before_lines = len(before_buffer.split("\n"))

    # run command
    await executor.execute_command(cmd)

    after_buffer = TtyOutputReader.get_buffer()
    after_lines = len(after_buffer.split("\n"))
    diff = after_lines - before_lines
    # read new lines
    lines_of_output = diff if diff > 0 else 25
    new_output = TtyOutputReader.call(lines_of_output)

    # Attempt to remove a trailing prompt line if present
    last_line = new_output.strip().split("\n")[-1]
    if re.search(r'(\$|%|#)\s*$', last_line):
        # If the last line looks like a prompt, remove it
        splitted = new_output.strip().split("\n")
        splitted.pop()
        new_output = "\n".join(splitted)
    return new_output.strip() or "(No output)"

#######################################
# DeepSeek Chat
#######################################
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"   # adjust if you have a different model name

def call_deepseek_api(messages):
    """
    Sends the conversation to DeepSeek. Returns the model's text.
    For reference:
      POST /chat/completions
      {
        "model": "deepseek-chat",
        "messages": [ {role, content}, ... ],
        "stream": false
      }
    With header "Authorization: Bearer <DEEPSEEK_API_KEY>"
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "stream": False
    }
    resp = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    # DeepSeek might store the model's text in data["choices"][0]["message"]["content"]
    return data["choices"][0]["message"]["content"]


#######################################
# Chat Endpoint
#######################################
@app.route("/chat", methods=["POST"])
def chat():
    """
    Accepts { "message": "...user text..." }
    1) Add user message to conversation
    2) Send conversation to DeepSeek
    3) Parse for lines like "CMD: something"
    4) For each command, run behind the scenes, inject the output into final text
    5) Return the final text to the user
    """
    global conversation

    data = request.json or {}
    user_text = data.get("message", "").strip()
    if not user_text:
        return jsonify({"message": "(No user input)"}), 400

    # 1) Add user message
    conversation.append({"role": "user", "content": user_text})

    # 2) Call DeepSeek
    try:
        assistant_text = call_deepseek_api(conversation)
    except Exception as e:
        err_msg = f"DeepSeek API error: {str(e)}"
        # We'll add an assistant message with the error
        conversation.append({"role": "assistant", "content": err_msg})
        return jsonify({"message": err_msg})

    # 3) Look for lines with "CMD: <stuff>"
    # We'll do a multiline approach, so we can handle multiple commands if needed.
    lines = assistant_text.split("\n")
    final_text_lines = []
    # We'll need an event loop for actual command runs
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for line in lines:
        if line.strip().startswith("CMD:"):
            cmd = line.strip()[len("CMD:"):].strip()
            if cmd:
                # 4) run behind scenes
                try:
                    output = loop.run_until_complete(run_shell_command(cmd))
                except Exception as exc:
                    output = f"(Error running '{cmd}': {exc})"

                # Insert the output after the command line
                final_text_lines.append(f"(Ran: {cmd})\n{output}")
            else:
                # no command after "CMD:"
                final_text_lines.append("(No command specified.)")
        else:
            # Normal text line
            final_text_lines.append(line)

    final_text = "\n".join(final_text_lines).strip()

    # 5) Add the final text to conversation
    conversation.append({"role": "assistant", "content": final_text})

    # Return it to the user
    return jsonify({"message": final_text})

#######################################
# Serve Chat Page
#######################################
@app.route("/")
def serve_chat():
    return send_from_directory("static", "chat.html")


#######################################
# MCP Endpoints remain if you need them
#######################################
@app.route('/mcp/list_tools', methods=['POST'])
def list_tools():
    return jsonify({
        "tools": [
            {
                "name": "write_to_terminal",
                "description": "Writes text to the active terminal session (like running a command).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The command to run or text to write"
                        }
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "read_terminal_output",
                "description": "Reads the output from the active terminal session",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "linesOfOutput": {
                            "type": "number",
                            "description": "How many lines from the bottom to read"
                        }
                    },
                    "required": ["linesOfOutput"]
                }
            },
            {
                "name": "send_control_character",
                "description": "Sends a control character to the active terminal (like Ctrl-C)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "letter": {
                            "type": "string",
                            "description": "Letter for the control char (e.g. 'C' for Ctrl-C)"
                        }
                    },
                    "required": ["letter"]
                }
            }
        ]
    })

@app.route('/mcp/call_tool', methods=['POST'])
def call_tool():
    """
    If you still want to do direct tool calls via cURL. 
    This remains from earlier examples, no changes.
    """
    from tools.command_executor import CommandExecutor

    data = request.json or {}
    tool_name = data.get("name", "")
    args = data.get("arguments", {})

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if tool_name == "write_to_terminal":
        command = str(args.get("command", ""))
        if not command:
            return jsonify({"error": "command is required"}), 400

        executor = CommandExecutor(shell)

        async def do_write():
            before_buffer = TtyOutputReader.get_buffer()
            before_lines = len(before_buffer.split("\n"))

            await executor.execute_command(command)

            after_buffer = TtyOutputReader.get_buffer()
            after_lines = len(after_buffer.split("\n"))
            diff = after_lines - before_lines

            msg = (f"{diff} lines were output after sending the command to the terminal. "
                   f"Read the last {diff} lines of terminal contents to orient yourself. "
                   f"Never assume that the command was executed or that it was successful.")
            return msg

        result_msg = loop.run_until_complete(do_write())
        return jsonify({
            "content": [{
                "type": "text",
                "text": result_msg
            }]
        })

    elif tool_name == "read_terminal_output":
        lines_of_output = int(args.get("linesOfOutput", 25))
        output = TtyOutputReader.call(lines_of_output)
        return jsonify({
            "content": [{
                "type": "text",
                "text": output
            }]
        })

    elif tool_name == "send_control_character":
        letter = str(args.get("letter", ""))
        if not letter:
            return jsonify({"error": "letter is required"}), 400

        sender = SendControlCharacter(shell)
        try:
            sender.send(letter)
        except Exception as e:
            return jsonify({"error": str(e)}), 400

        return jsonify({
            "content": [{
                "type": "text",
                "text": f"Sent control character: Control-{letter.upper()}"
            }]
        })

    else:
        return jsonify({"error": f"Unknown tool '{tool_name}'"}), 400


if __name__ == '__main__':
    print("Starting terminal+DeepSeek server:")
    print("  DEEPSEEK_API_KEY:", DEEPSEEK_API_KEY)
    app.run(host='127.0.0.1', port=5000, debug=True)
