"""
RAG (Retrieval Augmented Generation) Service for Banking Agent
Uses ChromaDB for vector storage and Groq (LLaMA 3) for generation.

WORKFLOW:
1. At startup → load all customer data + banking policies into ChromaDB
2. On each question → retrieve relevant chunks → send to Groq → return answer

DOCUMENTS USED:
- Customer profiles (demographics, credit, fraud, income data)
- Banking policies (credit rules, risk thresholds)
- Investigation results (from active sessions)
- Conversation history (for context continuity)
"""

import os
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

# Vector DB
import chromadb
from chromadb.config import Settings

# Embeddings (free, runs locally)
from sentence_transformers import SentenceTransformer

# Groq LLM (free)
from groq import Groq

logger = logging.getLogger(__name__)

# ============================================================
# BANKING KNOWLEDGE BASE — These are the "documents" for RAG
# ============================================================

BANKING_POLICIES = [
    {
        "id": "policy_credit_001",
        "title": "Credit Limit Increase Policy",
        "content": """
        Credit Limit Increase Guidelines:
        - Customers with FICO score above 750 qualify for up to 50% credit limit increase
        - Customers with FICO score 700-749 qualify for up to 30% increase
        - Customers with FICO score 650-699 qualify for up to 15% increase
        - Customers with FICO score below 650 are not eligible for increase
        - Debt-to-income ratio must be below 43% for any increase
        - Customer must have at least 12 months account history
        - No more than 2 late payments in the last 12 months
        - Credit utilization should ideally be below 30% after increase
        """,
        "category": "credit_policy"
    },
    {
        "id": "policy_risk_001",
        "title": "Risk Assessment Framework",
        "content": """
        Risk Assessment Levels:
        - LOW RISK: FICO > 720, utilization < 30%, 0 late payments, DTI < 30%
        - MEDIUM RISK: FICO 650-720, utilization 30-60%, 1-2 late payments, DTI 30-43%
        - HIGH RISK: FICO < 650, utilization > 60%, 3+ late payments, DTI > 43%
        
        Fraud Risk Scores:
        - Score 0-3: Low fraud risk, proceed normally
        - Score 3-7: Medium risk, additional verification required
        - Score 7-10: High risk, escalate to fraud team
        
        KYC Requirements:
        - All customers must have verified identity status
        - KYC score above 70 is considered satisfactory
        - KYC score below 70 requires re-verification
        """,
        "category": "risk_policy"
    },
    {
        "id": "policy_income_001",
        "title": "Income Verification Standards",
        "content": """
        Income Verification Policy:
        - Verified annual income must be confirmed via pay stubs or tax returns
        - Income stability score above 80 indicates reliable income
        - Income stability score 60-80 requires additional documentation
        - Income stability score below 60 indicates unstable income — caution advised
        - Self-employed customers require 2 years of tax returns
        - Part-time employment income can be counted at 75% of stated amount
        - Monthly debt payments should not exceed 43% of monthly gross income
        """,
        "category": "income_policy"
    },
    {
        "id": "policy_fraud_001",
        "title": "Fraud Detection and Prevention",
        "content": """
        Fraud Prevention Guidelines:
        - Identity verification is mandatory for all credit decisions
        - Customers with fraud risk score above 7 must be reviewed by fraud team
        - Unusual spending patterns should trigger additional review
        - Address changes within 30 days of credit request are flagged
        - Multiple credit applications within 30 days indicate potential fraud
        - KYC verification status must be 'verified' for any credit increase
        - Open banking data inconsistencies must be investigated
        """,
        "category": "fraud_policy"
    },
    {
        "id": "policy_decision_001",
        "title": "Credit Decision Documentation Requirements",
        "content": """
        Decision Documentation Standards:
        - All credit decisions must be documented with justification
        - Approved decisions must include: new limit, risk assessment, key factors
        - Rejected decisions must include: specific reasons citing policy
        - Partial approvals must explain the difference from requested amount
        - All decisions are subject to quarterly audit review
        - Agent must document all data sources used in decision
        - Decisions above $50,000 require supervisor approval
        - Customer must be notified within 24 hours of decision
        """,
        "category": "decision_policy"
    },
    {
        "id": "policy_segments_001",
        "title": "Customer Segment Guidelines",
        "content": """
        Customer Segments and Benefits:
        
        BASIC segment:
        - Standard credit products only
        - No premium features
        - Maximum credit limit: $15,000
        
        STANDARD segment:
        - Standard + some premium products
        - Priority customer service
        - Maximum credit limit: $30,000
        
        PREMIUM segment:
        - All products available
        - Dedicated relationship manager
        - Maximum credit limit: $75,000
        - Eligible for special interest rates
        
        Segment upgrades reviewed annually based on payment history and income growth.
        """,
        "category": "segment_policy"
    }
]


class RAGService:
    """
    RAG Service for Banking Agent.
    
    Combines:
    - ChromaDB: stores document embeddings locally
    - SentenceTransformers: creates embeddings (free, local)
    - Groq LLaMA 3: generates intelligent answers (free API)
    """

    def __init__(self):
        self.groq_client = None
        self.chroma_client = None
        self.collection = None
        self.embedding_model = None
        self._initialized = False
        logger.info("RAG Service created")

    async def initialize(self, mock_databases: Dict[str, Any]):
        """
        Initialize RAG service and load all documents.
        Called once at startup.
        
        Documents loaded:
        1. Banking policies (credit rules, risk thresholds)
        2. Customer profiles (all 10 customers from mock DB)
        3. Customer financial data (banking, credit, fraud, income)
        """
        if self._initialized:
            return

        try:
            logger.info("🚀 Initializing RAG Service...")

            # Step 1 — Initialize Groq client
            # Step 1 — Initialize Groq client
            groq_key = os.getenv("GROQ_API_KEY", "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")
            self.groq_client = Groq(api_key=groq_key)

            # Step 2 — Initialize embedding model (runs locally, free)
            logger.info("📦 Loading embedding model (first time may take 30 seconds)...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedding model loaded")

            # Step 3 — Initialize ChromaDB (local vector database)
            self.chroma_client = chromadb.Client(Settings(
                anonymized_telemetry=False
            ))
            
            # Create or get collection
            try:
                self.chroma_client.delete_collection("banking_knowledge")
            except:
                pass
            
            self.collection = self.chroma_client.create_collection(
                name="banking_knowledge",
                metadata={"description": "Banking agent knowledge base"}
            )
            logger.info("✅ ChromaDB collection created")

            # Step 4 — Load all documents into vector store
            await self._load_banking_policies()
            await self._load_customer_data(mock_databases)
            logger.info("✅ All documents loaded into vector store")

            self._initialized = True
            logger.info("🎉 RAG Service fully initialized!")

        except Exception as e:
            logger.error(f"❌ RAG Service initialization failed: {str(e)}")
            raise

    async def _load_banking_policies(self):
        """Load banking policy documents into ChromaDB."""
        logger.info("📄 Loading banking policies...")
        
        documents = []
        embeddings = []
        ids = []
        metadatas = []

        for policy in BANKING_POLICIES:
            # Create embedding for this policy
            embedding = self.embedding_model.encode(
                policy["title"] + " " + policy["content"]
            ).tolist()

            documents.append(policy["content"])
            embeddings.append(embedding)
            ids.append(policy["id"])
            metadatas.append({
                "title": policy["title"],
                "category": policy["category"],
                "type": "policy",
                "source": "banking_policies"
            })

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )
        logger.info(f"✅ Loaded {len(BANKING_POLICIES)} banking policy documents")

    async def _load_customer_data(self, mock_databases: Dict[str, Any]):
        """
        Load all customer data into ChromaDB.
        
        For each customer, creates a rich text document combining:
        - Demographics (name, income, employment, state)
        - Banking data (credit limit, balance, utilization, payments)
        - Credit bureau (FICO scores, delinquencies)
        - Fraud/KYC (risk scores, verification status)
        - Income data (verified income, DTI ratio, stability)
        """
        logger.info("👥 Loading customer data...")

        documents = []
        embeddings = []
        ids = []
        metadatas = []

        demographics = mock_databases.get("customer_demographics", [])
        banking_data = {d["customer_id"]: d for d in mock_databases.get("internal_banking_data", [])}
        credit_data = {d["customer_id"]: d for d in mock_databases.get("credit_bureau_data", [])}
        fraud_data = {d["customer_id"]: d for d in mock_databases.get("fraud_kyc_compliance", [])}
        income_data = {d["customer_id"]: d for d in mock_databases.get("income_ability_to_pay", [])}
        open_banking = {d["customer_id"]: d for d in mock_databases.get("open_banking_data", [])}

        for customer in demographics:
            cid = customer["customer_id"]

            # Build rich text document for this customer
            doc_text = f"""
Customer ID: {cid}
Name: {customer['first_name']} {customer['last_name']}
Email: {customer.get('email', 'N/A')}
Date of Birth: {customer.get('date_of_birth', 'N/A')}
Annual Income: ${customer.get('annual_income', 0):,}
Employment Status: {customer.get('employment_status', 'N/A')}
Customer Segment: {customer.get('customer_segment', 'N/A')}
State: {customer.get('state', 'N/A')}
City: {customer.get('city', 'N/A')}
Customer Since: {customer.get('customer_since', 'N/A')}
Employer: {customer.get('employer_name', 'N/A')}
Job Title: {customer.get('job_title', 'N/A')}
Household Size: {customer.get('household_size', 'N/A')}
"""

            # Add banking data
            bd = banking_data.get(cid, {})
            if bd:
                doc_text += f"""
BANKING DATA:
Current Credit Limit: ${bd.get('current_credit_limit', 0):,}
Current Balance: ${bd.get('current_balance', 0):,.2f}
Utilization Rate: {bd.get('utilization_rate', 0):.1f}%
On-time Payments (12m): {bd.get('on_time_payments_12m', 0)}
Late Payments (12m): {bd.get('late_payments_12m', 0)}
Account Tenure: {bd.get('tenure_months', 0)} months
"""

            # Add credit bureau data
            cd = credit_data.get(cid, {})
            if cd:
                doc_text += f"""
CREDIT BUREAU DATA:
FICO Score 8: {cd.get('fico_score_8', 'N/A')}
FICO Score 9: {cd.get('fico_score_9', 'N/A')}
Total Accounts: {cd.get('total_accounts_bureau', 0)}
Delinquencies (30+ days, 12m): {cd.get('delinquencies_30_plus_12m', 0)}
"""

            # Add fraud/KYC data
            fd = fraud_data.get(cid, {})
            if fd:
                doc_text += f"""
FRAUD AND KYC:
Fraud Risk Score: {fd.get('overall_fraud_risk_score', 0):.2f}
Risk Level: {fd.get('risk_level', 'N/A')}
KYC Score: {fd.get('kyc_score', 0):.1f}
Identity Verification: {fd.get('identity_verification_status', 'N/A')}
"""

            # Add income data
            ind = income_data.get(cid, {})
            if ind:
                doc_text += f"""
INCOME AND ABILITY TO PAY:
Verified Annual Income: ${ind.get('verified_annual_income', 0):,.0f}
Debt-to-Income Ratio: {ind.get('debt_to_income_ratio', 0)*100:.1f}%
Monthly Debt Payments: ${ind.get('total_monthly_debt_payments', 0):,.0f}
Income Stability Score: {ind.get('income_stability_score', 0):.1f}
"""

            # Add open banking
            ob = open_banking.get(cid, {})
            if ob:
                doc_text += f"""
OPEN BANKING:
Consent Given: {ob.get('open_banking_consent', False)}
Average Monthly Income: ${ob.get('avg_monthly_income', 0):,.0f}
Cash Flow Stability: {ob.get('cash_flow_stability_score', 0):.1f}
Monthly Rent/Obligations: ${ob.get('expense_obligations_rent', 0):,}
"""

            # Create embedding
            embedding = self.embedding_model.encode(doc_text).tolist()

            documents.append(doc_text)
            embeddings.append(embedding)
            ids.append(f"customer_{cid}")
            metadatas.append({
                "customer_id": str(cid),
                "customer_name": f"{customer['first_name']} {customer['last_name']}",
                "type": "customer_profile",
                "source": "mock_database"
            })

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )
        logger.info(f"✅ Loaded {len(demographics)} customer profiles")

    def add_investigation_result(self, session_id: str, customer_name: str,
                                  customer_id: int, result_text: str):
        """
        Add investigation results to vector store dynamically.
        Called when an investigation is completed.
        """
        try:
            doc_id = f"investigation_{session_id}"
            embedding = self.embedding_model.encode(result_text).tolist()

            self.collection.add(
                documents=[result_text],
                embeddings=[embedding],
                ids=[doc_id],
                metadatas=[{
                    "type": "investigation_result",
                    "session_id": session_id,
                    "customer_id": str(customer_id),
                    "customer_name": customer_name,
                    "timestamp": datetime.now().isoformat()
                }]
            )
            logger.info(f"✅ Investigation result added to RAG: {session_id}")
        except Exception as e:
            logger.error(f"Failed to add investigation result: {str(e)}")

    def retrieve_relevant_context(self, query: str, customer_id: Optional[int] = None,
                                   n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query.
        
        Steps:
        1. Convert query to embedding vector
        2. Search ChromaDB for similar vectors
        3. Return top N most relevant chunks
        """
        try:
            # Create query embedding
            query_embedding = self.embedding_model.encode(query).tolist()

            # Build where filter
            where_filter = None
            if customer_id:
                # Get both customer-specific and policy documents
                where_filter = {
                    "$or": [
                        {"customer_id": str(customer_id)},
                        {"type": "policy"},
                        {"type": "investigation_result"}
                    ]
                }

            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, self.collection.count()),
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            retrieved = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    retrieved.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i],
                        "relevance_score": 1 - results["distances"][0][i]
                    })

            logger.info(f"Retrieved {len(retrieved)} relevant chunks for query")
            return retrieved

        except Exception as e:
            logger.error(f"Retrieval failed: {str(e)}")
            return []

    async def generate_answer(self, query: str, customer_id: Optional[int] = None,
                               customer_name: Optional[str] = None,
                               conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Main RAG function — retrieve + generate.
        
        Steps:
        1. Retrieve relevant documents from ChromaDB
        2. Build prompt with retrieved context
        3. Send to Groq LLaMA 3
        4. Return generated answer
        """
        if not self._initialized:
            return {
                "success": False,
                "answer": "RAG service not initialized yet. Please wait...",
                "sources": []
            }

        try:
            # Step 1 — RETRIEVE relevant context
            retrieved_docs = self.retrieve_relevant_context(
                query=query,
                customer_id=customer_id,
                n_results=5
            )

            # Step 2 — BUILD context string from retrieved docs
            context_parts = []
            sources = []

            for doc in retrieved_docs:
                meta = doc["metadata"]
                source_type = meta.get("type", "unknown")

                if source_type == "customer_profile":
                    context_parts.append(f"[CUSTOMER DATA]\n{doc['content']}")
                    sources.append(f"Customer Profile: {meta.get('customer_name', 'Unknown')}")
                elif source_type == "policy":
                    context_parts.append(f"[BANKING POLICY: {meta.get('title', '')}]\n{doc['content']}")
                    sources.append(f"Policy: {meta.get('title', '')}")
                elif source_type == "investigation_result":
                    context_parts.append(f"[INVESTIGATION RESULT]\n{doc['content']}")
                    sources.append(f"Investigation: {meta.get('session_id', '')}")

            context_text = "\n\n---\n\n".join(context_parts)

            # Step 3 — BUILD conversation history for multi-turn chat
            messages = [
                {
                    "role": "system",
                    "content": f"""You are an intelligent AI banking analyst assistant for the NeuroStack Banking Agent platform. 
You help banking analysts make informed credit decisions.

You have access to the following retrieved knowledge:

{context_text}

INSTRUCTIONS:
- Always base your answers on the retrieved data above
- Cite specific numbers (FICO scores, income, utilization rates) when relevant  
- Apply banking policies when making recommendations
- Be professional, precise, and data-driven
- If asking about a specific customer, focus on their data
- For credit decisions, always reference the relevant policy
- Keep responses clear and actionable
- Current customer being analyzed: {customer_name or 'Not specified'} (ID: {customer_id or 'N/A'})
"""
                }
            ]

            # Add conversation history for context
            if conversation_history:
                for msg in conversation_history[-6:]:  # Last 3 exchanges
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })

            # Add current question
            messages.append({
                "role": "user",
                "content": query
            })

            # Step 4 — GENERATE answer using Groq LLaMA 3
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.3,
                max_tokens=1024
            )

            answer = response.choices[0].message.content

            return {
                "success": True,
                "answer": answer,
                "sources": list(set(sources)),
                "retrieved_chunks": len(retrieved_docs),
                "model": "llama3-70b-8192",
                "rag_enabled": True
            }

        except Exception as e:
            logger.error(f"RAG generation failed: {str(e)}")
            return {
                "success": False,
                "answer": f"I encountered an error generating the response: {str(e)}",
                "sources": [],
                "rag_enabled": False
            }

    def get_status(self) -> Dict[str, Any]:
        """Get RAG service status."""
        try:
            doc_count = self.collection.count() if self.collection else 0
            return {
                "initialized": self._initialized,
                "total_documents": doc_count,
                "embedding_model": "all-MiniLM-L6-v2",
                "llm_model": "llama3-70b-8192 (Groq)",
                "vector_db": "ChromaDB (local)",
                "documents_breakdown": {
                    "banking_policies": len(BANKING_POLICIES),
                    "customer_profiles": doc_count - len(BANKING_POLICIES) if doc_count > len(BANKING_POLICIES) else 0
                }
            }
        except Exception as e:
            return {"initialized": False, "error": str(e)}


# Global RAG service instance
rag_service = RAGService()


async def get_rag_service() -> RAGService:
    """Get global RAG service instance."""
    return rag_service
