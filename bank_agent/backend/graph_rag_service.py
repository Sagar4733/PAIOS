"""
PAIOS GraphRAG Service
======================
Combines Knowledge Graph + RAG + Groq LLaMA 3

Flow:
1. User asks question or uploads fault description
2. Knowledge Graph finds relevant robot/fault/procedure
3. RAG retrieves additional context from documents
4. Both are combined and sent to Groq LLaMA 3
5. Intelligent answer returned with repair steps
"""

import os
import logging
from typing import Dict, List, Any, Optional
from groq import Groq
from knowledge_graph import get_knowledge_graph

logger = logging.getLogger(__name__)


class GraphRAGService:
    """
    GraphRAG = Knowledge Graph + RAG + LLM

    This is MORE powerful than plain RAG because:
    - Knowledge Graph provides structured relationship data
    - RAG provides additional document context
    - LLM generates human-readable repair guidance
    """

    def __init__(self):
        self.groq_client = None
        self._initialized = False

    def initialize(self):
        """Initialize Groq client and knowledge graph."""
        try:
            groq_key = os.getenv(
                "GROQ_API_KEY",
                "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"
            )
            self.groq_client = Groq(api_key=groq_key)

            # Build knowledge graph
            kg = get_knowledge_graph()
            stats = kg.get_graph_stats()
            logger.info(f"✅ GraphRAG ready: {stats['total_nodes']} nodes, {stats['total_edges']} edges")
            self._initialized = True

        except Exception as e:
            logger.error(f"GraphRAG init failed: {str(e)}")
            raise

    async def answer_question(
        self,
        question: str,
        robot_id: Optional[str] = None,
        fault_code: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Main GraphRAG function.

        Steps:
        1. Extract robot/fault from question if not provided
        2. Query knowledge graph for structured data
        3. Build comprehensive context
        4. Send to Groq LLaMA 3
        5. Return answer
        """
        if not self._initialized:
            self.initialize()

        try:
            kg = get_knowledge_graph()

            # Step 1 — Extract entities from question
            if not robot_id:
                robot_id = self._extract_robot_from_text(question)
            if not fault_code:
                fault_code = self._extract_fault_from_text(question)

            # Step 2 — Query knowledge graph
            graph_context = ""
            sources = []

            if robot_id and fault_code:
                # Full diagnosis
                diagnosis = kg.diagnose_fault(robot_id, fault_code)
                graph_context = kg.format_diagnosis_for_llm(diagnosis)
                sources.append(f"Knowledge Graph: {robot_id} fault {fault_code}")

            elif robot_id:
                # Robot info + all faults
                robot_info = kg.get_robot_info(robot_id)
                faults = kg.get_robot_faults(robot_id)
                similar = kg.get_similar_robots(robot_id)

                if robot_info:
                    graph_context = f"""
ROBOT FROM KNOWLEDGE GRAPH:
Name: {robot_info.get('name')}
Manufacturer: {robot_info.get('manufacturer')}
Type: {robot_info.get('type')}
Payload: {robot_info.get('payload_kg')} kg
Reach: {robot_info.get('reach_mm')} mm
Use Cases: {', '.join(robot_info.get('use_cases', []))}

KNOWN FAULTS FOR THIS ROBOT:
"""
                    for f in faults:
                        graph_context += f"- {f.get('code')}: {f.get('name')} (Severity: {f.get('severity')})\n"

                    if similar:
                        graph_context += "\nSIMILAR ROBOTS:\n"
                        for s in similar:
                            graph_context += f"- {s.get('name')}: {s.get('similarity_reason', '')}\n"

                    sources.append(f"Knowledge Graph: {robot_id} profile")

            else:
                # Symptom-based search
                symptom_faults = kg.search_faults_by_symptom(question)
                if symptom_faults:
                    graph_context = "FAULTS MATCHING YOUR DESCRIPTION:\n"
                    for f in symptom_faults[:5]:
                        robot_info = kg.get_robot_info(f.get("robot", ""))
                        robot_name = robot_info.get("name", "Unknown") if robot_info else "Unknown"
                        graph_context += f"""
Fault: {f.get('code')} - {f.get('name')}
Robot: {robot_name}
Severity: {f.get('severity')}
Description: {f.get('description')}
Symptoms: {', '.join(f.get('symptoms', []))}
"""
                    sources.append("Knowledge Graph: Symptom search")

            # Step 3 — Build system prompt with graph context
            system_prompt = f"""You are PAIOS AI — an expert robotics diagnostic assistant for manufacturing environments.

You help technicians diagnose and repair industrial robots and cobots including:
ABB GoFa, KUKA LBR iisy, Yaskawa ArcWorld, Universal Robots UR10e, and Fanuc CRX.

You have access to an enterprise knowledge graph with structured data about robots, 
fault codes, root causes, and step-by-step repair procedures.

{f"KNOWLEDGE GRAPH DATA:{chr(10)}{graph_context}" if graph_context else ""}

INSTRUCTIONS:
- Always prioritize safety — start with LOCKOUT/TAGOUT procedures
- Give specific, actionable repair steps
- Reference exact fault codes and procedures from the knowledge graph
- Mention required tools and skill level
- Warn about dangers where applicable
- If you don't have specific data, say so and give general guidance
- Be concise but complete — technicians need clear instructions
"""

            # Step 4 — Build messages
            messages = [{"role": "system", "content": system_prompt}]

            if conversation_history:
                for msg in conversation_history[-6:]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })

            messages.append({"role": "user", "content": question})

            # Step 5 — Call Groq LLaMA 3
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.2,
                max_tokens=1500
            )

            answer = response.choices[0].message.content

            return {
                "success": True,
                "answer": answer,
                "sources": sources,
                "graph_context_used": bool(graph_context),
                "robot_identified": robot_id,
                "fault_identified": fault_code,
                "model": "llama-3.3-70b-versatile (Groq)",
                "architecture": "GraphRAG"
            }

        except Exception as e:
            logger.error(f"GraphRAG error: {str(e)}")
            return {
                "success": False,
                "answer": f"I encountered an error: {str(e)}",
                "sources": [],
                "graph_context_used": False
            }

    def _extract_robot_from_text(self, text: str) -> Optional[str]:
        """Extract robot ID from text using keyword matching."""
        text_lower = text.lower()
        robot_keywords = {
            "ABB_GOFA": ["abb gofa", "gofa", "crb 15000", "crb15000", "abb cobot"],
            "KUKA_LBR_IISY": ["kuka lbr", "lbr iisy", "kuka iisy", "kuka cobot"],
            "YASKAWA_ARCWORLD": ["yaskawa", "arcworld", "arc world", "motoman", "yrc1000"],
            "UNIVERSAL_ROBOTS_UR10E": ["universal robots", "ur10", "ur10e", "ur cobot"],
            "FANUC_CRX": ["fanuc crx", "fanuc", "crx-10", "crx10"],
        }
        for robot_id, keywords in robot_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    return robot_id
        return None

    def _extract_fault_from_text(self, text: str) -> Optional[str]:
        """Extract fault code from text."""
        import re
        # Look for patterns like E-001, F-234, A.100, SRVO-023
        patterns = [
            r'[EF]-\d{3}',
            r'A\.\d{3}',
            r'SRVO-\d{3}',
            r'error\s+\w+-?\d+',
            r'fault\s+\w+-?\d+',
            r'alarm\s+\w+\.?\d+'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def get_knowledge_graph_summary(self) -> Dict:
        """Get summary of knowledge graph for status display."""
        kg = get_knowledge_graph()
        stats = kg.get_graph_stats()
        robots = kg.get_all_robots()
        return {
            "stats": stats,
            "robots": [{"id": r["id"], "name": r["name"], "manufacturer": r["manufacturer"]} for r in robots]
        }


# Global instance
_graph_rag_service = None


def get_graph_rag_service() -> GraphRAGService:
    """Get global GraphRAG service."""
    global _graph_rag_service
    if _graph_rag_service is None:
        _graph_rag_service = GraphRAGService()
        _graph_rag_service.initialize()
    return _graph_rag_service
