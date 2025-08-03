# ==========================================
# OpenRouter + LangGraph CodeAct RE Mock工具示例 (修正版)
# ==========================================

import os
import asyncio
from dotenv import load_dotenv
from llm_sandbox import SandboxSession, SandboxBackend
from langchain_openai import ChatOpenAI
from langgraph_codeact import create_codeact, create_default_prompt
from langgraph.checkpoint.memory import MemorySaver
from langchain.tools import tool

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
    # 1. Prepare a Python snippet that defines each variable.
    init = "\n".join(f"{func_name} = {repr(func_def)}"
                     for func_name, func_def in _locals.items())

    full_code = f"{init}\n{code}"

    with SandboxSession(lang="python",
                        image="re:latest",
                        backend=SandboxBackend.DOCKER) as session:
        result = session.run(full_code)
        stdout = result.stdout or ""
        return stdout, {}  # session can't capture local state directly

# 4. 创建 mock RE 工具（直接用函数或@tool修饰）
@tool("get_function_list")
def get_function_list(binary_path: str) -> list:
    """List all functions in the binary."""
    return [
        {"name": "main", "address": "0x401000"},
        {"name": "helper", "address": "0x401100"},
    ]

@tool("get_disassembly")
def get_disassembly(binary_path: str, function_name: str) -> str:
    """Get disassembly of a function."""
    return f"Disassembly for {function_name} at {binary_path}:\n0x401000: push rbp\n0x401001: mov rbp, rsp\n..."

@tool("get_pseudo_code")
def get_pseudo_code(binary_path: str, function_name: str) -> str:
    """Get decompiled (pseudo code) of a function."""
    return f"Pseudo code for {function_name}:\nint {function_name}() {{ ... }}"

@tool("get_call_graph")
def get_call_graph(binary_path: str) -> dict:
    """Get the function call graph of the binary."""
    return {
        "main": ["helper", "exit"],
        "helper": ["memcpy"]
    }

@tool("get_cfg_basic_blocks")
def get_cfg_basic_blocks(binary_path: str, function_name: str) -> list:
    """Get control flow graph (CFG) basic blocks for a function."""
    return [
        {"start": "0x401000", "end": "0x401010"},
        {"start": "0x401010", "end": "0x401020"},
    ]

@tool("get_strings")
def get_strings(binary_path: str) -> list:
    """Extract all printable strings in the binary."""
    return [
        {"string": "Hello, world!", "address": "0x402000"},
        {"string": "Input: ", "address": "0x402010"},
    ]

@tool("search_string_refs")
def search_string_refs(binary_path: str, string: str) -> list:
    """Find references to a string in the binary."""
    return [
        {"address": "0x401050", "ref_type": "mov", "context": f"Loads '{string}'"}
    ]

@tool("emulate_basic_block")
def emulate_basic_block(binary_path: str, address: str) -> str:
    """Emulate execution of a basic block at a given address."""
    return f"Emulated basic block at {address} in {binary_path}: EAX=0x1, EBX=0x2"

# 工具函数直接作为列表
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
        {"messages": [("user", "计算1到100的平方和")]},
        config=config
    )

    print(result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())