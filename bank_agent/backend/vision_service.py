"""
PAIOS Vision Service
====================
Analyzes uploaded images of robots/machinery using Groq Vision AI.

Flow:
1. User uploads image of broken robot/machine
2. Image converted to base64
3. Sent to Groq LLaMA Vision model
4. Model identifies: robot model, visible fault, error codes
5. Knowledge Graph queries repair procedures
6. Full diagnosis returned to user
"""

import os
import base64
import logging
from typing import Dict, Any, Optional
from groq import Groq
from knowledge_graph import get_knowledge_graph

logger = logging.getLogger(__name__)


class VisionService:
    """
    Vision AI service for robot fault image analysis.
    Uses Groq's vision-capable model to analyze robot images.
    """

    def __init__(self):
        self.groq_client = None
        self._initialized = False

    def initialize(self):
        groq_key = os.getenv(
            "GROQ_API_KEY",
            "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"
        )
        self.groq_client = Groq(api_key=groq_key)
        self._initialized = True
        logger.info("✅ Vision Service initialized")

    async def analyze_robot_image(
        self,
        image_data: bytes,
        image_mime_type: str = "image/jpeg",
        additional_context: str = "",
        robot_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a robot/machine image for fault diagnosis.

        Steps:
        1. Convert image to base64
        2. Send to Groq vision model
        3. Extract robot ID and fault from response
        4. Query knowledge graph for repair procedures
        5. Return full diagnosis
        """
        if not self._initialized:
            self.initialize()

        try:
            # Step 1 — Convert image to base64
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            # Step 2 — Build vision prompt
            robot_context = ""
            if robot_id:
                kg = get_knowledge_graph()
                robot_info = kg.get_robot_info(robot_id)
                if robot_info:
                    robot_context = f"\nThis robot is identified as: {robot_info.get('name')} by {robot_info.get('manufacturer')}."

            system_prompt = """You are PAIOS Vision AI — an expert in industrial robot and cobot fault diagnosis.
You analyze images of robots, machinery, and control panels to identify:
1. Robot model and manufacturer (if visible)
2. Error codes shown on displays or pendant screens
3. Visible physical damage or abnormalities
4. Warning lights or indicators
5. Potential fault type based on visual evidence

Known robots: ABB GoFa (CRB 15000), KUKA LBR iisy, Yaskawa ArcWorld, Universal Robots UR10e, Fanuc CRX-10iA

Always respond in this structured format:
ROBOT_IDENTIFIED: [robot name or "Unknown"]
MANUFACTURER: [manufacturer or "Unknown"]  
ERROR_CODE: [error code if visible or "Not visible"]
FAULT_TYPE: [type of fault observed]
VISIBLE_SYMPTOMS: [list what you can see]
SEVERITY: [LOW/MEDIUM/HIGH/CRITICAL]
INITIAL_ASSESSMENT: [brief expert assessment]
RECOMMENDED_ACTION: [immediate action to take]"""

            user_message = f"Analyze this robot/machinery image for faults.{robot_context}"
            if additional_context:
                user_message += f"\nAdditional context from operator: {additional_context}"

            # Step 3 — Call Groq Vision
            response = self.groq_client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_mime_type};base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": user_message
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=1000
            )

            vision_response = response.choices[0].message.content

            # Step 4 — Parse structured response
            parsed = self._parse_vision_response(vision_response)

            # Step 5 — Query knowledge graph if robot/fault identified
            kg_diagnosis = None
            identified_robot_id = robot_id

            if not identified_robot_id:
                identified_robot_id = self._match_robot_to_id(parsed.get("ROBOT_IDENTIFIED", ""))

            if identified_robot_id and parsed.get("ERROR_CODE", "Not visible") != "Not visible":
                kg = get_knowledge_graph()
                kg_diagnosis = kg.diagnose_fault(
                    identified_robot_id,
                    parsed.get("ERROR_CODE", "")
                )

            # Step 6 — Generate comprehensive answer using both vision + graph
            final_answer = await self._generate_final_diagnosis(
                vision_analysis=parsed,
                raw_vision_response=vision_response,
                kg_diagnosis=kg_diagnosis,
                robot_id=identified_robot_id
            )

            return {
                "success": True,
                "vision_analysis": parsed,
                "raw_vision_response": vision_response,
                "knowledge_graph_diagnosis": kg_diagnosis,
                "robot_identified": identified_robot_id,
                "fault_code": parsed.get("ERROR_CODE"),
                "severity": parsed.get("SEVERITY", "UNKNOWN"),
                "final_answer": final_answer,
                "model_used": "llama-4-scout-17b (Groq Vision)"
            }

        except Exception as e:
            logger.error(f"Vision analysis failed: {str(e)}")

            # Fallback — use text-only analysis
            return await self._fallback_text_analysis(additional_context, robot_id, str(e))

    def _parse_vision_response(self, response: str) -> Dict[str, str]:
        """Parse structured vision response into dictionary."""
        parsed = {}
        lines = response.strip().split("\n")
        for line in lines:
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().upper().replace(" ", "_")
                value = value.strip()
                if key in ["ROBOT_IDENTIFIED", "MANUFACTURER", "ERROR_CODE",
                           "FAULT_TYPE", "VISIBLE_SYMPTOMS", "SEVERITY",
                           "INITIAL_ASSESSMENT", "RECOMMENDED_ACTION"]:
                    parsed[key] = value
        return parsed

    def _match_robot_to_id(self, robot_name: str) -> Optional[str]:
        """Match robot name from vision to knowledge graph ID."""
        if not robot_name or robot_name.lower() == "unknown":
            return None

        name_lower = robot_name.lower()
        mappings = {
            "ABB_GOFA": ["abb", "gofa", "crb 15000", "crb15000"],
            "KUKA_LBR_IISY": ["kuka", "lbr", "iisy"],
            "YASKAWA_ARCWORLD": ["yaskawa", "arcworld", "motoman"],
            "UNIVERSAL_ROBOTS_UR10E": ["universal", "ur10", "ur5", "ur3"],
            "FANUC_CRX": ["fanuc", "crx"],
        }

        for robot_id, keywords in mappings.items():
            if any(kw in name_lower for kw in keywords):
                return robot_id

        return None

    async def _generate_final_diagnosis(
        self,
        vision_analysis: Dict,
        raw_vision_response: str,
        kg_diagnosis: Optional[Dict],
        robot_id: Optional[str]
    ) -> str:
        """Generate comprehensive diagnosis combining vision + knowledge graph."""

        # Build context
        context = f"""VISION AI ANALYSIS:
{raw_vision_response}
"""

        if kg_diagnosis and kg_diagnosis.get("fault"):
            kg = get_knowledge_graph()
            context += f"\n{kg.format_diagnosis_for_llm(kg_diagnosis)}"

        prompt = f"""Based on the vision analysis and knowledge graph data below, provide a clear, 
professional diagnosis and repair guidance for the technician.

{context}

Provide:
1. Summary of what was identified
2. Severity assessment
3. Immediate safety steps
4. Step-by-step repair procedure
5. Tools needed
6. When to escalate to specialist"""

        response = self.groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are PAIOS AI, an expert robot maintenance engineer. Give clear, safe, actionable repair guidance."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1200
        )

        return response.choices[0].message.content

    async def _fallback_text_analysis(
        self,
        context: str,
        robot_id: Optional[str],
        error: str
    ) -> Dict[str, Any]:
        """Fallback when vision model is unavailable."""
        logger.warning(f"Vision fallback used: {error}")

        fallback_answer = """I wasn't able to analyze the image directly, but here's what you can do:

**Immediate Steps:**
1. Check the robot's teach pendant or control panel for any error codes
2. Note any warning lights (red = fault, yellow = warning, green = normal)
3. Listen for unusual sounds (grinding, clicking, buzzing)
4. Check if any axis appears to be in an unusual position

**To get specific help:**
- Tell me the error code shown on the display
- Describe what happened just before the fault
- Mention the robot model if you know it

I can then provide exact repair procedures from the knowledge graph."""

        return {
            "success": False,
            "vision_analysis": {},
            "raw_vision_response": f"Vision analysis unavailable: {error}",
            "knowledge_graph_diagnosis": None,
            "robot_identified": robot_id,
            "fault_code": None,
            "severity": "UNKNOWN",
            "final_answer": fallback_answer,
            "model_used": "fallback"
        }


# Global instance
_vision_service = None


def get_vision_service() -> VisionService:
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
        _vision_service.initialize()
    return _vision_service
