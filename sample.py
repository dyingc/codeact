# ==========================================
# OpenRouter + LangGraph CodeAct RE Mock工具示例 (修正版)
# ==========================================

import os
import asyncio
import inspect
from dotenv import load_dotenv
from llm_sandbox import SandboxSession, SandboxBackend
from langchain_openai import ChatOpenAI
from langgraph_codeact import create_codeact, create_default_prompt
from langgraph.checkpoint.memory import MemorySaver
from langchain.tools import tool
from typing import List, Dict, Any

# 1. 设置环境变量
load_dotenv()

# 2. 配置OpenRouter模型
model = ChatOpenAI(
    model=os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite"),
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0
)


# 3. Docker沙箱评估函数
async def docker_eval_fn(code: str, _locals: dict) -> tuple[str, dict]:
    """Execute code in Docker container with tool functions available."""

    # Get available tools from _locals and inject their source
    tool_sources = []
    for name, obj in _locals.items():
        if hasattr(obj, '__name__') and obj.__name__ in TOOL_REGISTRY:
            tool_sources.append(TOOL_REGISTRY[obj.__name__])

    # Additional imports for RE environment
    imports = """
import json
import subprocess
import os
import re
from typing import List, Dict, Any
"""

    # Combine code
    full_code = f"{imports}\n\n" + "\n".join(tool_sources) + f"\n\n{code}"

    try:
        with SandboxSession(lang="python",
                          image="re:latest",
                          backend=SandboxBackend.DOCKER) as session:
            result = session.run(full_code)
            stdout = result.stdout or ""
            stderr = result.stderr or ""

            if stderr:
                stdout += f"\nSTDERR: {stderr}"

            return stdout, {}
    except Exception as e:
        return f"Docker execution error: {str(e)}", {}

# 自动注册装饰器
TOOL_REGISTRY = {}

def re_tool(name):
    """Decorator that registers tool source code and creates LangChain tool"""
    def decorator(func):
        # Store source code in registry (exclude decorator line)
        try:
            source = inspect.getsource(func)
            # Remove the decorator line
            lines = source.split('\n')
            # Find first line that doesn't start with @re_tool
            start_idx = 0
            for i, line in enumerate(lines):
                if not line.strip().startswith('@re_tool'):
                    start_idx = i
                    break
            TOOL_REGISTRY[name] = '\n'.join(lines[start_idx:])
        except OSError:
            # Fallback for dynamically created functions
            TOOL_REGISTRY[name] = f"# Source unavailable for {name}"

        # Return LangChain tool
        return tool(name)(func)
    return decorator

# Define tools with auto-registration
@re_tool("get_function_list")
def get_function_list(binary_path: str) -> List[Dict[str, Any]]:
    """
    List all functions in the binary.

    Args:
        binary_path (str): Path to the binary file.
    Returns:
        List[Dict[str, Any]]: List of functions with their names and addresses.
    Example:
        [
            {"name": "main", "address": "0x401000"},
            {"name": "helper", "address": "0x401100"}
        ]
    """
    return [
        {"name": "main", "address": "0x401000"},
        {"name": "helper", "address": "0x401100"},
    ]

@re_tool("get_disassembly")
def get_disassembly(binary_path: str, function_name: str) -> str:
    """Get disassembly of a function."""
    return f"Disassembly for {function_name} at {binary_path}:\n0x401000: push rbp\n0x401001: mov rbp, rsp\n..."

@re_tool("get_pseudo_code")
def get_pseudo_code(binary_path: str, function_name: str) -> Dict[str, str]:
    """Get decompiled (pseudo code) of a function."""
    return {"pseudo_code": f"int {function_name}() {{ ... }}"}

@re_tool("get_call_graph")
def get_call_graph(binary_path: str) -> Dict[str, List[str]]:
    """Get the function call graph of the binary."""
    return {
        "main": ["helper", "exit"],
        "helper": ["memcpy"]
    }

@re_tool("get_cfg_basic_blocks")
def get_cfg_basic_blocks(binary_path: str, function_name: str) -> List[Dict[str, Any]]:
    """Get control flow graph (CFG) basic blocks for a function."""
    return [
        {"start": "0x401000", "end": "0x401010"},
        {"start": "0x401010", "end": "0x401020"},
    ]

@re_tool("get_strings")
def get_strings(binary_path: str) -> List[Dict[str, str]]:
    """Extract all printable strings in the binary."""
    return [
        {"string": "Hello, world!", "address": "0x402000"},
        {"string": "Input: ", "address": "0x402010"},
    ]

@re_tool("search_string_refs")
def search_string_refs(binary_path: str, string: str) -> List[Dict[str, Any]]:
    """Find references to a string in the binary."""
    return [
        {"address": "0x401050", "ref_type": "mov", "context": f"Loads '{string}'"}
    ]

@re_tool("emulate_basic_block")
def emulate_basic_block(binary_path: str, address: str) -> str:
    """Emulate execution of a basic block at a given address."""
    return f"Emulated basic block at {address} in {binary_path}: EAX=0x1, EBX=0x2"

tools = [
    get_function_list,
    get_disassembly,
    get_pseudo_code,
    get_call_graph,
    get_cfg_basic_blocks,
    get_strings,
    search_string_refs,
    emulate_basic_block
]

# 创建 CodeAct 代理
base_prompt = (
    "You are a highly experienced cybersecurity expert with exceptional skills in binary analysis and reverse engineering. "
    "You excel at static analysis and symbolic execution using tools such as angr, and are highly proficient with dynamic analysis tools like Ghidra and Radare2/Rizin. "
    "You have access to an environment where these tools are installed, and can execute code within a secure, sandboxed environment."
)

prompt = create_default_prompt(tools, base_prompt)
code_act = create_codeact(model, tools=tools, eval_fn=docker_eval_fn, prompt=prompt)
agent = code_act.compile(checkpointer=MemorySaver())

# 5. 简单测试
async def main():
    config = {"configurable": {"thread_id": "test"}}

    result = await agent.ainvoke(
        {"messages": [("user", "Get the list of functions, not system ones, from ./sample_binary and calculate the number of such functions. You should tell me the name of the function and its address.")], "config": config},
        config=config
    )

    print(result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())