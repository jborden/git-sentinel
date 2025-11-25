import logging
from typing import TypedDict
from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langfuse.langchain import CallbackHandler

from sentinel_tools import quarantine_file, write_remediation_report

load_dotenv()

# --- Logging Setup ---
logging.basicConfig(
    filename='sentinel_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    filemode='a'
)
logger = logging.getLogger(__name__)

# --- State ---
class AgentState(TypedDict):
    file_path: str         # The dangerous file
    threat_type: str       # "AWS Key", "PII", etc.
    analysis: str          # LLM reasoning
    tool_calls: list       # Tools selected by LLM

# --- LLM Setup ---
llm = ChatOllama(model="qwen3-coder:30b", temperature=0)
tools = [quarantine_file, write_remediation_report]
tools_map = {t.name: t for t in tools}
llm_with_tools = llm.bind_tools(tools)

# --- Nodes ---

def analyze_threat(state: AgentState):
    """Analyze the threat and decide on mitigation steps."""
    path = state["file_path"]
    threat = state["threat_type"]
    logger.info(f"Analyzing threat: {threat} in {path}")

    # Prompt triggers the LLM to call BOTH tools: Quarantine first, then Report.
    msg = [
        ("system", "You are a Cyber Security Sentinel. You have detected a security violation in a git repository. "
                   "You must IMMEDIATELY quarantine the file. "
                   "Then, you must write a remediation report explaining the specific risks of this threat type. "
                   "For AWS keys, explain the risk of cloud bill shock. "
                   "For PII, explain GDPR risks."),
        ("human", f"ALERT: Detected {threat} in file {path}. Execute protocol.")
    ]

    response = llm_with_tools.invoke(msg)
    return {"tool_calls": response.tool_calls}

def execute_mitigation(state: AgentState):
    """Execute the tools chosen by the LLM."""
    results = []
    for tool_call in state["tool_calls"]:
        tool_name = tool_call["name"]
        args = tool_call["args"]

        logger.info(f"Executing tool: {tool_name}")
        tool_func = tools_map.get(tool_name)

        # Invoke tool
        res = tool_func.invoke(args)
        results.append(str(res))

    return {"analysis": f"Executed {len(results)} mitigation steps."}

# --- Graph ---

def build_sentinel_agent():
    workflow = StateGraph(AgentState)

    workflow.add_node("analyze", analyze_threat)
    workflow.add_node("execute", execute_mitigation)

    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "execute")
    workflow.add_edge("execute", END)

    return workflow.compile()

# --- Runner ---

def process_threat_event(file_path: str, threat_type: str):
    """Entry point for the CLI."""
    langfuse_handler = CallbackHandler()
    app = build_sentinel_agent()

    initial_state = {
        "file_path": file_path,
        "threat_type": threat_type
    }

    try:
        # We process it
        result = app.invoke(initial_state, config={"callbacks": [langfuse_handler]})
        return result
    except Exception as e:
        logger.error(f"Agent failed: {e}")
        return {"analysis": f"Agent Crash: {str(e)}"}
