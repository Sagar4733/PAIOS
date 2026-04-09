import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, Chip, CircularProgress, Tooltip } from '@mui/material';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import FactoryIcon from '@mui/icons-material/Factory';
import PrecisionManufacturingIcon from '@mui/icons-material/PrecisionManufacturing';
import BugReportIcon from '@mui/icons-material/BugReport';
import BuildIcon from '@mui/icons-material/Build';
import MemoryIcon from '@mui/icons-material/Memory';
import TimelineIcon from '@mui/icons-material/Timeline';

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
const getToken = () => localStorage.getItem('access_token');

const SEVERITY_COLORS: Record<string, string> = {
  LOW: '#10b981',
  MEDIUM: '#f59e0b',
  HIGH: '#ef4444',
  CRITICAL: '#7c3aed',
  UNKNOWN: '#6b7280',
};

/* ── Colors per node type ── */
const NODE_STYLE: Record<string, { fill: string; stroke: string; text: string; icon: string }> = {
  FACTORY:         { fill: '#0c4a6e', stroke: '#06b6d4', text: '#e0f2fe', icon: '🏭' },
  PLANT:           { fill: '#1e3a5f', stroke: '#3b82f6', text: '#bfdbfe', icon: '🏢' },
  PRODUCTION_LINE: { fill: '#1a1a3e', stroke: '#8b5cf6', text: '#ddd6fe', icon: '⚙️' },
  MACHINE:         { fill: '#1a2e1a', stroke: '#10b981', text: '#d1fae5', icon: '🤖' },
  ROBOT:           { fill: '#1a2e1a', stroke: '#10b981', text: '#d1fae5', icon: '🤖' },
  COMPONENT:       { fill: '#2d1a1a', stroke: '#f59e0b', text: '#fef3c7', icon: '🔩' },
  FAULT:           { fill: '#2d1a1a', stroke: '#ef4444', text: '#fee2e2', icon: '⚠️' },
  PROCEDURE:       { fill: '#1a2d1a', stroke: '#10b981', text: '#d1fae5', icon: '🔧' },
  CAUSE:           { fill: '#2d2d1a', stroke: '#f59e0b', text: '#fef3c7', icon: '🔍' },
  DEFAULT:         { fill: '#1a1a2e', stroke: '#475569', text: '#cbd5e1', icon: '●' },
};

interface GraphNode {
  id: string;
  label: string;
  type: string;
  x: number;
  y: number;
  children: string[];
  data: any;
}

interface EKGTreeProps {
  selectedRobot?: string;
  height?: number;
}

const EKGTree: React.FC<EKGTreeProps> = ({ selectedRobot, height = 500 }) => {
  const [nodes,     setNodes]     = useState<GraphNode[]>([]);
  const [edges,     setEdges]     = useState<{ from: string; to: string; label: string }[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [selected,  setSelected]  = useState<GraphNode | null>(null);
  const [viewMode,  setViewMode]  = useState<'ekg' | 'robot'>('robot');
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const [dragging,  setDragging]  = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);

  const W = 900;

  useEffect(() => { loadGraph(); }, [selectedRobot, viewMode]);

  const loadGraph = async () => {
    setLoading(true);
    try {
      const token = getToken();
      const headers = { Authorization: `Bearer ${token || ''}` };

      if (viewMode === 'ekg') {
        // Load EKG factory hierarchy
        const res = await fetch(`${API_BASE}/api/ekg/hierarchy`, { headers });
        const data = await res.json();
        if (data.success && data.factories?.length > 0) {
          buildEKGLayout(data.factories);
        } else {
          buildDefaultEKGLayout();
        }
      } else {
        // Load robot knowledge graph
        const robotId = selectedRobot || 'ABB_GOFA';
        const res = await fetch(`${API_BASE}/api/knowledge-graph/robots/${robotId}`, { headers });
        const data = await res.json();
        if (data.success) {
          buildRobotLayout(data.robot, data.faults, data.similar_robots || []);
        }
      }
    } catch {
      buildDefaultEKGLayout();
    } finally {
      setLoading(false);
    }
  };

  /* ── Build robot-centric graph layout ── */
  const buildRobotLayout = (robot: any, faults: any[], similar: any[]) => {
    const newNodes: GraphNode[] = [];
    const newEdges: { from: string; to: string; label: string }[] = [];

    const cx = W / 2;
    const cy = 180;

    // Central robot node
    newNodes.push({
      id: robot.id, label: robot.name?.split('(')[0]?.trim() || robot.id,
      type: 'ROBOT', x: cx, y: cy, children: [], data: robot,
    });

    // Fault nodes — arc below robot
    const faultSlice = faults.slice(0, 7);
    faultSlice.forEach((f, i) => {
      const angle = ((i / Math.max(faultSlice.length - 1, 1)) - 0.5) * Math.PI * 1.2;
      const r = 200;
      const x = cx + r * Math.sin(angle);
      const y = cy + 120 + r * (1 - Math.cos(angle)) * 0.4;
      newNodes.push({ id: f.id, label: f.code || f.name, type: 'FAULT', x, y: y + 60, children: [], data: f });
      newEdges.push({ from: robot.id, to: f.id, label: 'FAULT' });
    });

    // Similar robots — upper arc
    const simSlice = similar.slice(0, 3);
    simSlice.forEach((s, i) => {
      const angle = ((i / Math.max(simSlice.length - 1, 1)) - 0.5) * Math.PI * 0.8;
      const r = 180;
      const x = cx + r * Math.sin(angle);
      newNodes.push({ id: s.id, label: s.name?.split('(')[0]?.trim() || s.id, type: 'ROBOT', x, y: cy - 160, children: [], data: s });
      newEdges.push({ from: robot.id, to: s.id, label: 'SIMILAR' });
    });

    setNodes(newNodes);
    setEdges(newEdges);
    setTransform({ x: 0, y: 0, scale: 1 });
  };

  /* ── Build EKG factory hierarchy layout ── */
  const buildEKGLayout = (factories: any[]) => {
    const newNodes: GraphNode[] = [];
    const newEdges: { from: string; to: string; label: string }[] = [];

    let yOffset = 60;

    factories.forEach((factory, fi) => {
      const fx = W / 2;
      newNodes.push({ id: factory.id, label: factory.name, type: 'FACTORY', x: fx, y: yOffset, children: [], data: factory });
      yOffset += 120;

      const plants = factory.plants || [];
      const plantSpacing = Math.min(280, (W - 100) / Math.max(plants.length, 1));
      const plantStart = fx - (plants.length - 1) * plantSpacing / 2;

      plants.forEach((plant: any, pi: number) => {
        const px = plantStart + pi * plantSpacing;
        const py = yOffset;
        newNodes.push({ id: plant.id, label: plant.name, type: 'PLANT', x: px, y: py, children: [], data: plant });
        newEdges.push({ from: factory.id, to: plant.id, label: 'HAS_PLANT' });

        const lines = plant.lines || [];
        const lineSpacing = Math.min(180, plantSpacing / Math.max(lines.length, 1));
        const lineStart = px - (lines.length - 1) * lineSpacing / 2;

        lines.slice(0, 3).forEach((line: any, li: number) => {
          const lx = lineStart + li * lineSpacing;
          const ly = py + 110;
          newNodes.push({ id: line.id, label: line.name, type: 'PRODUCTION_LINE', x: lx, y: ly, children: [], data: line });
          newEdges.push({ from: plant.id, to: line.id, label: 'HAS_LINE' });

          const machines = line.machines || [];
          const machSpacing = Math.min(120, lineSpacing / Math.max(machines.length, 1));
          const machStart = lx - (machines.length - 1) * machSpacing / 2;

          machines.slice(0, 4).forEach((mach: any, mi: number) => {
            const mx = machStart + mi * machSpacing;
            const my = ly + 110;
            newNodes.push({ id: mach.id, label: mach.name || mach.model || 'Machine', type: 'MACHINE', x: mx, y: my, children: [], data: mach });
            newEdges.push({ from: line.id, to: mach.id, label: 'HAS_MACHINE' });
          });

          yOffset = Math.max(yOffset, ly + 150);
        });

        yOffset = Math.max(yOffset, py + 260);
      });

      yOffset += 60;
    });

    setNodes(newNodes);
    setEdges(newEdges);
    setTransform({ x: 0, y: 0, scale: 1 });
  };

  /* ── Fallback demo EKG ── */
  const buildDefaultEKGLayout = () => {
    const demo = [{
      id: 'DEMO_FACTORY', name: 'Example Factory', plants: [{
        id: 'DEMO_PLANT_1', name: 'Body Shop', lines: [
          { id: 'DEMO_LINE_1', name: 'Welding Line 1', machines: [
            { id: 'DEMO_M1', name: 'ABB IRB 1600', model: 'IRB 1600-10' },
            { id: 'DEMO_M2', name: 'ABB IRB 1600', model: 'IRB 1600-10' },
          ]},
          { id: 'DEMO_LINE_2', name: 'Welding Line 2', machines: [
            { id: 'DEMO_M3', name: 'KUKA LBR iisy', model: 'LBR iisy 15' },
          ]},
        ]
      }]
    }];
    buildEKGLayout(demo);
  };

  /* ── Pan/zoom handlers ── */
  const onMouseDown = (e: React.MouseEvent) => {
    if ((e.target as SVGElement).closest('.node-group')) return;
    setDragging(true);
    setDragStart({ x: e.clientX - transform.x, y: e.clientY - transform.y });
  };
  const onMouseMove = (e: React.MouseEvent) => {
    if (!dragging) return;
    setTransform(t => ({ ...t, x: e.clientX - dragStart.x, y: e.clientY - dragStart.y }));
  };
  const onMouseUp = () => setDragging(false);
  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setTransform(t => ({ ...t, scale: Math.max(0.3, Math.min(2.5, t.scale * delta)) }));
  };

  /* ── Compute SVG height ── */
  const maxY = nodes.length > 0 ? Math.max(...nodes.map(n => n.y)) + 80 : 400;
  const svgH = Math.max(height, maxY);

  const nodeStyle = (type: string) => NODE_STYLE[type] || NODE_STYLE.DEFAULT;

  const nodeRadius = (type: string) => {
    if (type === 'FACTORY') return 38;
    if (type === 'PLANT') return 32;
    if (type === 'PRODUCTION_LINE') return 28;
    return 24;
  };

  return (
    <Box sx={{ width: '100%', bgcolor: '#09090f', borderRadius: 2, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.08)' }}>
      {/* Toolbar */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 2, py: 1, borderBottom: '1px solid rgba(255,255,255,0.07)', bgcolor: '#111119' }}>
        <AccountTreeIcon sx={{ color: '#06b6d4', fontSize: 18 }} />
        <Typography sx={{ color: '#e0f2fe', fontSize: '0.82rem', fontWeight: 700, flex: 1 }}>
          Knowledge Graph Visualisation
        </Typography>
        {/* View switcher */}
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          {[
            { id: 'robot', label: '🤖 Robot Graph' },
            { id: 'ekg',   label: '🏭 EKG Hierarchy' },
          ].map(v => (
            <Box key={v.id} onClick={() => setViewMode(v.id as any)}
              sx={{ px: 1.5, py: 0.5, borderRadius: 1.5, cursor: 'pointer', fontSize: '0.72rem', fontWeight: 600,
                bgcolor: viewMode === v.id ? '#06b6d4' : 'rgba(255,255,255,0.06)',
                color: viewMode === v.id ? '#000' : '#64748b',
                '&:hover': { bgcolor: viewMode === v.id ? '#06b6d4' : 'rgba(255,255,255,0.1)' } }}>
              {v.label}
            </Box>
          ))}
        </Box>

        {/* Zoom controls */}
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          {[
            { label: '+', action: () => setTransform(t => ({ ...t, scale: Math.min(2.5, t.scale * 1.2) }) )},
            { label: '−', action: () => setTransform(t => ({ ...t, scale: Math.max(0.3, t.scale * 0.85) }) )},
            { label: '↺', action: () => setTransform({ x: 0, y: 0, scale: 1 }) },
          ].map(b => (
            <Box key={b.label} onClick={b.action}
              sx={{ width: 26, height: 26, display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 1, cursor: 'pointer',
                bgcolor: 'rgba(255,255,255,0.07)', color: '#94a3b8', fontSize: '0.85rem', fontWeight: 700,
                '&:hover': { bgcolor: 'rgba(255,255,255,0.15)', color: 'white' } }}>
              {b.label}
            </Box>
          ))}
        </Box>

        <Typography sx={{ color: '#334155', fontSize: '0.62rem' }}>Drag to pan · Scroll to zoom</Typography>
      </Box>

      {/* Legend */}
      <Box sx={{ display: 'flex', gap: 1.5, px: 2, py: 0.75, borderBottom: '1px solid rgba(255,255,255,0.05)', flexWrap: 'wrap' }}>
        {[
          { type: 'FACTORY', label: 'Factory' },
          { type: 'PLANT', label: 'Plant' },
          { type: 'PRODUCTION_LINE', label: 'Line' },
          { type: 'MACHINE', label: 'Machine' },
          { type: 'FAULT', label: 'Fault' },
          { type: 'ROBOT', label: 'Robot' },
        ].map(({ type, label }) => {
          const s = nodeStyle(type);
          return (
            <Box key={type} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: s.stroke, opacity: 0.9 }} />
              <Typography sx={{ color: '#475569', fontSize: '0.62rem' }}>{label}</Typography>
            </Box>
          );
        })}
      </Box>

      {/* SVG Canvas */}
      <Box sx={{ position: 'relative', width: '100%', height, overflow: 'hidden', cursor: dragging ? 'grabbing' : 'grab' }}>
        {loading ? (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 1 }}>
            <CircularProgress size={20} sx={{ color: '#06b6d4' }} />
            <Typography sx={{ color: '#64748b', fontSize: '0.82rem' }}>Loading graph...</Typography>
          </Box>
        ) : (
          <svg ref={svgRef} width="100%" height={height}
            onMouseDown={onMouseDown} onMouseMove={onMouseMove} onMouseUp={onMouseUp} onMouseLeave={onMouseUp}
            onWheel={onWheel} style={{ display: 'block' }}>
            <defs>
              <marker id="arr" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="rgba(100,116,139,0.6)" />
              </marker>
              <filter id="glow">
                <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>

            <g transform={`translate(${transform.x},${transform.y}) scale(${transform.scale})`}>

              {/* Edges */}
              {edges.map((edge, i) => {
                const from = nodes.find(n => n.id === edge.from);
                const to   = nodes.find(n => n.id === edge.to);
                if (!from || !to) return null;
                const mx = (from.x + to.x) / 2;
                const my = (from.y + to.y) / 2;
                return (
                  <g key={i}>
                    <line x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                      stroke="rgba(100,116,139,0.35)" strokeWidth={1.5}
                      markerEnd="url(#arr)" />
                    <text x={mx} y={my - 6} fill="rgba(100,116,139,0.6)"
                      fontSize={8} textAnchor="middle" dominantBaseline="middle">
                      {edge.label}
                    </text>
                  </g>
                );
              })}

              {/* Nodes */}
              {nodes.map(node => {
                const s = nodeStyle(node.type);
                const r = nodeRadius(node.type);
                const isSelected = selected?.id === node.id;
                const label = node.label.length > 14 ? node.label.substring(0, 14) + '…' : node.label;

                return (
                  <g key={node.id} className="node-group" onClick={() => setSelected(isSelected ? null : node)}
                    style={{ cursor: 'pointer' }}>
                    {/* Glow ring for selected */}
                    {isSelected && (
                      <circle cx={node.x} cy={node.y} r={r + 8}
                        fill="none" stroke={s.stroke} strokeWidth={2} opacity={0.5}
                        strokeDasharray="4,4" filter="url(#glow)" />
                    )}
                    {/* Main circle */}
                    <circle cx={node.x} cy={node.y} r={r}
                      fill={s.fill} stroke={s.stroke} strokeWidth={isSelected ? 2.5 : 1.5} />
                    {/* Icon */}
                    <text x={node.x} y={node.y - 6} textAnchor="middle" dominantBaseline="middle"
                      fontSize={node.type === 'FACTORY' ? 16 : 13}>
                      {s.icon}
                    </text>
                    {/* Label */}
                    <text x={node.x} y={node.y + (r > 30 ? 14 : 10)}
                      fill={s.text} fontSize={node.type === 'FACTORY' ? 9 : 8}
                      textAnchor="middle" dominantBaseline="middle" fontWeight="600">
                      {label}
                    </text>
                    {/* Type badge */}
                    <text x={node.x} y={node.y + r + 12}
                      fill={s.stroke} fontSize={6.5} textAnchor="middle" dominantBaseline="middle" opacity={0.8}>
                      {node.type.replace('_', ' ')}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>
        )}

        {/* Node detail panel */}
        {selected && (
          <Box sx={{
            position: 'absolute', bottom: 12, right: 12,
            bgcolor: 'rgba(17,17,25,0.96)', border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: 2, p: 1.75, maxWidth: 240, backdropFilter: 'blur(8px)'
          }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
              <Box>
                <Typography sx={{ color: '#e0f2fe', fontWeight: 700, fontSize: '0.82rem' }}>{selected.label}</Typography>
                <Chip label={selected.type.replace('_', ' ')} size="small"
                  sx={{ fontSize: 9, height: 17, mt: 0.25, bgcolor: `${nodeStyle(selected.type).stroke}20`, color: nodeStyle(selected.type).stroke }} />
              </Box>
              <Box onClick={() => setSelected(null)} sx={{ cursor: 'pointer', color: '#64748b', fontSize: 14, '&:hover': { color: '#e0f2fe' } }}>✕</Box>
            </Box>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              {selected.data?.manufacturer && <Typography sx={{ color: '#64748b', fontSize: '0.72rem' }}>Manufacturer: <span style={{ color: '#94a3b8' }}>{selected.data.manufacturer}</span></Typography>}
              {selected.data?.payload_kg && <Typography sx={{ color: '#64748b', fontSize: '0.72rem' }}>Payload: <span style={{ color: '#94a3b8' }}>{selected.data.payload_kg} kg</span></Typography>}
              {selected.data?.reach_mm && <Typography sx={{ color: '#64748b', fontSize: '0.72rem' }}>Reach: <span style={{ color: '#94a3b8' }}>{selected.data.reach_mm} mm</span></Typography>}
              {selected.data?.severity && <Typography sx={{ color: '#64748b', fontSize: '0.72rem' }}>Severity: <span style={{ color: SEVERITY_COLORS[selected.data.severity] || '#94a3b8' }}>{selected.data.severity}</span></Typography>}
              {selected.data?.description && <Typography sx={{ color: '#94a3b8', fontSize: '0.7rem', mt: 0.5, lineHeight: 1.5 }}>{selected.data.description.substring(0, 100)}{selected.data.description.length > 100 ? '…' : ''}</Typography>}
              {selected.data?.location && <Typography sx={{ color: '#64748b', fontSize: '0.72rem' }}>Location: <span style={{ color: '#94a3b8' }}>{selected.data.location}</span></Typography>}
            </Box>
          </Box>
        )}
      </Box>

      {/* Stats bar */}
      <Box sx={{ display: 'flex', gap: 3, px: 2, py: 1, borderTop: '1px solid rgba(255,255,255,0.05)', bgcolor: '#111119' }}>
        {[
          { label: 'Nodes', value: nodes.length },
          { label: 'Edges', value: edges.length },
          { label: 'Factories', value: nodes.filter(n => n.type === 'FACTORY').length },
          { label: 'Machines', value: nodes.filter(n => n.type === 'MACHINE' || n.type === 'ROBOT').length },
          { label: 'Faults', value: nodes.filter(n => n.type === 'FAULT').length },
        ].map(s => (
          <Box key={s.label} sx={{ textAlign: 'center' }}>
            <Typography sx={{ color: '#06b6d4', fontWeight: 800, fontSize: '1rem', lineHeight: 1 }}>{s.value}</Typography>
            <Typography sx={{ color: '#334155', fontSize: '0.6rem' }}>{s.label}</Typography>
          </Box>
        ))}
        <Typography sx={{ color: '#1e293b', fontSize: '0.6rem', ml: 'auto', alignSelf: 'center' }}>
          Click any node for details
        </Typography>
      </Box>
    </Box>
  );
};

export default EKGTree;
