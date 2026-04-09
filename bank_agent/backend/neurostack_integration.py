"""
NeuroStack Integration Layer for Banking Agent - Local Demo Version
Simplified version that works without Azure services for local demo.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Mock customer data (same as in main.py MOCK_DATABASES)
CUSTOMERS = [
    {"customer_id": 1, "first_name": "John", "last_name": "Doe", "annual_income": 75000, "state": "CA", "employment_status": "Self-employed", "customer_segment": "Standard", "email": "john.doe@email.com"},
    {"customer_id": 2, "first_name": "Jane", "last_name": "Smith", "annual_income": 95000, "state": "NY", "employment_status": "Full-time", "customer_segment": "Standard", "email": "jane.smith@email.com"},
    {"customer_id": 3, "first_name": "Bob", "last_name": "Johnson", "annual_income": 65000, "state": "TX", "employment_status": "Full-time", "customer_segment": "Basic", "email": "bob.johnson@email.com"},
    {"customer_id": 4, "first_name": "Tom", "last_name": "Young", "annual_income": 64485, "state": "CA", "employment_status": "Full-time", "customer_segment": "Standard", "email": "tom.young@email.com"},
    {"customer_id": 5, "first_name": "Michael", "last_name": "Gonzales", "annual_income": 114394, "state": "CA", "employment_status": "Part-time", "customer_segment": "Premium", "email": "michael.gonzales@email.com"},
    {"customer_id": 6, "first_name": "Kyle", "last_name": "Johnson", "annual_income": 62859, "state": "OH", "employment_status": "Full-time", "customer_segment": "Standard", "email": "kyle.johnson@email.com"},
    {"customer_id": 7, "first_name": "Thomas", "last_name": "Pratt", "annual_income": 109841, "state": "IL", "employment_status": "Full-time", "customer_segment": "Premium", "email": "thomas.pratt@email.com"},
    {"customer_id": 8, "first_name": "Brandon", "last_name": "Johnson", "annual_income": 64046, "state": "TX", "employment_status": "Full-time", "customer_segment": "Standard", "email": "brandon.johnson@email.com"},
    {"customer_id": 9, "first_name": "Jacqueline", "last_name": "Gray", "annual_income": 79181, "state": "OH", "employment_status": "Full-time", "customer_segment": "Standard", "email": "jacqueline.gray@email.com"},
    {"customer_id": 10, "first_name": "John", "last_name": "Hoover", "annual_income": 82719, "state": "PA", "employment_status": "Full-time", "customer_segment": "Standard", "email": "john.hoover@email.com"},
]


class NeuroStackBankingIntegration:
    """Simplified integration class for local demo."""

    def __init__(self, tenant_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self._initialized = False
        logger.info("NeuroStackBankingIntegration initialized (demo mode)")

    async def initialize(self):
        if self._initialized:
            return
        self._initialized = True
        logger.info("NeuroStack Banking Integration ready (demo mode)")

    async def execute_text_to_sql(self, natural_query: str, tables: List[Dict[str, Any]],
                                   user_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns failure so main.py falls back to mock SQL generation."""
        return {
            "success": False,
            "error": "Using mock SQL generation for demo",
            "execution_time": 0.0
        }

    async def execute_customer_search(self, query: str, search_type: str = "semantic",
                                       user_id: Optional[str] = None) -> Dict[str, Any]:
        """Search customers by name."""
        query_lower = query.lower()
        results = [
            c for c in CUSTOMERS
            if query_lower in c["first_name"].lower()
            or query_lower in c["last_name"].lower()
            or query_lower in c.get("email", "").lower()
        ]
        return {
            "success": True,
            "customers": results,
            "count": len(results),
            "neurostack_features": {"demo_mode": True}
        }

    async def execute_data_analysis(self, analysis_type: str, data_source: str,
                                     user_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "success": True,
            "analysis_type": analysis_type,
            "data_source": data_source,
            "results": {"message": "Demo mode - analysis not available"},
            "insights": "Running in demo mode without Azure OpenAI.",
            "neurostack_features": {"demo_mode": True}
        }

    async def execute_customer_verification(self, customer_id: int,
                                             verification_type: str = "security_questions",
                                             user_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "success": True,
            "customer_id": customer_id,
            "questions": [
                "What is your mother's maiden name?",
                "What city were you born in?",
                "What was the name of your first pet?"
            ],
            "verification_type": verification_type,
            "neurostack_features": {"demo_mode": True}
        }

    async def get_similar_queries(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        return []

    async def get_recent_activity(self, hours: int = 24) -> Dict[str, Any]:
        return {"message": "Demo mode - no activity tracking"}

    async def generate_customer_summary(self, customer_id: int, customer_data: Dict[str, Any],
                                         prompt: str) -> Dict[str, Any]:
        """Generate a simple text summary without Azure OpenAI."""
        try:
            summary_parts = [f"## Customer {customer_id} Summary\n"]

            if "customer_demographics" in customer_data:
                d = customer_data["customer_demographics"]["data"]
                summary_parts.append(f"**Name:** {d.get('first_name')} {d.get('last_name')}")
                summary_parts.append(f"**Income:** ${d.get('annual_income', 0):,}")
                summary_parts.append(f"**Employment:** {d.get('employment_status')}")
                summary_parts.append(f"**Segment:** {d.get('customer_segment')}\n")

            if "internal_banking_data" in customer_data:
                b = customer_data["internal_banking_data"]["data"]
                summary_parts.append(f"**Credit Limit:** ${b.get('current_credit_limit', 0):,}")
                summary_parts.append(f"**Utilization:** {b.get('utilization_rate', 0):.1f}%")
                summary_parts.append(f"**On-time Payments (12m):** {b.get('on_time_payments_12m', 0)}\n")

            if "credit_bureau_data" in customer_data:
                c = customer_data["credit_bureau_data"]["data"]
                summary_parts.append(f"**FICO Score:** {c.get('fico_score_8', 'N/A')}")
                summary_parts.append(f"**Delinquencies (12m):** {c.get('delinquencies_30_plus_12m', 0)}\n")

            summary_parts.append("*Note: Running in demo mode. Connect Azure OpenAI for AI-powered summaries.*")
            summary = "\n".join(summary_parts)

            return {"success": True, "summary": summary, "neurostack_features": {"demo_mode": True}}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_available_tools(self) -> List[str]:
        return ["text_to_sql", "customer_search", "data_analysis", "customer_verification"]

    def get_tool_schemas(self) -> Dict[str, Dict[str, Any]]:
        return {}

    def search_customers_direct(self, query: str) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        return [
            c for c in CUSTOMERS
            if query_lower in c["first_name"].lower() or query_lower in c["last_name"].lower()
        ]

    def get_customer_by_id_direct(self, customer_id: int) -> Optional[Dict[str, Any]]:
        return next((c for c in CUSTOMERS if c["customer_id"] == customer_id), None)

    async def generate_response(self, prompt: str) -> str:
        return "Demo mode: Azure OpenAI not connected. Please configure Azure credentials for full functionality."


# Global instance
neurostack_integration = None


async def get_neurostack_integration() -> NeuroStackBankingIntegration:
    global neurostack_integration
    if neurostack_integration is None:
        neurostack_integration = NeuroStackBankingIntegration(tenant_id="banking_agent")
        await neurostack_integration.initialize()
    return neurostack_integration


async def execute_neurostack_text_to_sql(natural_query: str, tables: List[Dict[str, Any]],
                                          user_id: Optional[str] = None) -> Dict[str, Any]:
    integration = await get_neurostack_integration()
    return await integration.execute_text_to_sql(natural_query, tables, user_id)


async def execute_neurostack_customer_search(query: str, search_type: str = "semantic",
                                              user_id: Optional[str] = None) -> Dict[str, Any]:
    integration = await get_neurostack_integration()
    return await integration.execute_customer_search(query, search_type, user_id)


async def execute_neurostack_data_analysis(analysis_type: str, data_source: str,
                                            user_id: Optional[str] = None) -> Dict[str, Any]:
    integration = await get_neurostack_integration()
    return await integration.execute_data_analysis(analysis_type, data_source, user_id)


async def execute_neurostack_customer_verification(customer_id: int,
                                                    verification_type: str = "security_questions",
                                                    user_id: Optional[str] = None) -> Dict[str, Any]:
    integration = await get_neurostack_integration()
    return await integration.execute_customer_verification(customer_id, verification_type, user_id)
