"""
PAIOS Knowledge Graph — Robot & Manufacturing Intelligence
==========================================================

WHAT IS A KNOWLEDGE GRAPH?
A knowledge graph stores ENTITIES and RELATIONSHIPS between them.
Unlike a database (stores rows/columns) or RAG (searches text),
a knowledge graph stores HOW things CONNECT to each other.

Example:
  ABB GoFa --[HAS_COMPONENT]--> Joint Motor
  Joint Motor --[CAN_FAIL_WITH]--> Error E-001
  Error E-001 --[CAUSED_BY]--> Motor Overload
  Motor Overload --[FIXED_BY]--> Procedure: Reduce Load

WHEN IS IT USED?
- When you need to understand RELATIONSHIPS between things
- When a simple text search is not enough
- When you need multi-hop reasoning:
  "What procedure fixes faults caused by overheating in ABB robots?"
  Graph: ABB → components → motors → fault: overheating → fix: procedure P-7

HOW WE BUILT IT?
- Language: Python
- Library: NetworkX (free, no server needed, runs locally)
- Storage: JSON file (robots_knowledge_graph.json)
- Query: Python functions that traverse the graph
- In production: would use Neo4j (enterprise graph database)

GRAPH STRUCTURE:
Nodes (Entities):
  - Robot models (ABB GoFa, KUKA LBR iisy, etc.)
  - Components (motors, sensors, controllers)
  - Fault codes (E-001, F-234, etc.)
  - Causes (overload, overheating, etc.)
  - Repair procedures (step-by-step fixes)
  - Manufacturers (ABB, KUKA, Yaskawa, etc.)

Edges (Relationships):
  - HAS_COMPONENT
  - CAN_FAIL_WITH
  - CAUSED_BY
  - FIXED_BY
  - MANUFACTURED_BY
  - SIMILAR_TO
  - REQUIRES_TOOL
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import networkx as nx

logger = logging.getLogger(__name__)


# ============================================================
# KNOWLEDGE BASE DATA — All robots, faults, procedures
# ============================================================

ROBOTS = [
    {
        "id": "ABB_GOFA",
        "name": "ABB GoFa (CRB 15000)",
        "manufacturer": "ABB Robotics",
        "type": "Collaborative Robot (Cobot)",
        "payload_kg": 5,
        "reach_mm": 950,
        "axes": 6,
        "ip_rating": "IP54",
        "use_cases": ["Assembly", "Machine tending", "Packaging", "Quality inspection"],
        "description": "ABB GoFa is a collaborative robot designed for safe human-robot collaboration with 5kg payload and 950mm reach."
    },
    {
        "id": "KUKA_LBR_IISY",
        "name": "KUKA LBR iisy",
        "manufacturer": "KUKA Robotics",
        "type": "Collaborative Robot (Cobot)",
        "payload_kg": 15,
        "reach_mm": 1100,
        "axes": 7,
        "ip_rating": "IP54",
        "use_cases": ["Screwdriving", "Assembly", "Testing", "Human collaboration"],
        "description": "KUKA LBR iisy is a sensitive collaborative robot with 7 axes and built-in force/torque sensing."
    },
    {
        "id": "YASKAWA_ARCWORLD",
        "name": "Yaskawa ArcWorld",
        "manufacturer": "Yaskawa Motoman",
        "type": "Industrial Welding Robot",
        "payload_kg": 20,
        "reach_mm": 1730,
        "axes": 6,
        "ip_rating": "IP67",
        "use_cases": ["Arc welding", "MIG welding", "TIG welding", "Plasma cutting"],
        "description": "Yaskawa ArcWorld is a complete arc welding system with Motoman robot and YRC1000 controller."
    },
    {
        "id": "UNIVERSAL_ROBOTS_UR10E",
        "name": "Universal Robots UR10e",
        "manufacturer": "Universal Robots",
        "type": "Collaborative Robot (Cobot)",
        "payload_kg": 12.5,
        "reach_mm": 1300,
        "axes": 6,
        "ip_rating": "IP54",
        "use_cases": ["Palletizing", "Assembly", "Machine tending", "Welding"],
        "description": "UR10e is a versatile e-Series cobot with built-in force/torque sensor and easy programming."
    },
    {
        "id": "FANUC_CRX",
        "name": "Fanuc CRX-10iA",
        "manufacturer": "Fanuc Corporation",
        "type": "Collaborative Robot (Cobot)",
        "payload_kg": 10,
        "reach_mm": 1249,
        "axes": 6,
        "ip_rating": "IP67",
        "use_cases": ["Welding", "Assembly", "Handling", "Inspection"],
        "description": "Fanuc CRX is a dust and drip-proof cobot with tablet-based programming and sensitive contact detection."
    }
]

COMPONENTS = [
    {"id": "JOINT_MOTOR", "name": "Joint Motor", "description": "Servo motor that drives each robot joint", "type": "actuator"},
    {"id": "FORCE_TORQUE_SENSOR", "name": "Force/Torque Sensor", "description": "Measures forces and torques for safe collaboration", "type": "sensor"},
    {"id": "CONTROLLER", "name": "Robot Controller", "description": "Main computer that controls robot motion", "type": "electronics"},
    {"id": "TEACH_PENDANT", "name": "Teach Pendant / SmartPad", "description": "Handheld device for programming and operating the robot", "type": "interface"},
    {"id": "ENCODER", "name": "Joint Encoder", "description": "Measures precise position of each joint", "type": "sensor"},
    {"id": "BRAKE", "name": "Joint Brake", "description": "Mechanical brake that holds joint position when power is off", "type": "mechanical"},
    {"id": "COOLING_FAN", "name": "Cooling Fan", "description": "Keeps controller and motors at safe temperature", "type": "thermal"},
    {"id": "POWER_SUPPLY", "name": "Power Supply Unit", "description": "Converts AC mains power to DC for robot systems", "type": "electronics"},
    {"id": "COMMUNICATION_BUS", "name": "EtherCAT Bus", "description": "Real-time communication between controller and joints", "type": "communication"},
    {"id": "GRIPPER", "name": "End Effector / Gripper", "description": "Tool at the end of robot arm for gripping objects", "type": "tool"},
    {"id": "SAFETY_SYSTEM", "name": "Safety Monitoring System", "description": "Monitors speed, force, and position for safe operation", "type": "safety"},
    {"id": "WELDING_TORCH", "name": "Welding Torch", "description": "High-temperature tool for arc welding applications", "type": "tool"}
]

FAULT_CODES = [
    # ABB GoFa faults
    {
        "id": "ABB_E001",
        "code": "E-001",
        "robot": "ABB_GOFA",
        "name": "Motor Overload",
        "severity": "HIGH",
        "description": "Joint motor is drawing excessive current, indicating mechanical overload or motor failure.",
        "symptoms": ["Robot stops suddenly", "Error light flashes red", "Motor gets hot", "Reduced speed before stop"],
        "causes": ["EXCESSIVE_LOAD", "MECHANICAL_OBSTRUCTION", "MOTOR_DEGRADATION"],
        "component": "JOINT_MOTOR"
    },
    {
        "id": "ABB_E002",
        "code": "E-002",
        "robot": "ABB_GOFA",
        "name": "Communication Loss",
        "severity": "HIGH",
        "description": "EtherCAT communication between controller and joint modules has been interrupted.",
        "symptoms": ["All joints stop", "Controller shows network error", "Teach pendant disconnects"],
        "causes": ["CABLE_DAMAGE", "CONNECTOR_LOOSE", "CONTROLLER_FAULT"],
        "component": "COMMUNICATION_BUS"
    },
    {
        "id": "ABB_E003",
        "code": "E-003",
        "robot": "ABB_GOFA",
        "name": "Force Limit Exceeded",
        "severity": "MEDIUM",
        "description": "Robot detected contact force exceeding safe collaboration limits.",
        "symptoms": ["Robot stops on contact", "Protective stop triggered", "Force monitoring alarm"],
        "causes": ["UNEXPECTED_COLLISION", "INCORRECT_FORCE_SETTINGS", "PATH_PLANNING_ERROR"],
        "component": "FORCE_TORQUE_SENSOR"
    },
    {
        "id": "ABB_E004",
        "code": "E-004",
        "robot": "ABB_GOFA",
        "name": "Encoder Error",
        "severity": "HIGH",
        "description": "Joint position encoder is reporting invalid or inconsistent position data.",
        "symptoms": ["Jerky movement", "Position error alarms", "Robot drifts from path"],
        "causes": ["ENCODER_FAILURE", "CABLE_DAMAGE", "INTERFERENCE"],
        "component": "ENCODER"
    },
    # KUKA faults
    {
        "id": "KUKA_F234",
        "code": "F-234",
        "robot": "KUKA_LBR_IISY",
        "name": "Axis Overload",
        "severity": "HIGH",
        "description": "Robot axis is experiencing torque beyond rated capacity.",
        "symptoms": ["Axis stops abruptly", "SmartPad shows F-234", "Vibration before fault"],
        "causes": ["EXCESSIVE_LOAD", "SPEED_TOO_HIGH", "MECHANICAL_OBSTRUCTION"],
        "component": "JOINT_MOTOR"
    },
    {
        "id": "KUKA_F512",
        "code": "F-512",
        "robot": "KUKA_LBR_IISY",
        "name": "Safety Monitoring Fault",
        "severity": "CRITICAL",
        "description": "Safety monitoring system has detected a violation of safe operating parameters.",
        "symptoms": ["Emergency stop", "Safety LED red", "All motion suspended"],
        "causes": ["SAFETY_ZONE_VIOLATION", "SPEED_LIMIT_EXCEEDED", "SAFETY_SYSTEM_FAULT"],
        "component": "SAFETY_SYSTEM"
    },
    {
        "id": "KUKA_F089",
        "code": "F-089",
        "robot": "KUKA_LBR_IISY",
        "name": "Controller Temperature High",
        "severity": "MEDIUM",
        "description": "Robot controller internal temperature has exceeded safe operating threshold.",
        "symptoms": ["Performance reduced", "Temperature warning on SmartPad", "Fan noise increases"],
        "causes": ["COOLING_FAILURE", "AMBIENT_TEMP_HIGH", "BLOCKED_VENTILATION"],
        "component": "COOLING_FAN"
    },
    # Yaskawa faults
    {
        "id": "YASKAWA_A100",
        "code": "A.100",
        "robot": "YASKAWA_ARCWORLD",
        "name": "Overcurrent Detection",
        "severity": "HIGH",
        "description": "Servo drive detected overcurrent condition in welding robot axis.",
        "symptoms": ["Welding stops", "Alarm A.100 on YRC1000", "Servo drive LED red"],
        "causes": ["EXCESSIVE_LOAD", "SHORT_CIRCUIT", "DRIVE_FAILURE"],
        "component": "JOINT_MOTOR"
    },
    {
        "id": "YASKAWA_A900",
        "code": "A.900",
        "robot": "YASKAWA_ARCWORLD",
        "name": "Welding Wire Feed Error",
        "severity": "MEDIUM",
        "description": "Wire feeder is not delivering welding wire at the correct rate.",
        "symptoms": ["Poor weld quality", "Wire bird-nesting", "Arc instability"],
        "causes": ["WIRE_FEED_MOTOR_FAULT", "WIRE_TANGLE", "LINER_BLOCKAGE"],
        "component": "WELDING_TORCH"
    },
    # Universal Robots faults
    {
        "id": "UR_C00_PROTECTIVE_STOP",
        "code": "C00-Protective Stop",
        "robot": "UNIVERSAL_ROBOTS_UR10E",
        "name": "Protective Stop",
        "severity": "MEDIUM",
        "description": "Robot has entered protective stop due to safety system trigger.",
        "symptoms": ["Robot freezes mid-motion", "Teach pendant shows protective stop", "Safety output deactivated"],
        "causes": ["SAFETY_INPUT_TRIGGERED", "JOINT_LIMIT_REACHED", "FORCE_LIMIT_EXCEEDED"],
        "component": "SAFETY_SYSTEM"
    },
    {
        "id": "UR_JOINT_ERROR",
        "code": "Joint Position Error",
        "robot": "UNIVERSAL_ROBOTS_UR10E",
        "name": "Joint Position Error",
        "severity": "HIGH",
        "description": "Difference between commanded and actual joint position exceeds threshold.",
        "symptoms": ["Robot stops", "Joint position error on teach pendant", "Path deviation"],
        "causes": ["MECHANICAL_OBSTRUCTION", "ENCODER_FAILURE", "BRAKE_ISSUE"],
        "component": "ENCODER"
    },
    # Fanuc faults
    {
        "id": "FANUC_SRVO_023",
        "code": "SRVO-023",
        "robot": "FANUC_CRX",
        "name": "Stop Error Excess",
        "severity": "HIGH",
        "description": "Robot position error exceeds the stop error limit during motion.",
        "symptoms": ["Robot stops abruptly", "SRVO-023 on pendant", "Alarm state"],
        "causes": ["MECHANICAL_OBSTRUCTION", "BRAKE_FAILURE", "SERVO_FAULT"],
        "component": "BRAKE"
    },
    {
        "id": "FANUC_SRVO_001",
        "code": "SRVO-001",
        "robot": "FANUC_CRX",
        "name": "Operator Panel E-Stop",
        "severity": "LOW",
        "description": "Emergency stop button on operator panel has been pressed.",
        "symptoms": ["All motion stops", "SRVO-001 displayed", "E-stop button lit"],
        "causes": ["MANUAL_ESTOP", "SAFETY_TRIGGER"],
        "component": "SAFETY_SYSTEM"
    }
]

CAUSES = [
    {"id": "EXCESSIVE_LOAD", "name": "Excessive Load", "description": "Robot is carrying or pushing more weight than rated capacity"},
    {"id": "MECHANICAL_OBSTRUCTION", "name": "Mechanical Obstruction", "description": "Physical object blocking robot motion path"},
    {"id": "MOTOR_DEGRADATION", "name": "Motor Degradation", "description": "Motor windings or bearings have worn over time"},
    {"id": "CABLE_DAMAGE", "name": "Cable Damage", "description": "Communication or power cables are damaged or frayed"},
    {"id": "CONNECTOR_LOOSE", "name": "Loose Connector", "description": "Electrical connector has become disconnected or intermittent"},
    {"id": "CONTROLLER_FAULT", "name": "Controller Fault", "description": "Main controller hardware or software has failed"},
    {"id": "UNEXPECTED_COLLISION", "name": "Unexpected Collision", "description": "Robot contacted an unexpected object"},
    {"id": "INCORRECT_FORCE_SETTINGS", "name": "Incorrect Force Settings", "description": "Force/torque thresholds configured incorrectly"},
    {"id": "PATH_PLANNING_ERROR", "name": "Path Planning Error", "description": "Robot path brings it into contact with objects"},
    {"id": "ENCODER_FAILURE", "name": "Encoder Failure", "description": "Position encoder hardware has failed"},
    {"id": "INTERFERENCE", "name": "Electrical Interference", "description": "EMI or electrical noise corrupting signals"},
    {"id": "COOLING_FAILURE", "name": "Cooling Failure", "description": "Cooling fan or thermal management has failed"},
    {"id": "AMBIENT_TEMP_HIGH", "name": "High Ambient Temperature", "description": "Operating environment is too hot"},
    {"id": "BLOCKED_VENTILATION", "name": "Blocked Ventilation", "description": "Airflow to controller or motor is obstructed"},
    {"id": "SAFETY_ZONE_VIOLATION", "name": "Safety Zone Violation", "description": "Robot entered a restricted safety zone"},
    {"id": "SPEED_LIMIT_EXCEEDED", "name": "Speed Limit Exceeded", "description": "Robot moving faster than safety system allows"},
    {"id": "SAFETY_SYSTEM_FAULT", "name": "Safety System Fault", "description": "Safety monitoring hardware or software error"},
    {"id": "SHORT_CIRCUIT", "name": "Short Circuit", "description": "Electrical short in motor or drive circuitry"},
    {"id": "DRIVE_FAILURE", "name": "Drive Failure", "description": "Servo drive unit has malfunctioned"},
    {"id": "WIRE_FEED_MOTOR_FAULT", "name": "Wire Feed Motor Fault", "description": "Motor driving wire feeder has failed"},
    {"id": "WIRE_TANGLE", "name": "Wire Tangle", "description": "Welding wire has tangled in the spool or liner"},
    {"id": "LINER_BLOCKAGE", "name": "Liner Blockage", "description": "Wire guide liner is clogged with debris"},
    {"id": "SAFETY_INPUT_TRIGGERED", "name": "Safety Input Triggered", "description": "External safety device (light curtain, scanner) triggered"},
    {"id": "JOINT_LIMIT_REACHED", "name": "Joint Limit Reached", "description": "Robot joint reached its mechanical or software limit"},
    {"id": "BRAKE_ISSUE", "name": "Brake Issue", "description": "Joint brake is not releasing or engaging properly"},
    {"id": "BRAKE_FAILURE", "name": "Brake Failure", "description": "Joint brake has failed mechanically"},
    {"id": "SERVO_FAULT", "name": "Servo Fault", "description": "Servo amplifier or motor fault detected"},
    {"id": "SPEED_TOO_HIGH", "name": "Speed Too High", "description": "Programmed speed exceeds safe limit for payload"},
    {"id": "MANUAL_ESTOP", "name": "Manual E-Stop", "description": "Operator pressed emergency stop button"},
    {"id": "SAFETY_TRIGGER", "name": "Safety Trigger", "description": "Automatic safety system triggered e-stop"},
    {"id": "FORCE_LIMIT_EXCEEDED", "name": "Force Limit Exceeded", "description": "Contact force exceeded collaborative safety limit"},
]

REPAIR_PROCEDURES = [
    {
        "id": "PROC_MOTOR_OVERLOAD",
        "name": "Motor Overload Resolution",
        "applicable_faults": ["ABB_E001", "KUKA_F234", "YASKAWA_A100"],
        "estimated_time_minutes": 30,
        "skill_level": "Technician",
        "tools_required": ["Multimeter", "Torque wrench", "Service laptop"],
        "steps": [
            "1. SAFETY FIRST: Press emergency stop and lock out/tag out power",
            "2. Check payload: Verify robot is not carrying more than rated capacity",
            "3. Check for obstruction: Manually move each joint to feel for resistance",
            "4. Measure motor current: Use multimeter to check motor draw at each joint",
            "5. Check motor temperature: Allow 30 minutes to cool if overheated",
            "6. Inspect mechanical components: Look for damaged bearings or gears",
            "7. Reset fault: Clear error code from controller interface",
            "8. Test run: Run slow speed test cycle to verify resolution",
            "9. If fault recurs: Escalate to motor replacement procedure"
        ],
        "warning": "Never bypass overload protection. It exists to prevent fire and injury."
    },
    {
        "id": "PROC_COMMS_LOSS",
        "name": "Communication Loss Recovery",
        "applicable_faults": ["ABB_E002"],
        "estimated_time_minutes": 20,
        "skill_level": "Technician",
        "tools_required": ["Cable tester", "Compressed air", "Screwdriver set"],
        "steps": [
            "1. SAFETY FIRST: Power down robot safely using proper shutdown sequence",
            "2. Inspect all cable connections from controller to robot arm",
            "3. Check EtherCAT cable connectors for corrosion or damage",
            "4. Reseat all connectors firmly — common cause of intermittent faults",
            "5. Use cable tester to verify continuity on all communication cables",
            "6. Clean connectors with compressed air if dirt is present",
            "7. Power on controller and check for fault codes",
            "8. Test communication: Verify all joints respond to controller",
            "9. Run diagnostic cycle to confirm all axes communicate correctly"
        ],
        "warning": "Label all cables before disconnecting to avoid wrong reconnection."
    },
    {
        "id": "PROC_FORCE_LIMIT",
        "name": "Force Limit Fault Resolution",
        "applicable_faults": ["ABB_E003", "UR_C00_PROTECTIVE_STOP"],
        "estimated_time_minutes": 15,
        "skill_level": "Operator",
        "tools_required": ["Teach pendant", "Service manual"],
        "steps": [
            "1. Identify what the robot contacted — remove any unexpected objects",
            "2. Check force/torque settings in controller configuration",
            "3. Verify collaborative safety zones are correctly defined",
            "4. Review robot path for any points that could cause unintended contact",
            "5. Adjust force limits if they are too sensitive for the application",
            "6. Clear the fault code from the teach pendant",
            "7. Run the program slowly to verify no contact occurs",
            "8. Document the incident for safety review"
        ],
        "warning": "Do not simply increase force limits without understanding the root cause."
    },
    {
        "id": "PROC_ENCODER_ERROR",
        "name": "Encoder Error Diagnosis",
        "applicable_faults": ["ABB_E004", "UR_JOINT_ERROR"],
        "estimated_time_minutes": 60,
        "skill_level": "Engineer",
        "tools_required": ["Oscilloscope", "Encoder tester", "Service laptop", "Replacement encoder"],
        "steps": [
            "1. SAFETY: Full lockout/tagout — encoder faults can cause unpredictable motion",
            "2. Identify which joint has the encoder fault from error code",
            "3. Connect service laptop and read encoder diagnostic data",
            "4. Check encoder cable for damage, especially at joint flex points",
            "5. Measure encoder signal quality with oscilloscope",
            "6. If signal degraded, replace encoder cable first (cheaper fix)",
            "7. If cable is fine, replace encoder unit on affected joint",
            "8. Recalibrate joint position after encoder replacement",
            "9. Run full motion test to verify calibration is correct"
        ],
        "warning": "Incorrect encoder calibration can cause violent unexpected motion. Always test at slow speed first."
    },
    {
        "id": "PROC_KUKA_SAFETY",
        "name": "KUKA Safety Monitoring Recovery",
        "applicable_faults": ["KUKA_F512"],
        "estimated_time_minutes": 45,
        "skill_level": "Engineer",
        "tools_required": ["KUKA SmartPad", "Safety configuration software", "Multimeter"],
        "steps": [
            "1. Do NOT clear fault until root cause is identified",
            "2. Read full error log on SmartPad for details",
            "3. Check safety zone definitions in KUKA SafeOperation configuration",
            "4. Verify all safety inputs (light curtains, scanners) are functioning",
            "5. Test each safety device individually",
            "6. Check robot speed and force limits vs. safety configuration",
            "7. If safety hardware fault: replace affected safety device",
            "8. Recertify safety configuration after any changes",
            "9. Document all changes for compliance records"
        ],
        "warning": "Safety system changes require certified safety engineer sign-off in most jurisdictions."
    },
    {
        "id": "PROC_COOLING",
        "name": "Overtemperature Resolution",
        "applicable_faults": ["KUKA_F089"],
        "estimated_time_minutes": 25,
        "skill_level": "Technician",
        "tools_required": ["Thermometer", "Compressed air", "Replacement fan"],
        "steps": [
            "1. Power down robot and allow 30 minutes to cool",
            "2. Check ambient temperature — must be within robot spec (usually 0-45°C)",
            "3. Inspect cooling fan on controller — verify it is spinning",
            "4. Clean dust filters with compressed air",
            "5. Check ventilation around controller — 200mm clearance required",
            "6. If fan not spinning: replace cooling fan",
            "7. Monitor temperature after restart to confirm resolution",
            "8. Consider adding air conditioning if ambient temp is the issue"
        ],
        "warning": "Operating at high temperature reduces component life significantly."
    },
    {
        "id": "PROC_YASKAWA_WELDING",
        "name": "Wire Feed Error Resolution",
        "applicable_faults": ["YASKAWA_A900"],
        "estimated_time_minutes": 20,
        "skill_level": "Operator",
        "tools_required": ["Wire cutters", "Liner cleaning kit", "Replacement liner"],
        "steps": [
            "1. Stop welding and release wire pressure",
            "2. Check wire spool for tangles or birds-nesting",
            "3. Cut back any damaged wire section",
            "4. Inspect wire liner for blockages or kinks",
            "5. Blow out liner with compressed air",
            "6. If liner is damaged or heavily worn, replace it",
            "7. Re-thread welding wire through system",
            "8. Test wire feed at low speed before resuming production"
        ],
        "warning": "Welding wire can be sharp. Wear cut-resistant gloves."
    },
    {
        "id": "PROC_FANUC_SRVO023",
        "name": "Fanuc SRVO-023 Stop Error Resolution",
        "applicable_faults": ["FANUC_SRVO_023"],
        "estimated_time_minutes": 40,
        "skill_level": "Technician",
        "tools_required": ["Fanuc teach pendant", "Service manual", "Torque wrench"],
        "steps": [
            "1. Press E-stop if not already stopped",
            "2. Read full alarm history from Fanuc pendant (MENU > ALARM > HISTORY)",
            "3. Identify which axis triggered SRVO-023",
            "4. Check for mechanical obstruction on that axis",
            "5. Verify brake is releasing: Listen for click when servo enabled",
            "6. Check servo amplifier status LEDs",
            "7. Review position error parameters — may need tuning if load changed",
            "8. Clear alarm and jog axis slowly to verify smooth motion",
            "9. If brake suspected: test brake circuit continuity"
        ],
        "warning": "Do not increase position error tolerance without understanding why the error is occurring."
    },
    {
        "id": "PROC_ESTOP_RESET",
        "name": "Emergency Stop Reset Procedure",
        "applicable_faults": ["FANUC_SRVO_001"],
        "estimated_time_minutes": 5,
        "skill_level": "Operator",
        "tools_required": ["None"],
        "steps": [
            "1. Identify why e-stop was pressed — verify area is safe",
            "2. Ensure all personnel are clear of robot work envelope",
            "3. Twist and release the e-stop button to unlock it",
            "4. Press FAULT RESET on teach pendant",
            "5. Verify no other faults are present",
            "6. Resume automatic operation following standard startup procedure"
        ],
        "warning": "Never reset e-stop without verifying the cause and ensuring safety."
    }
]

ROBOT_COMPONENTS_MAP = {
    "ABB_GOFA": ["JOINT_MOTOR", "FORCE_TORQUE_SENSOR", "CONTROLLER", "TEACH_PENDANT", "ENCODER", "BRAKE", "COOLING_FAN", "POWER_SUPPLY", "COMMUNICATION_BUS", "SAFETY_SYSTEM"],
    "KUKA_LBR_IISY": ["JOINT_MOTOR", "FORCE_TORQUE_SENSOR", "CONTROLLER", "TEACH_PENDANT", "ENCODER", "BRAKE", "COOLING_FAN", "POWER_SUPPLY", "COMMUNICATION_BUS", "SAFETY_SYSTEM"],
    "YASKAWA_ARCWORLD": ["JOINT_MOTOR", "CONTROLLER", "TEACH_PENDANT", "ENCODER", "BRAKE", "COOLING_FAN", "POWER_SUPPLY", "COMMUNICATION_BUS", "WELDING_TORCH", "SAFETY_SYSTEM"],
    "UNIVERSAL_ROBOTS_UR10E": ["JOINT_MOTOR", "FORCE_TORQUE_SENSOR", "CONTROLLER", "TEACH_PENDANT", "ENCODER", "BRAKE", "POWER_SUPPLY", "COMMUNICATION_BUS", "SAFETY_SYSTEM"],
    "FANUC_CRX": ["JOINT_MOTOR", "CONTROLLER", "TEACH_PENDANT", "ENCODER", "BRAKE", "COOLING_FAN", "POWER_SUPPLY", "COMMUNICATION_BUS", "SAFETY_SYSTEM"]
}

SIMILAR_ROBOTS = [
    ("ABB_GOFA", "KUKA_LBR_IISY", "Both 6-axis cobots with similar payload and safety features"),
    ("ABB_GOFA", "UNIVERSAL_ROBOTS_UR10E", "Both cobots used in assembly and machine tending"),
    ("KUKA_LBR_IISY", "UNIVERSAL_ROBOTS_UR10E", "Both collaborative robots with force sensing"),
    ("FANUC_CRX", "UNIVERSAL_ROBOTS_UR10E", "Both cobots with tablet-style programming interface"),
]


class PAIOSKnowledgeGraph:
    """
    PAIOS Knowledge Graph for Robot Fault Diagnosis.
    
    Built with NetworkX — a Python graph library.
    Stores robots, components, faults, causes, and procedures
    as nodes, with relationships as edges.
    """

    def __init__(self):
        self.graph = nx.DiGraph()  # Directed graph (edges have direction)
        self._built = False
        logger.info("PAIOS Knowledge Graph initialized")

    def build(self):
        """Build the complete knowledge graph from data."""
        logger.info("🔨 Building PAIOS Knowledge Graph...")

        self._add_robots()
        self._add_components()
        self._add_faults()
        self._add_causes()
        self._add_procedures()
        self._add_relationships()

        self._built = True
        logger.info(f"✅ Knowledge Graph built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")

    def _add_robots(self):
        for robot in ROBOTS:
            node_data = {**robot, "node_type": "ROBOT"}
            self.graph.add_node(robot["id"], **node_data)

    def _add_components(self):
        for comp in COMPONENTS:
            node_data = {**comp, "node_type": "COMPONENT"}
            self.graph.add_node(comp["id"], **node_data)

    def _add_faults(self):
        for fault in FAULT_CODES:
            node_data = {**fault, "node_type": "FAULT"}
            self.graph.add_node(fault["id"], **node_data)

    def _add_causes(self):
        for cause in CAUSES:
            node_data = {**cause, "node_type": "CAUSE"}
            self.graph.add_node(cause["id"], **node_data)

    def _add_procedures(self):
        for proc in REPAIR_PROCEDURES:
            node_data = {**proc, "node_type": "PROCEDURE"}
            self.graph.add_node(proc["id"], **node_data)

    def _add_relationships(self):
        # Robot HAS_COMPONENT relationships
        for robot_id, components in ROBOT_COMPONENTS_MAP.items():
            for comp_id in components:
                self.graph.add_edge(robot_id, comp_id, relationship="HAS_COMPONENT")

        # Robot CAN_FAIL_WITH fault relationships
        for fault in FAULT_CODES:
            self.graph.add_edge(fault["robot"], fault["id"], relationship="CAN_FAIL_WITH")
            # Fault AFFECTS component
            if "component" in fault:
                self.graph.add_edge(fault["id"], fault["component"], relationship="AFFECTS_COMPONENT")

        # Fault CAUSED_BY cause relationships
        for fault in FAULT_CODES:
            for cause_id in fault.get("causes", []):
                self.graph.add_edge(fault["id"], cause_id, relationship="CAUSED_BY")

        # Procedure FIXES fault relationships
        for proc in REPAIR_PROCEDURES:
            for fault_id in proc["applicable_faults"]:
                self.graph.add_edge(proc["id"], fault_id, relationship="FIXES")
                self.graph.add_edge(fault_id, proc["id"], relationship="FIXED_BY")

        # Similar robot relationships
        for robot1, robot2, reason in SIMILAR_ROBOTS:
            self.graph.add_edge(robot1, robot2, relationship="SIMILAR_TO", reason=reason)
            self.graph.add_edge(robot2, robot1, relationship="SIMILAR_TO", reason=reason)

    # ============================================================
    # QUERY FUNCTIONS — Ask the graph questions
    # ============================================================

    def get_robot_info(self, robot_id: str) -> Optional[Dict]:
        """Get full info about a robot."""
        if robot_id in self.graph.nodes:
            return dict(self.graph.nodes[robot_id])
        return None

    def get_robot_faults(self, robot_id: str) -> List[Dict]:
        """Get all possible faults for a robot."""
        faults = []
        for neighbor in self.graph.successors(robot_id):
            edge_data = self.graph.edges[robot_id, neighbor]
            if edge_data.get("relationship") == "CAN_FAIL_WITH":
                fault_data = dict(self.graph.nodes[neighbor])
                faults.append(fault_data)
        return faults

    def get_fault_procedures(self, fault_id: str) -> List[Dict]:
        """Get repair procedures for a fault."""
        procedures = []
        for neighbor in self.graph.successors(fault_id):
            edge_data = self.graph.edges[fault_id, neighbor]
            if edge_data.get("relationship") == "FIXED_BY":
                proc_data = dict(self.graph.nodes[neighbor])
                procedures.append(proc_data)
        return procedures

    def get_fault_causes(self, fault_id: str) -> List[Dict]:
        """Get causes of a fault."""
        causes = []
        for neighbor in self.graph.successors(fault_id):
            edge_data = self.graph.edges[fault_id, neighbor]
            if edge_data.get("relationship") == "CAUSED_BY":
                cause_data = dict(self.graph.nodes[neighbor])
                causes.append(cause_data)
        return causes

    def get_similar_robots(self, robot_id: str) -> List[Dict]:
        """Get robots similar to the given robot."""
        similar = []
        for neighbor in self.graph.successors(robot_id):
            edge_data = self.graph.edges[robot_id, neighbor]
            if edge_data.get("relationship") == "SIMILAR_TO":
                robot_data = dict(self.graph.nodes[neighbor])
                robot_data["similarity_reason"] = edge_data.get("reason", "")
                similar.append(robot_data)
        return similar

    def diagnose_fault(self, robot_id: str, fault_code: str) -> Dict[str, Any]:
        """
        Full diagnosis for a robot fault.
        Returns: robot info, fault details, causes, and repair procedures.
        This is the main function called by the chatbot.
        """
        result = {
            "robot": None,
            "fault": None,
            "causes": [],
            "procedures": [],
            "similar_robot_fixes": [],
            "components_affected": []
        }

        # Get robot info
        result["robot"] = self.get_robot_info(robot_id)

        # Find matching fault
        for fault in FAULT_CODES:
            if (fault["robot"] == robot_id and
                (fault["code"].upper() == fault_code.upper() or
                 fault_code.upper() in fault["name"].upper() or
                 fault["id"] == fault_code)):

                result["fault"] = fault

                # Get causes
                result["causes"] = self.get_fault_causes(fault["id"])

                # Get procedures
                result["procedures"] = self.get_fault_procedures(fault["id"])

                # Get affected component
                if "component" in fault:
                    comp = self.get_robot_info(fault["component"])
                    if comp:
                        result["components_affected"].append(comp)

                # Check if similar robots have same fault type
                similar_robots = self.get_similar_robots(robot_id)
                for sim_robot in similar_robots:
                    sim_faults = self.get_robot_faults(sim_robot["id"])
                    for sf in sim_faults:
                        if sf.get("name") == fault.get("name"):
                            sim_procs = self.get_fault_procedures(sf["id"])
                            if sim_procs:
                                result["similar_robot_fixes"].append({
                                    "robot": sim_robot["name"],
                                    "fault": sf,
                                    "procedures": sim_procs
                                })
                break

        return result

    def search_faults_by_symptom(self, symptom_text: str) -> List[Dict]:
        """Search faults by symptom description."""
        symptom_lower = symptom_text.lower()
        matching_faults = []

        for fault in FAULT_CODES:
            # Check symptoms list
            for symptom in fault.get("symptoms", []):
                if symptom_lower in symptom.lower():
                    matching_faults.append(fault)
                    break
            # Check description
            if symptom_lower in fault.get("description", "").lower():
                if fault not in matching_faults:
                    matching_faults.append(fault)
            # Check name
            if symptom_lower in fault.get("name", "").lower():
                if fault not in matching_faults:
                    matching_faults.append(fault)

        return matching_faults

    def get_all_robots(self) -> List[Dict]:
        """Get all robots in the knowledge graph."""
        return [dict(self.graph.nodes[n]) for n in self.graph.nodes
                if self.graph.nodes[n].get("node_type") == "ROBOT"]

    def get_graph_stats(self) -> Dict:
        """Get statistics about the knowledge graph."""
        node_types = {}
        for node in self.graph.nodes:
            ntype = self.graph.nodes[node].get("node_type", "UNKNOWN")
            node_types[ntype] = node_types.get(ntype, 0) + 1

        edge_types = {}
        for u, v, data in self.graph.edges(data=True):
            rel = data.get("relationship", "UNKNOWN")
            edge_types[rel] = edge_types.get(rel, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": node_types,
            "edge_types": edge_types,
            "robots": len([n for n in self.graph.nodes if self.graph.nodes[n].get("node_type") == "ROBOT"]),
            "fault_codes": len([n for n in self.graph.nodes if self.graph.nodes[n].get("node_type") == "FAULT"]),
            "repair_procedures": len([n for n in self.graph.nodes if self.graph.nodes[n].get("node_type") == "PROCEDURE"]),
            "components": len([n for n in self.graph.nodes if self.graph.nodes[n].get("node_type") == "COMPONENT"])
        }

    def format_diagnosis_for_llm(self, diagnosis: Dict) -> str:
        """
        Format diagnosis result as text for LLM context.
        This is what gets sent to Groq LLaMA 3.
        """
        if not diagnosis["fault"]:
            return "No matching fault found in knowledge graph."

        robot = diagnosis["robot"]
        fault = diagnosis["fault"]
        text = f"""
KNOWLEDGE GRAPH DIAGNOSIS RESULT:

ROBOT: {robot.get('name', 'Unknown')}
Manufacturer: {robot.get('manufacturer', 'Unknown')}
Type: {robot.get('type', 'Unknown')}
Payload: {robot.get('payload_kg', 'Unknown')} kg

FAULT DETECTED:
Code: {fault.get('code', 'Unknown')}
Name: {fault.get('name', 'Unknown')}
Severity: {fault.get('severity', 'Unknown')}
Description: {fault.get('description', 'Unknown')}
Symptoms: {', '.join(fault.get('symptoms', []))}

ROOT CAUSES:
"""
        for i, cause in enumerate(diagnosis["causes"], 1):
            text += f"{i}. {cause.get('name', '')}: {cause.get('description', '')}\n"

        if diagnosis["procedures"]:
            proc = diagnosis["procedures"][0]
            text += f"""
REPAIR PROCEDURE: {proc.get('name', '')}
Estimated Time: {proc.get('estimated_time_minutes', 0)} minutes
Skill Level Required: {proc.get('skill_level', 'Unknown')}
Tools Required: {', '.join(proc.get('tools_required', []))}
WARNING: {proc.get('warning', '')}

STEP-BY-STEP REPAIR STEPS:
"""
            for step in proc.get("steps", []):
                text += f"{step}\n"

        if diagnosis["components_affected"]:
            comp = diagnosis["components_affected"][0]
            text += f"\nAFFECTED COMPONENT: {comp.get('name', '')}: {comp.get('description', '')}\n"

        return text


# Global instance
_knowledge_graph = None


def get_knowledge_graph() -> PAIOSKnowledgeGraph:
    """Get or build the global knowledge graph instance."""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = PAIOSKnowledgeGraph()
        _knowledge_graph.build()
    return _knowledge_graph
