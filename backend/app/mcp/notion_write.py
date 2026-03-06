import os
from notion_client import Client
import logging

logger = logging.getLogger("notion_write")

def get_notion_client(token: str = None):
    # Use provided token, or fall back to env var
    auth_token = token or os.environ.get("NOTION_TOKEN")
    if not auth_token:
        raise ValueError("NOTION_TOKEN not set in environment or passed explicitly")
    return Client(auth=auth_token)

def create_task(database_id: str, title: str, status: str = "Not started", priority: str = None, due_date: str = None, token: str = None):
    """
    Creates a new task in the specified Notion database.
    
    Args:
        database_id: The ID of the database to add the task to.
        title: The name of the task.
        status: The status (default: "Not started").
        priority: Optional priority (High, Medium, Low).
        due_date: Optional due date (ISO format YYYY-MM-DD).
        token: Optional Notion API token (injected by agent).
    """
    try:
        notion = get_notion_client(token)
        
        properties = {
            "Name": {"title": [{"text": {"content": title}}]},
            "Status": {"status": {"name": status}}
        }
        
        if priority:
            properties["Priority"] = {"select": {"name": priority}}
            
        if due_date:
            properties["Due Date"] = {"date": {"start": due_date}}
            
        response = notion.pages.create(
            parent={"database_id": database_id},
            properties=properties
        )
        return f"Successfully created task '{title}' (ID: {response['id']}) in database."
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        return f"Error creating task: {e}"

def update_task_status(page_id: str, status: str, token: str = None):
    """
    Updates the status of a Notion page (task).
    
    Args:
        page_id: The ID of the page to update.
        status: The new status (e.g., "Done", "In progress").
        token: Optional Notion API token (injected by agent).
    """
    try:
        notion = get_notion_client(token)
        
        response = notion.pages.update(
            page_id=page_id,
            properties={
                "Status": {"status": {"name": status}}
            }
        )
        return f"Successfully updated task status to '{status}' (ID: {page_id})."
    except Exception as e:
        logger.error(f"Failed to update task: {e}")
        return f"Error updating task: {e}"
