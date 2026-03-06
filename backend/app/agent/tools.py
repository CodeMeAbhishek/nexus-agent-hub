"""
Tool definitions and builders for the Nexus Agent.
"""
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.mcp.notion import call_notion_tool
from app.mcp.notion_write import create_task, update_task_status
from app.mcp.slack import async_call_slack_tool as call_slack_tool
from app.mcp.github import call_github_tool, get_github_user

# ============================================================================
# Notion Tools
# ============================================================================

class CallNotionInput(BaseModel):
    tool_name: str = Field(
        description="Notion MCP tool name. Common ones: notion-search-pages, notion-retrieve-block-children, notion-query-database"
    )
    arguments: dict = Field(
        default_factory=dict, 
        description="Arguments object. For search: {\"query\": \"text\"} or {\"query\": \"\"} for all. For blocks: {\"block_id\": \"id\"}."
    )

class CreateTaskInput(BaseModel):
    database_id: str = Field(description="The UUID of the database to add the task to.")
    title: str = Field(description="The title of the task.")
    status: str = Field(description="Status of the task (default: 'Not started').", default="Not started")
    priority: str = Field(description="Priority (High, Medium, Low).", default=None)
    due_date: str = Field(description="Due date in YYYY-MM-DD format.", default=None)

class UpdateStatusInput(BaseModel):
    page_id: str = Field(description="The UUID of the page/task to update.")
    status: str = Field(description="The new status (e.g., 'Done', 'In progress').")


def build_notion_tool(tool_list: list[dict], token: str | None = None) -> StructuredTool:
    """Build a single LangChain tool that calls Notion MCP by name + args."""
    if tool_list:
        names = ", ".join(t.get("name", "") for t in tool_list[:5])  # Show first 5 tools
        if len(tool_list) > 5:
            names += f", ... ({len(tool_list)} total)"
    else:
        names = "notion-search-pages, notion-retrieve-block-children, notion-query-database"
    
    desc = (
        f"Call a Notion API operation. Available tools: {names}. "
        "For search, use empty query to list all pages or provide keywords to search."
    )

    async def call_notion(tool_name: str, arguments: dict) -> str:
        args = dict(arguments) if arguments else {}
        # Pass the token captured in closure
        result = await call_notion_tool(tool_name, args, token=token)
        return result

    return StructuredTool.from_function(
        name="call_notion",
        description=desc,
        func=lambda tool_name, arguments: "",  # sync placeholder
        coroutine=call_notion,
        args_schema=CallNotionInput,
    )

def build_write_tools(token: str | None = None) -> list[StructuredTool]:
    """Build custom Notion write tools with auth token injection."""
    
    def create_task_wrapper(database_id: str, title: str, status: str = "Not started", priority: str = None, due_date: str = None):
        return create_task(database_id, title, status, priority, due_date, token=token)

    def update_status_wrapper(page_id: str, status: str):
        return update_task_status(page_id, status, token=token)

    return [
        StructuredTool.from_function(
            name="create_notion_task",
            description="Create a new task in a Notion database. Requires database_id (from search).",
            func=create_task_wrapper,
            args_schema=CreateTaskInput
        ),
        StructuredTool.from_function(
            name="update_notion_status",
            description="Update the status of a Notion task/page. Requires page_id.",
            func=update_status_wrapper,
            args_schema=UpdateStatusInput
        )
    ]

# ============================================================================
# Slack Tools
# ============================================================================

class CallSlackInput(BaseModel):
    tool_name: str = Field(
        description="Slack MCP tool name. Common: slack_list_channels, slack_post_message, slack_get_channel_history"
    )
    arguments: dict = Field(
        default_factory=dict,
        description="Arguments object. For post_message: {channel_id, text}. For history: {channel_id, limit}."
    )

def build_slack_tool(tool_list: list[dict], token: str | None = None, team_id: str | None = None) -> StructuredTool:
    """Build a single LangChain tool that calls Slack MCP by name + args."""
    if tool_list:
        names = ", ".join(t.get("name", "") for t in tool_list[:5])
        if len(tool_list) > 5:
            names += f", ... ({len(tool_list)} total)"
    else:
        names = "slack_list_channels, slack_post_message, slack_get_channel_history"
    
    desc = (
        f"Call a Slack API operation. Available tools: {names}. "
        "For posting messages, use channel_id and text. For channel history, use channel_id and limit."
    )

    async def call_slack(tool_name: str, arguments: dict) -> str:
        args = dict(arguments) if arguments else {}
        # Pass the token captured in closure
        result = await call_slack_tool(tool_name, args, token=token, team_id=team_id)
        return result

    return StructuredTool.from_function(
        name="call_slack",
        description=desc,
        func=lambda tool_name, arguments: "",  # sync placeholder
        coroutine=call_slack,
        args_schema=CallSlackInput,
    )

# ============================================================================
# GitHub Tools
# ============================================================================

class CallGitHubInput(BaseModel):
    tool_name: str = Field(
        description="GitHub MCP tool name. Common: search_repositories, list_issues, get_file_content, create_issue, get_github_user"
    )
    arguments: dict = Field(
        default_factory=dict,
        description="Arguments object. For list_issues: {owner, repo}. For search: {query}. For get_github_user: {}"
    )

def build_github_tool(tool_list: list[dict], user_id: str | None = None) -> StructuredTool:
    """Build a single LangChain tool that calls GitHub MCP."""
    names = "search_repositories, list_issues, create_issue, get_file_content"
    if tool_list:
         names = ", ".join(t.get("name", "") for t in tool_list[:5])

    desc = (
        f"Call a GitHub API operation. Available tools: {names}. "
        "Use this for managing code, issues, and repositories."
    )

    async def call_github(tool_name: str, arguments: dict) -> str:
        args = dict(arguments) if arguments else {}
        
        # Handle special custom tool for getting username
        if tool_name == "get_github_user":
            return await get_github_user(user_id=user_id)
            
        # Pass user_id to fetch token internally or pass token if we refactored
        # The call_github_tool takes user_id to fetch token
        result = await call_github_tool(tool_name, args, user_id=user_id)
        return result

    return StructuredTool.from_function(
        name="call_github",
        description=desc,
        func=lambda tool_name, arguments: "",
        coroutine=call_github,
        args_schema=CallGitHubInput,
    )
