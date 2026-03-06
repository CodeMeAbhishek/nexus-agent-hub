"""
MongoDB MCP limb - Direct database querying via pymongo.
Supports listing databases/collections, querying documents, and aggregation.
"""
import logging
import json
from typing import List, Optional, Dict, Any

from langchain_core.tools import tool

from app.db.supabase import get_connection_credentials

logger = logging.getLogger(__name__)


def _get_mongo_client(connection_string: str):
    """Create a pymongo client from connection string."""
    try:
        from pymongo import MongoClient
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        # Test connection
        client.admin.command('ping')
        return client
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return None


def get_mongodb_tools(user_id: str) -> List[Any]:
    """Return list of MongoDB tools, bound to the specific user_id."""

    async def _get_client():
        """Get MongoDB client from stored credentials."""
        creds = await get_connection_credentials(user_id, "mongodb")
        if not creds:
            return None
        connection_string = creds.get("token", "")
        if not connection_string:
            return None
        return _get_mongo_client(connection_string)

    @tool
    async def list_mongo_databases() -> str:
        """
        List all databases and their collections in the connected MongoDB instance.
        Use this first to discover what data is available.
        """
        client = await _get_client()
        if not client:
            return "MongoDB is not connected. Please connect it in Settings with your connection string."

        try:
            output = []
            db_names = client.list_database_names()
            # Filter out system databases
            db_names = [d for d in db_names if d not in ('admin', 'local', 'config')]

            if not db_names:
                return "No user databases found in MongoDB instance."

            for db_name in db_names:
                db = client[db_name]
                collections = db.list_collection_names()
                coll_list = ", ".join(collections) if collections else "(empty)"
                # Get rough doc counts
                coll_info = []
                for coll_name in collections[:10]:  # Limit to first 10
                    count = db[coll_name].estimated_document_count()
                    coll_info.append(f"`{coll_name}` ({count} docs)")
                info = ", ".join(coll_info) if coll_info else "(empty)"
                output.append(f"🗄️ **{db_name}**: {info}")

            client.close()
            return f"Found {len(db_names)} database(s):\n\n" + "\n".join(output)
        except Exception as e:
            logger.error(f"Error listing databases: {e}")
            return f"Error listing databases: {str(e)}"

    @tool
    async def query_mongo_collection(database: str, collection: str, filter_json: str = "{}", limit: int = 10) -> str:
        """
        Query documents from a MongoDB collection.
        Args:
            database: Database name (e.g., 'myapp')
            collection: Collection name (e.g., 'users', 'orders')
            filter_json: MongoDB filter as JSON string (e.g., '{"status": "active"}', '{"age": {"$gt": 25}}')
            limit: Maximum number of documents to return (default 10)
        """
        client = await _get_client()
        if not client:
            return "MongoDB is not connected. Please connect it in Settings with your connection string."

        try:
            # Parse filter
            try:
                filter_dict = json.loads(filter_json)
            except json.JSONDecodeError:
                return f"Invalid filter JSON: {filter_json}. Use valid MongoDB query syntax."

            db = client[database]
            coll = db[collection]

            # Execute query
            cursor = coll.find(filter_dict).limit(limit)
            docs = list(cursor)

            if not docs:
                return f"No documents found in `{database}.{collection}` matching filter `{filter_json}`."

            # Format output
            output = []
            for i, doc in enumerate(docs, 1):
                # Convert ObjectId to string for JSON serialization
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                # Convert dates to strings
                for key, val in doc.items():
                    if hasattr(val, 'isoformat'):
                        doc[key] = val.isoformat()
                # Truncate very long values
                formatted = json.dumps(doc, indent=2, default=str)
                if len(formatted) > 500:
                    formatted = formatted[:500] + "..."
                output.append(f"**Document {i}:**\n```json\n{formatted}\n```")

            total = coll.count_documents(filter_dict)
            client.close()

            header = f"Found **{total}** document(s) in `{database}.{collection}` (showing {len(docs)}):\n\n"
            return header + "\n---\n".join(output)

        except Exception as e:
            logger.error(f"Error querying MongoDB: {e}")
            return f"Error querying collection: {str(e)}"

    @tool
    async def aggregate_mongo_collection(database: str, collection: str, pipeline_json: str) -> str:
        """
        Run a MongoDB aggregation pipeline on a collection. Great for counts, averages, group-by, etc.
        Args:
            database: Database name
            collection: Collection name
            pipeline_json: MongoDB aggregation pipeline as JSON string.
                Examples:
                - Count: '[{"$count": "total"}]'
                - Group by status: '[{"$group": {"_id": "$status", "count": {"$sum": 1}}}]'
                - Average price: '[{"$group": {"_id": null, "avg_price": {"$avg": "$price"}}}]'
                - Filter + count: '[{"$match": {"status": "active"}}, {"$count": "active_count"}]'
        """
        client = await _get_client()
        if not client:
            return "MongoDB is not connected. Please connect it in Settings with your connection string."

        try:
            try:
                pipeline = json.loads(pipeline_json)
            except json.JSONDecodeError:
                return f"Invalid pipeline JSON: {pipeline_json}. Use valid MongoDB aggregation pipeline syntax."

            if not isinstance(pipeline, list):
                return "Pipeline must be a JSON array of stages, e.g., [{\"$count\": \"total\"}]"

            db = client[database]
            coll = db[collection]

            results = list(coll.aggregate(pipeline))

            if not results:
                return f"Aggregation returned no results for `{database}.{collection}`."

            # Format results
            output = []
            for i, result in enumerate(results, 1):
                if '_id' in result:
                    result['_id'] = str(result['_id'])
                formatted = json.dumps(result, indent=2, default=str)
                output.append(f"```json\n{formatted}\n```")

            client.close()
            return f"Aggregation result ({len(results)} row(s)) from `{database}.{collection}`:\n\n" + "\n".join(output)

        except Exception as e:
            logger.error(f"Error in MongoDB aggregation: {e}")
            return f"Error in aggregation: {str(e)}"

    return [list_mongo_databases, query_mongo_collection, aggregate_mongo_collection]
