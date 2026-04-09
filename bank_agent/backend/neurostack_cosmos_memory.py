"""
NeuroStack Memory Layer - Local Demo Version
Works without Azure Cosmos DB using in-memory storage.
"""

import os
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


class MockContainer:
    """In-memory container replacing Cosmos DB for demo."""

    def __init__(self, name: str):
        self.name = name
        self.items = []

    async def create_item(self, item: Dict[str, Any]):
        item["id"] = item.get("id", str(uuid.uuid4()))
        self.items.append(item)
        return item

    async def upsert_item(self, item: Dict[str, Any]):
        item["id"] = item.get("id", str(uuid.uuid4()))
        self.items = [i for i in self.items if i.get("id") != item.get("id")]
        self.items.append(item)
        return item

    async def read_item(self, id: str, partition_key: str):
        for item in self.items:
            if item.get("id") == id or item.get("user_id") == id:
                return item
        raise Exception("Item not found")

    async def read_all_items(self):
        return self.items.copy()


class CosmosDBMemoryManager:
    """
    Memory manager using in-memory storage for local demo.
    Falls back gracefully when Cosmos DB is not available.
    """

    def __init__(self, connection_string: str = "mock", database_name: str = "mock"):
        self.connection_string = connection_string
        self.database_name = database_name
        self._init_mock_containers()
        logger.info("Memory Manager initialized (demo mode - in-memory storage)")

    def _init_mock_containers(self):
        self.containers = {
            "query_results": MockContainer("query_results"),
            "query_patterns": MockContainer("query_patterns"),
            "user_behaviors": MockContainer("user_behaviors"),
            "semantic_embeddings": MockContainer("semantic_embeddings"),
            "query_analytics": MockContainer("query_analytics"),
            "investigation_executions": MockContainer("investigation_executions")
        }

    async def store_query_result(self, query_data: Dict[str, Any]) -> str:
        try:
            query_id = str(uuid.uuid4())
            item = {
                "id": query_id,
                "query_id": query_id,
                "natural_query": query_data.get("query", ""),
                "sql_generated": query_data.get("sql", ""),
                "result_count": query_data.get("result_count", 0),
                "execution_time": query_data.get("execution_time", 0.0),
                "success": query_data.get("success", False),
                "tables_used": query_data.get("tables", []),
                "query_type": query_data.get("query_type", "general"),
                "user_id": query_data.get("user_id"),
                "timestamp": datetime.now().isoformat(),
            }
            await self.containers["query_results"].create_item(item)
            await self._update_user_behavior(query_data)
            logger.info(f"Query result stored: {query_id}")
            return query_id
        except Exception as e:
            logger.error(f"Failed to store query result: {str(e)}")
            return str(uuid.uuid4())

    async def _update_user_behavior(self, query_data: Dict[str, Any]):
        try:
            user_id = query_data.get("user_id")
            if not user_id:
                return

            container = self.containers["user_behaviors"]
            try:
                behavior = await container.read_item(user_id, user_id)
                behavior["total_queries"] = behavior.get("total_queries", 0) + 1
                behavior["last_activity"] = datetime.now().isoformat()
                query_type = query_data.get("query_type", "general")
                if query_type not in behavior.get("preferred_query_types", []):
                    behavior.setdefault("preferred_query_types", []).append(query_type)
                for table in query_data.get("tables", []):
                    if table not in behavior.get("common_tables", []):
                        behavior.setdefault("common_tables", []).append(table)
                await container.upsert_item(behavior)
            except:
                behavior = {
                    "id": user_id,
                    "user_id": user_id,
                    "preferred_query_types": [query_data.get("query_type", "general")],
                    "common_tables": query_data.get("tables", []),
                    "avg_query_complexity": 1.0,
                    "session_patterns": {},
                    "last_activity": datetime.now().isoformat(),
                    "total_queries": 1
                }
                await container.upsert_item(behavior)
        except Exception as e:
            logger.error(f"Failed to update user behavior: {str(e)}")

    async def get_similar_queries(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            items = await self.containers["query_results"].read_all_items()
            results = []
            query_lower = query.lower()
            for item in items:
                stored = item.get("natural_query", "").lower()
                # Simple word overlap similarity
                query_words = set(query_lower.split())
                stored_words = set(stored.split())
                if query_words & stored_words:
                    results.append({
                        "query": item.get("natural_query"),
                        "sql": item.get("sql_generated"),
                        "similarity": len(query_words & stored_words) / max(len(query_words), 1),
                        "query_type": item.get("query_type"),
                        "success": item.get("success")
                    })
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:limit]
        except Exception as e:
            logger.error(f"Failed to get similar queries: {str(e)}")
            return []

    async def get_query_result(self, query_id: str) -> Optional[Dict[str, Any]]:
        try:
            items = await self.containers["query_results"].read_all_items()
            return next((i for i in items if i.get("query_id") == query_id), None)
        except Exception as e:
            logger.error(f"Failed to get query result: {str(e)}")
            return None

    async def get_query_patterns(self, query_type: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            items = await self.containers["query_patterns"].read_all_items()
            if query_type:
                return [p for p in items if p.get("query_type") == query_type]
            return items
        except Exception as e:
            logger.error(f"Failed to get query patterns: {str(e)}")
            return []

    async def get_user_behavior(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await self.containers["user_behaviors"].read_item(user_id, user_id)
        except Exception as e:
            logger.error(f"Failed to get user behavior: {str(e)}")
            return None

    async def get_query_analytics(self, hours: int = 24) -> Dict[str, Any]:
        try:
            items = await self.containers["query_results"].read_all_items()
            cutoff = datetime.now() - timedelta(hours=hours)
            recent = []
            for item in items:
                try:
                    ts = datetime.fromisoformat(item.get("timestamp", "2000-01-01"))
                    if ts > cutoff:
                        recent.append(item)
                except:
                    pass

            if not recent:
                return {"message": "No recent queries found", "total_queries": 0}

            return {
                "total_queries": len(recent),
                "success_rate": sum(1 for r in recent if r.get("success")) / len(recent),
                "avg_execution_time": sum(r.get("execution_time", 0) for r in recent) / len(recent),
                "query_types": {},
                "most_used_tables": {}
            }
        except Exception as e:
            logger.error(f"Failed to get query analytics: {str(e)}")
            return {"error": str(e)}

    async def get_optimization_suggestions(self, query: str,
                                            user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            similar = await self.get_similar_queries(query, limit=3)
            suggestions = []
            if similar:
                suggestions.append({
                    "type": "similar_query",
                    "message": f"Found {len(similar)} similar past queries",
                    "examples": similar[:2]
                })
            return suggestions
        except Exception as e:
            logger.error(f"Failed to get optimization suggestions: {str(e)}")
            return []

    async def store_investigation_execution(self, execution_data: Dict[str, Any]) -> str:
        try:
            execution_id = execution_data.get("execution_id", str(uuid.uuid4()))
            execution_data["id"] = execution_id
            await self.containers["investigation_executions"].upsert_item(execution_data)
            return execution_id
        except Exception as e:
            logger.error(f"Failed to store investigation execution: {str(e)}")
            return str(uuid.uuid4())

    async def get_investigation_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await self.containers["investigation_executions"].read_item(
                execution_id, execution_id
            )
        except Exception as e:
            logger.error(f"Failed to get investigation execution: {str(e)}")
            return None


# Global instance
cosmos_memory_manager = None


async def get_cosmos_memory_manager() -> CosmosDBMemoryManager:
    global cosmos_memory_manager
    if cosmos_memory_manager is None:
        logger.info("Initializing in-memory storage (demo mode)")
        cosmos_memory_manager = CosmosDBMemoryManager("mock", "mock")
    return cosmos_memory_manager
