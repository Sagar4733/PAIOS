"""
PAIOS EKG Modeling Agent
========================
Builds the Enterprise Knowledge Graph hierarchy dynamically
from natural language prompts.

Example prompt:
"I have a Toyota plant in Mumbai with 2 body shops.
 Each body shop has 3 welding lines with 5 ABB IRB 1600 robots each."

This agent extracts:
- Factory: Toyota Plant Mumbai
- Plants: Body Shop 1, Body Shop 2
- Lines: Welding Line 1-3 per plant
- Machines: ABB IRB 1600 x5 per line
And creates all nodes + edges in the knowledge graph — NO DUPLICATES.
"""

import os
import json
import logging
import re
from typing import Dict, List, Any, Optional
from groq import Groq

logger = logging.getLogger(__name__)


class EKGModelingAgent:
    """
    Builds factory hierarchy in the knowledge graph from natural language.
    Uses deduplication — never creates duplicate nodes.
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
        logger.info("✅ EKG Modeling Agent initialized")

    async def build_from_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Main function — takes natural language description,
        extracts hierarchy, adds to knowledge graph with deduplication.
        """
        if not self._initialized:
            self.initialize()

        logger.info(f"🏭 Building EKG from prompt: {prompt[:80]}...")

        try:
            # Step 1 — Extract hierarchy from prompt using LLaMA 3
            hierarchy = await self._extract_hierarchy(prompt)

            # Step 2 — Add to knowledge graph with deduplication
            result = self._add_to_graph(hierarchy)

            return {
                "success": True,
                "hierarchy": hierarchy,
                "nodes_created": result["nodes_created"],
                "nodes_updated": result["nodes_updated"],
                "edges_created": result["edges_created"],
                "summary": self._build_summary(hierarchy, result),
                "graph_stats": self._get_stats()
            }

        except Exception as e:
            logger.error(f"EKG build error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "nodes_created": 0,
                "nodes_updated": 0,
                "edges_created": 0
            }

    async def _extract_hierarchy(self, prompt: str) -> Dict:
        """Use LLaMA 3 to extract factory hierarchy from natural language."""

        system = """You are an expert at extracting manufacturing factory hierarchy from text.
Extract the complete hierarchy in JSON format.

HIERARCHY LEVELS (in order):
1. factory - The overall facility/company plant
2. plant - A specific building or area within the factory
3. line - A production/manufacturing line within a plant
4. machine - Individual machines/robots on the line
5. component - Key components of each machine

RULES:
- Always use UPPERCASE_WITH_UNDERSCORES for IDs
- Generate realistic IDs from names
- If count is mentioned (e.g. "5 robots"), create that many machine entries
- Keep names clean and professional
- If component info not mentioned, use standard robot components

Return ONLY valid JSON, no other text:
{
  "factories": [
    {
      "id": "TOYOTA_PLANT_MUMBAI",
      "name": "Toyota Plant Mumbai",
      "location": "Mumbai, India",
      "industry": "Automotive",
      "plants": [
        {
          "id": "BODY_SHOP_1",
          "name": "Body Shop 1",
          "type": "Welding & Assembly",
          "lines": [
            {
              "id": "WELDING_LINE_1",
              "name": "Welding Line 1",
              "type": "Arc Welding",
              "machines": [
                {
                  "id": "ABB_IRB1600_WL1_001",
                  "name": "ABB IRB 1600",
                  "model": "IRB 1600-10/1.45",
                  "manufacturer": "ABB",
                  "serial": "WL1-001",
                  "components": ["Joint Motor", "Encoder", "Controller"]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}"""

        response = self.groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Extract the factory hierarchy from this description:\n\n{prompt}"}
            ],
            temperature=0.1,
            max_tokens=3000
        )

        raw = response.choices[0].message.content.strip()
        # Clean JSON
        raw = re.sub(r'```json\s*', '', raw)
        raw = re.sub(r'```\s*', '', raw)
        raw = raw.strip()
        # Find JSON object
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1:
            raw = raw[start:end+1]

        return json.loads(raw)

    def _add_to_graph(self, hierarchy: Dict) -> Dict:
        """
        Add hierarchy to knowledge graph with full deduplication.
        Never creates duplicate nodes — updates existing ones instead.
        """
        from knowledge_graph import get_knowledge_graph
        kg = get_knowledge_graph()

        nodes_created = 0
        nodes_updated = 0
        edges_created = 0

        def upsert_node(node_id: str, node_type: str, **attrs):
            """Insert or update node — never duplicate."""
            nonlocal nodes_created, nodes_updated
            if node_id in kg.graph.nodes:
                # UPDATE existing node with new info
                kg.graph.nodes[node_id].update(attrs)
                nodes_updated += 1
                logger.info(f"🔄 Updated existing node: {node_id}")
            else:
                # CREATE new node
                kg.graph.add_node(node_id, node_type=node_type, **attrs)
                nodes_created += 1
                logger.info(f"➕ Created new node: {node_id}")

        def upsert_edge(from_id: str, to_id: str, relationship: str):
            """Insert edge only if it doesn't exist."""
            nonlocal edges_created
            if from_id in kg.graph.nodes and to_id in kg.graph.nodes:
                if not kg.graph.has_edge(from_id, to_id):
                    kg.graph.add_edge(from_id, to_id, relationship=relationship)
                    edges_created += 1

        for factory in hierarchy.get("factories", []):
            # Factory node
            upsert_node(
                factory["id"], "FACTORY",
                name=factory["name"],
                location=factory.get("location", ""),
                industry=factory.get("industry", "Manufacturing"),
                ekg_level="factory",
                auto_extracted=True
            )

            for plant in factory.get("plants", []):
                # Plant node
                upsert_node(
                    plant["id"], "PLANT",
                    name=plant["name"],
                    plant_type=plant.get("type", ""),
                    parent_factory=factory["id"],
                    ekg_level="plant",
                    auto_extracted=True
                )
                upsert_edge(factory["id"], plant["id"], "HAS_PLANT")

                for line in plant.get("lines", []):
                    # Line node
                    upsert_node(
                        line["id"], "PRODUCTION_LINE",
                        name=line["name"],
                        line_type=line.get("type", ""),
                        parent_plant=plant["id"],
                        ekg_level="line",
                        auto_extracted=True
                    )
                    upsert_edge(plant["id"], line["id"], "HAS_LINE")

                    for machine in line.get("machines", []):
                        # Machine node
                        upsert_node(
                            machine["id"], "MACHINE",
                            name=machine["name"],
                            model=machine.get("model", ""),
                            manufacturer=machine.get("manufacturer", ""),
                            serial=machine.get("serial", ""),
                            parent_line=line["id"],
                            ekg_level="machine",
                            auto_extracted=True
                        )
                        upsert_edge(line["id"], machine["id"], "HAS_MACHINE")

                        # Try to link to existing robot in KG
                        self._link_to_existing_robot(
                            kg, machine["id"],
                            machine.get("manufacturer", ""),
                            machine.get("model", "")
                        )

                        # Component nodes
                        for comp_name in machine.get("components", []):
                            comp_id = f"COMP_{machine['id']}_{comp_name.upper().replace(' ', '_')}"
                            upsert_node(
                                comp_id, "COMPONENT",
                                name=comp_name,
                                parent_machine=machine["id"],
                                ekg_level="component",
                                auto_extracted=True
                            )
                            upsert_edge(machine["id"], comp_id, "HAS_COMPONENT")

        return {
            "nodes_created": nodes_created,
            "nodes_updated": nodes_updated,
            "edges_created": edges_created
        }

    def _link_to_existing_robot(self, kg, machine_id: str, manufacturer: str, model: str):
        """
        Try to connect EKG machine node to existing robot knowledge nodes.
        e.g. ABB IRB 1600 machine → ABB_GOFA robot node with its faults.
        """
        if not manufacturer and not model:
            return

        mfr_lower = manufacturer.lower()
        model_lower = model.lower()

        robot_map = {
            ("abb", "gofa"): "ABB_GOFA",
            ("abb", "irb 1600"): "ABB_GOFA",
            ("abb", "irb1600"): "ABB_GOFA",
            ("kuka", "lbr"): "KUKA_LBR_IISY",
            ("kuka", "iisy"): "KUKA_LBR_IISY",
            ("yaskawa", ""): "YASKAWA_ARCWORLD",
            ("universal", ""): "UNIVERSAL_ROBOTS_UR10E",
            ("ur", ""): "UNIVERSAL_ROBOTS_UR10E",
            ("fanuc", ""): "FANUC_CRX",
        }

        for (mfr_key, model_key), robot_id in robot_map.items():
            if mfr_key in mfr_lower and (not model_key or model_key in model_lower):
                if robot_id in kg.graph.nodes:
                    if not kg.graph.has_edge(machine_id, robot_id):
                        kg.graph.add_edge(machine_id, robot_id, relationship="IS_TYPE")
                        kg.graph.add_edge(robot_id, machine_id, relationship="INSTANCE_OF")
                        logger.info(f"🔗 Linked {machine_id} → {robot_id}")
                break

    def _build_summary(self, hierarchy: Dict, result: Dict) -> str:
        factories = hierarchy.get("factories", [])
        total_plants = sum(len(f.get("plants", [])) for f in factories)
        total_lines = sum(len(l) for f in factories for p in f.get("plants", []) for l in [p.get("lines", [])])
        total_machines = sum(len(m) for f in factories for p in f.get("plants", []) for l in p.get("lines", []) for m in [l.get("machines", [])])

        parts = []
        if factories:
            parts.append(f"{len(factories)} factory" if len(factories) == 1 else f"{len(factories)} factories")
        if total_plants:
            parts.append(f"{total_plants} plant(s)")
        if total_lines:
            parts.append(f"{total_lines} production line(s)")
        if total_machines:
            parts.append(f"{total_machines} machine(s)")

        return (
            f"EKG built: {', '.join(parts)}. "
            f"+{result['nodes_created']} new nodes, "
            f"{result['nodes_updated']} updated, "
            f"+{result['edges_created']} edges."
        )

    def _get_stats(self) -> Dict:
        from knowledge_graph import get_knowledge_graph
        kg = get_knowledge_graph()
        return kg.get_graph_stats()


# Global instance
_ekg_agent = None

def get_ekg_agent() -> EKGModelingAgent:
    global _ekg_agent
    if _ekg_agent is None:
        _ekg_agent = EKGModelingAgent()
        _ekg_agent.initialize()
    return _ekg_agent
