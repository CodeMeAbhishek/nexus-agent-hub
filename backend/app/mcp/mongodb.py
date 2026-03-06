"""
MongoDB MCP limb - Direct database querying via pymongo.
Supports listing databases/collections, querying documents, and aggregation.
"""
import logging
import json
import os
import re
from urllib.parse import quote_plus
from typing import List, Optional, Dict, Any

from langchain_core.tools import tool

from app.db.supabase import get_connection_credentials

logger = logging.getLogger(__name__)

# Help Windows + Atlas TLS: point system SSL to certifi before any connection
try:
    import certifi as _certifi
    os.environ.setdefault("SSL_CERT_FILE", _certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _certifi.where())
except ImportError:
    pass


def _escape_mongo_uri(uri: str) -> str:
    """Escape username and password in a MongoDB URI per RFC 3986 (fixes InvalidURI when password has @, :, #, etc.)."""
    uri = uri.strip()
    # Match scheme:// then split on *last* @ so password can contain @ (e.g. user:p@ss@host)
    m = re.match(r"^((?:mongodb(?:\+srv)?)://)(.*)@([^@]+)$", uri, re.IGNORECASE | re.DOTALL)
    if not m:
        return uri
    scheme, userinfo, host_and_rest = m.group(1), m.group(2), m.group(3)
    # userinfo is "user:password" — split on first ':' only (password may contain ':')
    idx = userinfo.find(":")
    if idx == -1:
        userinfo_escaped = quote_plus(userinfo)
    else:
        user_escaped = quote_plus(userinfo[:idx])
        pass_escaped = quote_plus(userinfo[idx + 1 :])
        userinfo_escaped = f"{user_escaped}:{pass_escaped}"
    return f"{scheme}{userinfo_escaped}@{host_and_rest}"


def _strip_tls_options_from_uri(uri: str) -> str:
    """Remove tlsAllowInvalidCertificates and tlsDisableOCSPEndpointCheck from URI so we control them via kwargs only (pymongo forbids both together)."""
    if "?" not in uri:
        return uri
    base, qs = uri.split("?", 1)
    for opt in ("tlsallowinvalidcertificates", "tlsdisableocspendpointcheck"):
        qs = re.sub(r"&?" + re.escape(opt) + r"=[^&]*", "", qs, flags=re.IGNORECASE)
    qs = qs.strip("&")
    return f"{base}?{qs}" if qs else base


def _get_mongo_client(connection_string: str) -> tuple[Optional[Any], Optional[str]]:
    """Create a pymongo client from connection string. Returns (client, None) or (None, error_message)."""
    from pymongo import MongoClient

    raw_uri = connection_string.strip()
    raw_uri = _escape_mongo_uri(raw_uri)
    raw_uri = _strip_tls_options_from_uri(raw_uri)
    try:
        import certifi
        _certifi_path = certifi.where()
    except ImportError:
        _certifi_path = None

    def _connect(
        use_uri: str,
        tls_allow_invalid: Optional[bool] = None,
        tls_disable_ocsp: Optional[bool] = None,
    ) -> tuple[Optional[Any], Optional[str]]:
        # pymongo forbids tlsAllowInvalidCertificates and tlsDisableOCSPEndpointCheck together — pass only one
        try:
            kwargs: Dict[str, Any] = {"serverSelectionTimeoutMS": 15000, "tlsAllowInvalidHostnames": True}
            if tls_allow_invalid is not None:
                kwargs["tlsAllowInvalidCertificates"] = tls_allow_invalid
            if tls_disable_ocsp is not None:
                kwargs["tlsDisableOCSPEndpointCheck"] = tls_disable_ocsp
            if _certifi_path:
                kwargs["tlsCAFile"] = _certifi_path
            client = MongoClient(use_uri, **kwargs)
            client.admin.command("ping")
            return (client, None)
        except Exception as e:
            return (None, e)

    # Attempt 1: relaxed cert only (pymongo forbids both options together)
    logger.info("MongoDB: attempt 1 — tlsAllowInvalidCertificates + certifi")
    client, err = _connect(raw_uri, tls_allow_invalid=True, tls_disable_ocsp=None)
    if client:
        logger.info("MongoDB: connected (relaxed TLS)")
        return (client, None)

    err_str = str(err).lower()
    logger.warning("MongoDB: attempt 1 failed: %s", err)

    # Attempt 2: OCSP disabled only
    if "ssl" in err_str or "tls" in err_str or "handshake" in err_str or "invalid" in err_str or "uri" in err_str:
        logger.info("MongoDB: attempt 2 — tlsDisableOCSPEndpointCheck + certifi")
        client, err2 = _connect(raw_uri, tls_allow_invalid=None, tls_disable_ocsp=True)
        if client:
            logger.info("MongoDB: connected (OCSP disabled)")
            return (client, None)
        logger.warning("MongoDB: attempt 2 failed: %s", err2)
        err = err2

    # Attempt 3: certifi only (strict verification)
    if "ssl" in err_str or "tls" in err_str or "handshake" in err_str or "invalid" in err_str or "uri" in err_str:
        logger.info("MongoDB: attempt 3 — certifi CA only (strict)")
        client, err3 = _connect(raw_uri, tls_allow_invalid=None, tls_disable_ocsp=None)
        if client:
            logger.info("MongoDB: connected (strict verification)")
            return (client, None)
        logger.warning("MongoDB: attempt 3 failed: %s", err3)
        err = err3

    logger.error(
        "MongoDB connection failed after 3 attempts. Error type=%s message=%s",
        type(err).__name__,
        err,
    )
    err_str_lower = str(err).lower()
    if "bad auth" in err_str_lower or "authentication failed" in err_str_lower:
        msg = (
            "MongoDB authentication failed: the username or password is wrong, or the user has no access. "
            "In Atlas: (1) Database Access → check the user exists and the password is correct; "
            "(2) Re-copy the connection string from Connect → Drivers, replace <password> with your actual password "
            "(no angle brackets). If the password contains special characters (@, #, :, etc.), re-enter it in Settings "
            "so the app can escape it correctly."
        )
    else:
        msg = (
            f"MongoDB connection failed: {err}. "
            "Try: (1) Upgrade certifi: `pip install --upgrade certifi`. "
            "(2) Ensure `pymongo[ocsp]` is installed. (3) Use Python from python.org (not Microsoft Store). "
            "(4) Check Atlas Network Access allows your IP; (5) Try from WSL or another network (no VPN)."
        )
    return (None, msg)


def get_mongodb_tools(user_id: str) -> List[Any]:
    """Return list of MongoDB tools, bound to the specific user_id."""

    async def _get_client():
        """Get MongoDB client from stored credentials. Returns (client, None) or (None, error_message)."""
        creds = await get_connection_credentials(user_id, "mongodb")
        if not creds:
            logger.info("MongoDB: no credentials for user — connect MongoDB in Settings")
            return (None, "MongoDB is not connected. Please connect it in Settings with your connection string.")
        connection_string = creds.get("token", "")
        if not connection_string:
            logger.info("MongoDB: connection string empty — set it in Settings")
            return (None, "MongoDB is not connected. Please connect it in Settings with your connection string.")
        logger.info("MongoDB tool: connecting to Atlas (URI present)...")
        return _get_mongo_client(connection_string)

    @tool
    async def list_mongo_databases() -> str:
        """
        List all databases and their collections in the connected MongoDB instance.
        Use this first to discover what data is available.
        """
        client, err = await _get_client()
        if not client:
            return err or "MongoDB is not connected. Please connect it in Settings with your connection string."

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
        client, err = await _get_client()
        if not client:
            return err or "MongoDB is not connected. Please connect it in Settings with your connection string."

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
        client, err = await _get_client()
        if not client:
            return err or "MongoDB is not connected. Please connect it in Settings with your connection string."

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
