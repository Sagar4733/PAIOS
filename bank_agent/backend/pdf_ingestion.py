"""
PAIOS PDF Ingestion Pipeline
============================
Automatically builds the Knowledge Graph from uploaded robot manuals.

FLOW:
1. User uploads PDF (e.g. ABB_IRB1600_Manual.pdf)
2. Extract all text from PDF using pdfplumber
3. Send text to Groq LLaMA 3 with structured extraction prompt
4. LLaMA extracts: robot model, fault codes, components, procedures
5. Add extracted entities as nodes/edges to NetworkX knowledge graph
6. User can now query the graph built from the actual manual
"""

import os
import json
import logging
import re
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


@dataclass
class ExtractedRobot:
    id: str
    name: str
    manufacturer: str
    model_number: str
    robot_type: str
    payload_kg: Optional[float]
    reach_mm: Optional[float]
    axes: Optional[int]
    use_cases: List[str]
    description: str
    source_document: str


@dataclass
class ExtractedFault:
    id: str
    robot_id: str
    code: str
    name: str
    severity: str
    description: str
    symptoms: List[str]
    causes: List[str]
    source_document: str


@dataclass
class ExtractedProcedure:
    id: str
    name: str
    applicable_fault_codes: List[str]
    estimated_time_minutes: int
    skill_level: str
    tools_required: List[str]
    steps: List[str]
    warning: str
    source_document: str


@dataclass
class IngestionResult:
    document_id: str
    filename: str
    status: str
    robots_extracted: int
    faults_extracted: int
    procedures_extracted: int
    nodes_added: int
    edges_added: int
    error: Optional[str]
    timestamp: str
    robots: List[Dict] = field(default_factory=list)
    faults: List[Dict] = field(default_factory=list)
    procedures: List[Dict] = field(default_factory=list)


class PDFIngestionPipeline:
    """
    Automatically extracts robot knowledge from PDF manuals
    and populates the PAIOS Knowledge Graph.
    """

    def __init__(self):
        self.groq_client = None
        self._initialized = False
        self.ingestion_history: List[IngestionResult] = []

    def initialize(self):
        from groq import Groq
        groq_key = os.getenv(
            "GROQ_API_KEY",
            "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"
        )
        self.groq_client = Groq(api_key=groq_key)
        self._initialized = True
        logger.info("✅ PDF Ingestion Pipeline initialized")

    async def ingest_pdf(
        self,
        pdf_bytes: bytes,
        filename: str
    ) -> IngestionResult:
        """
        Main ingestion function.

        Steps:
        1. Extract text from PDF
        2. Chunk text into manageable pieces
        3. Extract entities using LLaMA 3
        4. Add to knowledge graph
        """
        if not self._initialized:
            self.initialize()

        doc_id = str(uuid.uuid4())[:8]
        logger.info(f"📄 Starting ingestion: {filename} (ID: {doc_id})")

        result = IngestionResult(
            document_id=doc_id,
            filename=filename,
            status="processing",
            robots_extracted=0,
            faults_extracted=0,
            procedures_extracted=0,
            nodes_added=0,
            edges_added=0,
            error=None,
            timestamp=datetime.now().isoformat()
        )

        try:
            # Step 1 — Extract text from PDF
            logger.info("📖 Extracting text from PDF...")
            text = self._extract_pdf_text(pdf_bytes)

            if not text or len(text) < 100:
                result.status = "failed"
                result.error = "Could not extract text from PDF. May be scanned/image-based."
                return result

            logger.info(f"✅ Extracted {len(text)} characters from PDF")

            # Step 2 — Extract robot model info
            logger.info("🤖 Extracting robot information...")
            robots = await self._extract_robots(text, filename)
            result.robots = [asdict(r) for r in robots]
            result.robots_extracted = len(robots)
            logger.info(f"✅ Found {len(robots)} robot model(s)")

            # Step 3 — Extract fault codes
            logger.info("⚠️ Extracting fault codes...")
            robot_id = robots[0].id if robots else f"ROBOT_{doc_id}"
            faults = await self._extract_faults(text, robot_id, filename)
            result.faults = [asdict(f) for f in faults]
            result.faults_extracted = len(faults)
            logger.info(f"✅ Found {len(faults)} fault code(s)")

            # Step 4 — Extract repair procedures
            logger.info("🔧 Extracting repair procedures...")
            procedures = await self._extract_procedures(text, faults, filename)
            result.procedures = [asdict(p) for p in procedures]
            result.procedures_extracted = len(procedures)
            logger.info(f"✅ Found {len(procedures)} procedure(s)")

            # Step 5 — Add to Knowledge Graph
            logger.info("🕸️ Adding to Knowledge Graph...")
            nodes_added, edges_added = self._add_to_knowledge_graph(
                robots, faults, procedures
            )
            result.nodes_added = nodes_added
            result.edges_added = edges_added
            result.status = "completed"

            logger.info(f"🎉 Ingestion complete: {nodes_added} nodes, {edges_added} edges added")

        except Exception as e:
            logger.error(f"❌ Ingestion failed: {str(e)}")
            result.status = "failed"
            result.error = str(e)

        self.ingestion_history.append(result)
        return result

    def _extract_pdf_text(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF using pdfplumber."""
        try:
            import pdfplumber
            import io
            text_parts = []
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                total = len(pdf.pages)
                logger.info(f"PDF has {total} pages")
                # Extract first 80 pages max to avoid token limits
                for i, page in enumerate(pdf.pages[:80]):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(f"\n--- PAGE {i+1} ---\n{page_text}")
                    except Exception:
                        continue
            return "\n".join(text_parts)
        except ImportError:
            logger.warning("pdfplumber not installed — trying PyPDF2")
            return self._extract_pdf_text_pypdf2(pdf_bytes)
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            raise

    def _extract_pdf_text_pypdf2(self, pdf_bytes: bytes) -> str:
        """Fallback PDF extraction using PyPDF2."""
        try:
            import PyPDF2
            import io
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            parts = []
            for i, page in enumerate(reader.pages[:80]):
                try:
                    text = page.extract_text()
                    if text:
                        parts.append(f"\n--- PAGE {i+1} ---\n{text}")
                except Exception:
                    continue
            return "\n".join(parts)
        except Exception as e:
            raise Exception(f"Could not extract PDF text: {str(e)}")

    async def _extract_robots(
        self, text: str, filename: str
    ) -> List[ExtractedRobot]:
        """Extract robot model information from text."""

        # Take first 8000 chars — robot specs usually in introduction
        sample = text[:8000]

        prompt = f"""You are analyzing a robot technical manual to extract robot model information.

DOCUMENT: {filename}
TEXT SAMPLE:
{sample}

Extract the robot model information. Return ONLY a valid JSON array.
If multiple models are mentioned, include all of them.

JSON format:
[
  {{
    "name": "Full robot name",
    "manufacturer": "Company name",
    "model_number": "Model number/series",
    "robot_type": "Industrial robot / Collaborative robot / Welding robot etc.",
    "payload_kg": 10.0,
    "reach_mm": 1600,
    "axes": 6,
    "use_cases": ["welding", "assembly", "machine tending"],
    "description": "Brief description of this robot"
  }}
]

If you cannot find specific values, use null. Return ONLY the JSON array, no other text."""

        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You extract structured data from robot manuals. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )

            raw = response.choices[0].message.content.strip()
            raw = self._clean_json(raw)
            data = json.loads(raw)

            robots = []
            for item in data:
                robot_id = self._make_id(
                    item.get("manufacturer", "UNKNOWN"),
                    item.get("model_number", item.get("name", "ROBOT"))
                )
                robots.append(ExtractedRobot(
                    id=robot_id,
                    name=item.get("name", "Unknown Robot"),
                    manufacturer=item.get("manufacturer", "Unknown"),
                    model_number=item.get("model_number", ""),
                    robot_type=item.get("robot_type", "Industrial Robot"),
                    payload_kg=item.get("payload_kg"),
                    reach_mm=item.get("reach_mm"),
                    axes=item.get("axes"),
                    use_cases=item.get("use_cases", []),
                    description=item.get("description", ""),
                    source_document=filename
                ))
            return robots

        except Exception as e:
            logger.error(f"Robot extraction error: {str(e)}")
            # Fallback — try to detect from filename
            return self._fallback_robot_from_filename(filename)

    async def _extract_faults(
        self, text: str, robot_id: str, filename: str
    ) -> List[ExtractedFault]:
        """Extract fault codes from PDF text."""

        # Look for sections with error/fault/alarm codes
        fault_sections = self._find_fault_sections(text)

        if not fault_sections:
            # Use middle portion of document
            fault_sections = text[len(text)//4: len(text)//4 * 3][:12000]

        prompt = f"""You are analyzing a robot service manual to extract ALL fault/error/alarm codes.

DOCUMENT: {filename}
RELEVANT TEXT:
{fault_sections[:10000]}

Extract every fault code mentioned. Return ONLY a valid JSON array.

JSON format:
[
  {{
    "code": "E-001 or A.100 or SRVO-023 etc.",
    "name": "Short fault name",
    "severity": "LOW or MEDIUM or HIGH or CRITICAL",
    "description": "What this fault means",
    "symptoms": ["symptom 1", "symptom 2"],
    "causes": ["possible cause 1", "possible cause 2"]
  }}
]

Extract as many fault codes as you can find. Return ONLY the JSON array."""

        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You extract fault codes from robot manuals. Return only valid JSON arrays."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=3000
            )

            raw = response.choices[0].message.content.strip()
            raw = self._clean_json(raw)
            data = json.loads(raw)

            faults = []
            for item in data:
                code = item.get("code", "UNKNOWN")
                fault_id = f"{robot_id}_FAULT_{self._make_id('', code)}"
                faults.append(ExtractedFault(
                    id=fault_id,
                    robot_id=robot_id,
                    code=code,
                    name=item.get("name", f"Fault {code}"),
                    severity=item.get("severity", "MEDIUM"),
                    description=item.get("description", ""),
                    symptoms=item.get("symptoms", []),
                    causes=item.get("causes", []),
                    source_document=filename
                ))

            return faults[:50]  # Cap at 50 faults

        except Exception as e:
            logger.error(f"Fault extraction error: {str(e)}")
            return []

    async def _extract_procedures(
        self, text: str, faults: List[ExtractedFault], filename: str
    ) -> List[ExtractedProcedure]:
        """Extract repair procedures from PDF text."""

        # Look for maintenance/repair sections
        proc_section = self._find_procedure_sections(text)

        if not proc_section:
            proc_section = text[len(text)//2:][:10000]

        fault_codes = [f.code for f in faults[:10]]  # Top 10 faults

        prompt = f"""You are analyzing a robot service manual to extract repair procedures.

DOCUMENT: {filename}
KNOWN FAULT CODES: {fault_codes}
MAINTENANCE/REPAIR TEXT:
{proc_section[:8000]}

Extract repair/maintenance procedures. Return ONLY a valid JSON array.

JSON format:
[
  {{
    "name": "Procedure name",
    "applicable_fault_codes": ["E-001", "E-002"],
    "estimated_time_minutes": 30,
    "skill_level": "Operator or Technician or Engineer",
    "tools_required": ["tool 1", "tool 2"],
    "steps": [
      "Step 1: Do this first",
      "Step 2: Then do this"
    ],
    "warning": "Safety warning if any"
  }}
]

Return ONLY the JSON array."""

        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You extract repair procedures from robot manuals. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=3000
            )

            raw = response.choices[0].message.content.strip()
            raw = self._clean_json(raw)
            data = json.loads(raw)

            procedures = []
            for item in data:
                proc_id = f"PROC_{self._make_id('', item.get('name', 'PROC'))}"
                procedures.append(ExtractedProcedure(
                    id=proc_id,
                    name=item.get("name", "Maintenance Procedure"),
                    applicable_fault_codes=item.get("applicable_fault_codes", []),
                    estimated_time_minutes=item.get("estimated_time_minutes", 30),
                    skill_level=item.get("skill_level", "Technician"),
                    tools_required=item.get("tools_required", []),
                    steps=item.get("steps", []),
                    warning=item.get("warning", "Follow all safety procedures"),
                    source_document=filename
                ))

            return procedures[:20]  # Cap at 20 procedures

        except Exception as e:
            logger.error(f"Procedure extraction error: {str(e)}")
            return []

    def _add_to_knowledge_graph(
        self,
        robots,
        faults,
        procedures
    ):
        """Add extracted entities to KG with full deduplication."""
        from knowledge_graph import get_knowledge_graph
        kg = get_knowledge_graph()

        nodes_added = 0
        edges_added = 0

        def upsert_node(node_id, node_type, **attrs):
            """Add node if not exists, update if exists."""
            nonlocal nodes_added
            if node_id not in kg.graph.nodes:
                kg.graph.add_node(node_id, node_type=node_type, **attrs)
                nodes_added += 1
            else:
                # Update existing node with any new info
                for k, v in attrs.items():
                    if v and not kg.graph.nodes[node_id].get(k):
                        kg.graph.nodes[node_id][k] = v

        def upsert_edge(from_id, to_id, relationship):
            """Add edge only if it doesn't exist."""
            nonlocal edges_added
            if (from_id in kg.graph.nodes and
                to_id in kg.graph.nodes and
                not kg.graph.has_edge(from_id, to_id)):
                kg.graph.add_edge(from_id, to_id, relationship=relationship)
                edges_added += 1

        # Add robots
        for robot in robots:
            upsert_node(
                robot.id, "ROBOT",
                name=robot.name,
                manufacturer=robot.manufacturer,
                model_number=robot.model_number,
                type=robot.robot_type,
                payload_kg=robot.payload_kg,
                reach_mm=robot.reach_mm,
                axes=robot.axes,
                use_cases=robot.use_cases,
                description=robot.description,
                source_document=robot.source_document,
                auto_extracted=True
            )

        # Add faults
        for fault in faults:
            upsert_node(
                fault.id, "FAULT",
                code=fault.code,
                name=fault.name,
                severity=fault.severity,
                description=fault.description,
                symptoms=fault.symptoms,
                causes=fault.causes,
                source_document=fault.source_document,
                auto_extracted=True
            )
            if fault.robot_id in kg.graph.nodes:
                upsert_edge(fault.robot_id, fault.id, "CAN_FAIL_WITH")

            for cause_text in fault.causes:
                cause_id = f"CAUSE_{self._make_id('', cause_text)}"
                upsert_node(
                    cause_id, "CAUSE",
                    name=cause_text,
                    description=cause_text,
                    auto_extracted=True
                )
                upsert_edge(fault.id, cause_id, "CAUSED_BY")

        # Add procedures
        for proc in procedures:
            upsert_node(
                proc.id, "PROCEDURE",
                name=proc.name,
                estimated_time_minutes=proc.estimated_time_minutes,
                skill_level=proc.skill_level,
                tools_required=proc.tools_required,
                steps=proc.steps,
                warning=proc.warning,
                source_document=proc.source_document,
                auto_extracted=True
            )
            for fault_code in proc.applicable_fault_codes:
                for fault in faults:
                    if fault.code == fault_code:
                        upsert_edge(fault.id, proc.id, "FIXED_BY")
                        upsert_edge(proc.id, fault.id, "FIXES")

        logger.info(
            f"✅ KG updated (dedup): +{nodes_added} nodes, +{edges_added} edges"
        )
        return nodes_added, edges_added

    def _find_fault_sections(self, text: str) -> str:
        """Find sections of text related to faults/errors."""
        keywords = [
            "fault", "error", "alarm", "warning", "troubleshoot",
            "diagnostic", "E-0", "A.", "SRVO", "error code"
        ]
        lines = text.split("\n")
        relevant = []
        capture = False
        captured = 0

        for line in lines:
            line_lower = line.lower()
            if any(kw.lower() in line_lower for kw in keywords):
                capture = True
                captured = 0
            if capture:
                relevant.append(line)
                captured += 1
                if captured > 50:
                    capture = False

        result = "\n".join(relevant)
        return result[:12000] if result else ""

    def _find_procedure_sections(self, text: str) -> str:
        """Find maintenance/repair procedure sections."""
        keywords = [
            "maintenance", "repair", "replace", "procedure",
            "corrective", "service", "step", "inspection", "check"
        ]
        lines = text.split("\n")
        relevant = []
        capture = False
        captured = 0

        for line in lines:
            line_lower = line.lower()
            if any(kw.lower() in line_lower for kw in keywords):
                capture = True
                captured = 0
            if capture:
                relevant.append(line)
                captured += 1
                if captured > 80:
                    capture = False

        result = "\n".join(relevant)
        return result[:10000] if result else ""

    def _clean_json(self, raw: str) -> str:
        """Clean LLM output to get valid JSON."""
        raw = raw.strip()
        # Remove markdown code blocks
        raw = re.sub(r'```json\s*', '', raw)
        raw = re.sub(r'```\s*', '', raw)
        raw = raw.strip()
        # Find JSON array
        start = raw.find('[')
        end = raw.rfind(']')
        if start != -1 and end != -1:
            return raw[start:end+1]
        # Find JSON object
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1:
            return '[' + raw[start:end+1] + ']'
        return raw

    def _make_id(self, prefix: str, text: str) -> str:
        """Create a clean ID from text."""
        clean = re.sub(r'[^A-Z0-9_]', '_', text.upper())
        clean = re.sub(r'_+', '_', clean).strip('_')
        return f"{prefix}_{clean}" if prefix else clean

    def _fallback_robot_from_filename(
        self, filename: str
    ) -> List[ExtractedRobot]:
        """Create a basic robot entry from filename if extraction fails."""
        name = filename.replace(".pdf", "").replace("_", " ").replace("-", " ")
        robot_id = self._make_id("", name[:20])
        return [ExtractedRobot(
            id=robot_id,
            name=name,
            manufacturer="Unknown",
            model_number=name,
            robot_type="Industrial Robot",
            payload_kg=None,
            reach_mm=None,
            axes=None,
            use_cases=[],
            description=f"Extracted from {filename}",
            source_document=filename
        )]

    def get_ingestion_history(self) -> List[Dict]:
        """Get all ingestion history."""
        return [asdict(r) for r in self.ingestion_history]


# Global instance
_pipeline = None


def get_pdf_pipeline() -> PDFIngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = PDFIngestionPipeline()
        _pipeline.initialize()
    return _pipeline
