import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box, Typography, IconButton, Avatar, Chip, Tooltip,
  Divider, InputBase, Menu, MenuItem, ListItemIcon,
  ListItemText, LinearProgress, CircularProgress
} from '@mui/material';
import {
  PrecisionManufacturing as RobotIcon,
  AccountTree as KGIcon,
  Description as DocsIcon,
  BugReport as FaultIcon,
  Analytics as DiagnosticsIcon,
  Storage as DataIcon,
  FlightTakeoff as AviationIcon,
  LocalGasStation as OilIcon,
  Train as TrainIcon,
  Memory as SemiIcon,
  Factory as IndustrialIcon,
  Biotech as PharmaIcon,
  Close as CloseIcon,
  Logout as LogoutIcon,
  Person as PersonIcon,
  Add as NewChatIcon,
  KeyboardArrowRight as ArrowIcon,
  AutoAwesome as SparkleIcon,
  Mic as MicIcon,
  AttachFile as AttachIcon,
  Send as SendIcon,
  Psychology as AgentIcon,
  ChevronRight as ExpandIcon,
  ChevronLeft as CollapseIcon,
  Image as ImageIcon,
  PictureAsPdf as PdfIcon,
  Search as SearchIcon,
  Hub as EKGIcon,
  CloudUpload as UploadIcon,
  Link as LinkIcon,
  ArrowBack as BackIcon,
  Inventory as InventoryIcon,
  CheckCircle as CheckIcon,
  PlayArrow as RunIcon,
  Build as BuildIcon,
} from '@mui/icons-material';
import RAGChat from './RAGChat';
import EKGTree from './EKGTree';

/* ─── PALETTE ─────────────────────────── */
const C = {
  bg:'#09090f', s1:'#111119', s2:'#1a1a26', s3:'#23232f',
  b1:'rgba(255,255,255,0.06)', b2:'rgba(255,255,255,0.11)', b3:'rgba(255,255,255,0.18)',
  txt:'#eef2f7', sub:'#64748b', muted:'#2d3748',
  cyan:'#06b6d4', cyanL:'rgba(6,182,212,0.13)', cyanG:'rgba(6,182,212,0.24)',
};

/* ─── DATA ─────────────────────────────── */
const INDUSTRIES = [
  { id:'aviation',      label:'Aviation',       icon:<AviationIcon/>,   color:'#3b82f6',
    suggestions:['Diagnose vibration fault in CFM56 turbine','Build EKG for Boeing 737 MRO facility','What causes hydraulic pressure drop?','Upload Airbus A320 maintenance manual'] },
  { id:'oil-gas',       label:'Oil & Gas',       icon:<OilIcon/>,        color:'#f59e0b',
    suggestions:['Diagnose pump cavitation in offshore platform','Build EKG for refinery distillation unit','What causes pipeline pressure anomaly?','Upload drilling rig equipment manual'] },
  { id:'trains',        label:'Rail & Loco',     icon:<TrainIcon/>,      color:'#10b981',
    suggestions:['Diagnose traction motor fault in EMU locomotive','Build EKG for metro rail maintenance depot','What causes wheel slip fault in diesel loco?','Upload locomotive maintenance manual'] },
  { id:'semiconductor', label:'Semiconductor',   icon:<SemiIcon/>,       color:'#8b5cf6',
    suggestions:['Diagnose contamination fault in CVD chamber','Build EKG for semiconductor fab cleanroom','What causes wafer yield drop in etching?','Upload fab equipment service manual'] },
  { id:'industrial',    label:'Industrial',      icon:<IndustrialIcon/>, color:'#06b6d4',
    suggestions:['ABB IRB 1600 showing error E-001, how to fix?','Build EKG for Toyota welding plant','What causes KUKA LBR iisy axis overload?','Upload robot maintenance manual'] },
  { id:'pharma',        label:'Pharma',          icon:<PharmaIcon/>,     color:'#ec4899',
    suggestions:['Diagnose fill-seal machine pressure fault','Build EKG for pharmaceutical packaging line','What causes tablet coating defects?','Upload GMP equipment maintenance manual'] },
];

const DEFAULT_SUGGESTIONS = [
  'ABB IRB 1600 showing error E-001, how to fix?',
  'Build knowledge graph for Toyota welding plant',
  'What causes KUKA LBR iisy axis overload fault?',
  'Upload maintenance manual and extract fault codes',
];

const MODULES = [
  { id:'asset',   label:'Asset Registry',    icon:<InventoryIcon/>,   color:'#f59e0b' },
  { id:'kg',      label:'Knowledge Graph',   icon:<KGIcon/>,          color:'#8b5cf6' },
  { id:'data',    label:'Data Layer',        icon:<DataIcon/>,        color:'#6366f1' },
  { id:'diag',    label:'Diagnostics',       icon:<DiagnosticsIcon/>, color:'#06b6d4' },
  { id:'agents',  label:'Agent Store',       icon:<AgentIcon/>,       color:'#10b981' },
  { id:'docs',    label:'Repair Docs',       icon:<DocsIcon/>,        color:'#a78bfa' },
];

const RECENT = [
  { id:'1', title:'ABB GoFa fault E-001 diagnosis',  time:'2h ago'    },
  { id:'2', title:'Toyota welding plant EKG',        time:'Yesterday' },
  { id:'3', title:'KUKA LBR iisy overload fix',      time:'2d ago'    },
  { id:'4', title:'IRB 1600 manual ingestion',       time:'3d ago'    },
  { id:'5', title:'Fanuc CRX SRVO-023 repair',       time:'4d ago'    },
];

const AGENTS = [
  { name:'KG Builder Agent',       desc:'Reads PDFs and auto-builds the knowledge graph from extracted entities',  color:'#8b5cf6', status:'Active',   destination:'data',  action:'Upload a robot manual PDF to activate this agent' },
  { name:'Fault Diagnosis Agent',  desc:'Identifies faults from symptoms, images or error codes using GraphRAG',  color:'#ef4444', status:'Active',   destination:'chat',  action:'Ask about any robot fault to activate this agent'  },
  { name:'EKG Modeling Agent',     desc:'Builds factory hierarchy dynamically from natural language prompts',      color:'#06b6d4', status:'Building', destination:'kg',   action:'Describe your factory to build the EKG hierarchy'  },
  { name:'Data Pipeline Agent',    desc:'Connects to SharePoint, auto-pulls and ingests documents continuously',  color:'#f59e0b', status:'Planned',  destination:'data',  action:'Connect SharePoint URL in Data Layer'              },
  { name:'Repair Procedure Agent', desc:'Generates step-by-step repair guidance with required tools',             color:'#10b981', status:'Active',   destination:'chat',  action:'Ask for repair steps for any fault code'           },
  { name:'Reasoning Engine',       desc:'Orchestrates all agents — Plan → Evaluate → Adapt → Execute',           color:'#ec4899', status:'Building', destination:'diag',  action:'Orchestration engine — coming soon'                },
];

interface DashboardProps { onLogout: () => void; user: any; }

export default function Dashboard({ onLogout, user }: DashboardProps) {
  const [expanded,       setExpanded]       = useState(true);
  const [view,           setView]           = useState('home');
  const [industry,       setIndustry]       = useState<string|null>(null);
  const [chatQuery,      setChatQuery]      = useState('');
  const [query,          setQuery]          = useState('');
  const [anchor,         setAnchor]         = useState<null|HTMLElement>(null);
  const [pdfUploading,   setPdfUploading]   = useState(false);
  const [pdfProgress,    setPdfProgress]    = useState(0);
  const [pdfMsg,         setPdfMsg]         = useState('');
  const [ingestedDocs,   setIngestedDocs]   = useState<any[]>([]);
  const [graphStats,     setGraphStats]     = useState<any>(null);
  const [sharePointUrl,  setSharePointUrl]  = useState('');

  const inputRef = useRef<HTMLInputElement>(null);
  const fileRef  = useRef<HTMLInputElement>(null);
  const homeFileRef = useRef<HTMLInputElement>(null);
  const API      = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
  const tok      = () => localStorage.getItem('access_token');

  useEffect(() => { if (view==='home') setTimeout(() => inputRef.current?.focus(), 100); }, [view]);
  useEffect(() => { if (view==='data') { fetchDocs(); fetchStats(); } }, [view]);

  const ind         = INDUSTRIES.find(i => i.id === industry);
  const suggestions = ind ? ind.suggestions : DEFAULT_SUGGESTIONS;
  const SW          = expanded ? 240 : 64;

  const goHome   = ()          => { setView('home'); setQuery(''); };
  const goChat   = (q = '')    => { if (q) setChatQuery(q); setView('chat'); };
  const goModule = (id:string) => setView(id);
  const handleSearch = () => { if (query.trim()) { setChatQuery(query); setQuery(''); setView('chat'); } };

  const handleHomeAttach = () => {
  homeFileRef.current?.click();
};

const handleHomeMic = () => {
  const SR = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
  if (!SR) { alert('Voice input requires Chrome browser.'); return; }
  const recognition = new SR();
  recognition.lang = 'en-US';
  recognition.interimResults = false;
  recognition.onresult = (e: any) => setQuery(e.results[0][0].transcript);
  recognition.onerror = () => alert('Voice input failed. Please try again.');
  recognition.start();
};

const handleHomeFileUpload = (file: File) => {
  if (file.name.toLowerCase().endsWith('.pdf')) {
    setView('data');
    setTimeout(() => handlePdfUpload(file), 400);
  } else if (file.type.startsWith('image/')) {
    setChatQuery('Please analyze this fault image and diagnose the issue');
    setView('chat');
  }
};

  const fetchDocs = async () => {
    try {
      const r = await fetch(`${API}/api/ingest/history`, { headers:{ Authorization:`Bearer ${tok()}` } });
      const d = await r.json();
      if (d.success) setIngestedDocs(d.documents || []);
    } catch {}
  };

  const fetchStats = async () => {
    try {
      const r = await fetch(`${API}/api/ingest/graph-stats`, { headers:{ Authorization:`Bearer ${tok()}` } });
      const d = await r.json();
      if (d.success) setGraphStats(d);
    } catch {}
  };

  const handlePdfUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) return;
    setPdfUploading(true); setPdfProgress(10); setPdfMsg('Reading PDF...');
    try {
      const fd = new FormData(); fd.append('file', file);
      setPdfProgress(35); setPdfMsg('Extracting text from document...');
      const r = await fetch(`${API}/api/ingest/pdf`, { method:'POST', headers:{ Authorization:`Bearer ${tok()}` }, body:fd });
      setPdfProgress(70); setPdfMsg('AI extracting entities and building graph...');
      const d = await r.json(); setPdfProgress(100);
      if (d.success) {
        setPdfMsg(`✅ Done! ${d.summary.faults_found} faults, ${d.summary.procedures_found} procedures, +${d.summary.nodes_added_to_graph} nodes added`);
        fetchDocs(); fetchStats();
      } else { setPdfMsg(`❌ Error: ${d.error}`); }
    } catch (e:any) { setPdfMsg(`❌ Error: ${e.message}`); }
    finally { setTimeout(() => { setPdfUploading(false); setPdfProgress(0); }, 3500); }
  };

  /* ─── MODULE HEADER ─── */
  const ModHdr = ({ label, icon, color }:{ label:string; icon:React.ReactNode; color:string }) => (
    <Box sx={{ display:'flex', alignItems:'center', gap:1.5, px:3, py:1.75, borderBottom:`1px solid ${C.b1}`, bgcolor:C.s1, flexShrink:0 }}>
      <IconButton size="small" onClick={goHome} sx={{ color:C.sub, '&:hover':{ color:C.txt } }}>
        <BackIcon fontSize="small"/>
      </IconButton>
      <Box sx={{ color, display:'flex' }}>{React.cloneElement(icon as any, { sx:{ fontSize:20 } })}</Box>
      <Typography sx={{ color:C.txt, fontWeight:700, fontSize:'0.95rem' }}>{label}</Typography>
    </Box>
  );

  /* ─── ASSET REGISTRY ─── */
  const AssetView = () => {
    const [q,         setQ]         = useState('');
    const [results,   setResults]   = useState<any[]>([]);
    const [robots,    setRobots]    = useState<any[]>([]);
    const [searching, setSearching] = useState(false);

    useEffect(() => {
      fetch(`${API}/api/knowledge-graph/robots`, { headers:{ Authorization:`Bearer ${tok()}` } })
        .then(r=>r.json()).then(d=>{ if (d.success) setRobots(d.robots||[]); }).catch(()=>{});
    }, []);

    const search = async () => {
      if (!q.trim()) return;
      setSearching(true);
      try {
        const r = await fetch(`${API}/api/knowledge-graph/search?symptom=${encodeURIComponent(q)}`, { headers:{ Authorization:`Bearer ${tok()}` } });
        const d = await r.json();
        setResults(d.faults || []);
      } catch {} finally { setSearching(false); }
    };

    return (
      <Box sx={{ flex:1, overflowY:'auto', p:3 }}>
        <Typography sx={{ color:C.sub, fontSize:'0.82rem', mb:2.5 }}>
          Registry of all machines and assets in the knowledge graph. Search by model, serial number, plant, or fault symptom.
        </Typography>
        {robots.length > 0 && (
          <Box sx={{ mb:3 }}>
            <Typography sx={{ color:C.sub, fontSize:'0.62rem', textTransform:'uppercase', letterSpacing:'0.08em', mb:1.5 }}>
              Registered assets ({robots.length})
            </Typography>
            <Box sx={{ display:'flex', gap:1.5, flexWrap:'wrap' }}>
              {robots.map((r:any) => (
                <Box key={r.id} sx={{ px:2, py:1.2, bgcolor:C.s2, border:`1px solid ${C.b2}`, borderRadius:2, minWidth:180 }}>
                  <Typography sx={{ color:C.txt, fontWeight:600, fontSize:'0.82rem' }}>{r.name}</Typography>
                  <Typography sx={{ color:C.sub, fontSize:'0.68rem' }}>{r.manufacturer}</Typography>
                  {r.auto_extracted && <Chip label="From PDF" size="small" sx={{ fontSize:9, height:16, mt:0.5, bgcolor:'rgba(139,92,246,0.15)', color:'#a78bfa' }} />}
                </Box>
              ))}
            </Box>
          </Box>
        )}
        <Box sx={{ maxWidth:700 }}>
          <Box sx={{ display:'flex', gap:1, mb:1.5 }}>
            <InputBase fullWidth value={q} onChange={e=>setQ(e.target.value)} onKeyDown={e=>{ if (e.key==='Enter') search(); }}
              placeholder="Search by model, serial number, plant name, or fault symptom..."
              sx={{ flex:1, color:C.txt, fontSize:'0.88rem', bgcolor:C.s2, border:`1px solid ${C.b2}`, borderRadius:2, px:2, py:1.2, '&:focus-within':{ borderColor:C.cyan } }} />
            <Box onClick={search} sx={{ display:'flex', alignItems:'center', gap:1, px:2.5, py:1, borderRadius:2, cursor:'pointer', bgcolor:C.cyan, color:'#000', fontWeight:700, fontSize:'0.85rem' }}>
              {searching ? <CircularProgress size={16} sx={{ color:'#000' }}/> : <SearchIcon sx={{ fontSize:18 }}/>}
              Search
            </Box>
          </Box>
          <Box sx={{ display:'flex', gap:1, flexWrap:'wrap' }}>
            {['ABB IRB 1600','KUKA LBR iisy','Motor overload','Encoder fault','E-001'].map(t=>(
              <Chip key={t} label={t} size="small" onClick={()=>setQ(t)}
                sx={{ cursor:'pointer', bgcolor:C.s2, color:C.sub, border:`1px solid ${C.b2}`, '&:hover':{ bgcolor:C.s3, color:C.txt } }} />
            ))}
          </Box>
        </Box>
        {results.length > 0 && (
          <Box sx={{ maxWidth:700, mt:2.5 }}>
            <Typography sx={{ color:C.sub, fontSize:'0.62rem', textTransform:'uppercase', letterSpacing:'0.08em', mb:1 }}>Results ({results.length})</Typography>
            {results.map((f:any, i:number) => (
              <Box key={i} sx={{ p:2, mb:1, bgcolor:C.s2, border:`1px solid ${C.b2}`, borderRadius:2 }}>
                <Box sx={{ display:'flex', alignItems:'center', gap:1, mb:0.5 }}>
                  <Chip label={f.code} size="small" sx={{ bgcolor:'rgba(239,68,68,0.15)', color:'#ef4444', fontWeight:700, fontSize:11 }} />
                  <Typography sx={{ color:C.txt, fontWeight:600, fontSize:'0.85rem' }}>{f.name}</Typography>
                  <Chip label={f.severity||'—'} size="small" sx={{ ml:'auto', fontSize:10, height:18,
                    bgcolor:f.severity==='HIGH'?'rgba(239,68,68,0.15)':f.severity==='MEDIUM'?'rgba(245,158,11,0.15)':'rgba(16,185,129,0.15)',
                    color:f.severity==='HIGH'?'#ef4444':f.severity==='MEDIUM'?'#f59e0b':'#10b981' }} />
                </Box>
                <Typography sx={{ color:C.sub, fontSize:'0.78rem' }}>{f.description}</Typography>
              </Box>
            ))}
          </Box>
        )}
      </Box>
    );
  };

  /* ─── KNOWLEDGE GRAPH — with EKGTree visual ─── */
  const KGView = () => {
    const [prompt,   setPrompt]   = useState('');
    const [building, setBuilding] = useState(false);
    const [kgResult, setKgResult] = useState<any>(null);
    const [stats,    setStats]    = useState<any>(null);
    const [graphTab, setGraphTab] = useState(0); // 0 = visual, 1 = build

    useEffect(() => {
      fetch(`${API}/api/knowledge-graph/status`, { headers:{ Authorization:`Bearer ${tok()}` } })
        .then(r=>r.json()).then(d=>setStats(d)).catch(()=>{});
    }, []);

    const buildEKG = async () => {
      if (!prompt.trim()) return;
      setBuilding(true); setKgResult(null);
      try {
        const r = await fetch(`${API}/api/ekg/build-from-prompt`, {
          method: 'POST',
          headers: { 'Content-Type':'application/json', Authorization:`Bearer ${tok()}` },
          body: JSON.stringify({ prompt })
        });
        const d = await r.json();
        setKgResult(d);
        if (d.success) {
          // Refresh stats then switch to visual tab
          const s = await fetch(`${API}/api/knowledge-graph/status`, { headers:{ Authorization:`Bearer ${tok()}` } });
          setStats(await s.json());
          setGraphTab(0);
        }
      } catch (e:any) { setKgResult({ success:false, error:e.message }); }
      finally { setBuilding(false); }
    };

    return (
      <Box sx={{ flex:1, overflowY:'auto', p:3 }}>

        {/* Stats row */}
        {stats && (
          <Box sx={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:1.5, mb:3, maxWidth:960 }}>
            {[
              { label:'Total nodes', value:stats.total_nodes,       color:C.cyan    },
              { label:'Fault codes', value:stats.fault_codes,       color:'#ef4444' },
              { label:'Procedures',  value:stats.repair_procedures, color:'#10b981' },
              { label:'Robots',      value:stats.robots,            color:'#8b5cf6' },
            ].map(s=>(
              <Box key={s.label} sx={{ bgcolor:C.s2, border:`1px solid ${s.color}20`, borderRadius:2, p:2, textAlign:'center' }}>
                <Typography sx={{ fontSize:28, fontWeight:800, color:s.color, lineHeight:1 }}>{s.value}</Typography>
                <Typography sx={{ color:C.sub, fontSize:'0.72rem', mt:0.5 }}>{s.label}</Typography>
              </Box>
            ))}
          </Box>
        )}

        {/* Tab switcher */}
        <Box sx={{ display:'flex', gap:1, mb:2.5, maxWidth:960 }}>
          {[
            { id:0, label:'🕸  Graph Visualisation' },
            { id:1, label:'🏭  Build EKG from Prompt' },
          ].map(t=>(
            <Box key={t.id} onClick={()=>setGraphTab(t.id)}
              sx={{
                px:2, py:1, borderRadius:2, cursor:'pointer', fontSize:'0.82rem', fontWeight:600,
                bgcolor: graphTab===t.id ? C.cyan : 'transparent',
                color:   graphTab===t.id ? '#000' : C.sub,
                border:  `1px solid ${graphTab===t.id ? C.cyan : C.b2}`,
                transition:'all 0.15s',
                '&:hover':{ bgcolor: graphTab===t.id ? C.cyan : C.s2 }
              }}>
              {t.label}
            </Box>
          ))}
        </Box>

        {/* TAB 0 — Interactive graph visual */}
        {graphTab === 0 && (
          <Box sx={{ maxWidth:960 }}>
            <EKGTree height={500} />
          </Box>
        )}

        {/* TAB 1 — Build EKG from prompt */}
        {graphTab === 1 && (
          <Box sx={{ bgcolor:C.s2, border:`1px solid ${C.b2}`, borderRadius:3, p:2.5, maxWidth:960 }}>
            <Typography sx={{ color:C.txt, fontWeight:700, mb:0.5 }}>Build EKG dynamically</Typography>
            <Typography sx={{ color:C.sub, fontSize:'0.78rem', mb:2 }}>
              Describe your factory in natural language. The EKG Modeling Agent extracts the
              hierarchy and adds it to the knowledge graph with full deduplication.
            </Typography>

            {/* Hierarchy reminder */}
            <Box sx={{ display:'flex', gap:1, alignItems:'center', flexWrap:'wrap', mb:2 }}>
              {['Factory','Plant','Production Line','Machine','Component','Fault','Procedure'].map((n,i)=>(
                <React.Fragment key={n}>
                  {i > 0 && <ArrowIcon sx={{ color:C.muted, fontSize:15 }}/>}
                  <Chip label={n} size="small" sx={{ bgcolor:`rgba(139,92,246,${0.08+i*0.05})`, color:'#a78bfa', border:'1px solid rgba(139,92,246,0.2)', fontWeight:600 }}/>
                </React.Fragment>
              ))}
            </Box>

            <InputBase multiline rows={4} fullWidth value={prompt} onChange={e=>setPrompt(e.target.value)}
              placeholder="e.g. I have a Toyota plant in Mumbai with 2 body shops. Each body shop has 3 welding lines with 5 ABB IRB 1600 robots each. Each robot has a joint motor and encoder..."
              sx={{ color:C.txt, fontSize:'0.875rem', bgcolor:C.s3, border:`1px solid ${C.b2}`, borderRadius:2, p:1.5, mb:1.5, width:'100%', '&:focus-within':{ borderColor:'#8b5cf6' } }}/>

            {kgResult && (
              <Box sx={{ p:1.5, borderRadius:2, mb:1.5,
                bgcolor: kgResult.success ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                border:  `1px solid ${kgResult.success ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}` }}>
                <Typography sx={{ color:kgResult.success?'#10b981':'#ef4444', fontSize:'0.82rem', fontWeight:600 }}>
                  {kgResult.success ? `✅ ${kgResult.summary}` : `❌ ${kgResult.error}`}
                </Typography>
                {kgResult.success && (
                  <Typography sx={{ color:C.sub, fontSize:'0.72rem', mt:0.5 }}>
                    +{kgResult.nodes_created} nodes created · {kgResult.nodes_updated} updated · +{kgResult.edges_created} edges
                  </Typography>
                )}
              </Box>
            )}

            <Box onClick={buildEKG}
              sx={{ display:'inline-flex', alignItems:'center', gap:1, px:2.5, py:1, borderRadius:2, cursor:'pointer',
                bgcolor: prompt.trim() ? '#8b5cf6' : C.s3,
                color:   prompt.trim() ? 'white'   : C.sub,
                fontWeight:600, fontSize:'0.85rem',
                '&:hover':{ opacity:0.88 } }}>
              {building
                ? <CircularProgress size={16} sx={{ color:'white' }}/>
                : <EKGIcon sx={{ fontSize:16 }}/>}
              {building ? 'Building EKG...' : 'Build EKG from description'}
            </Box>
          </Box>
        )}
      </Box>
    );
  };

  /* ─── DATA LAYER ─── */
  const DataView = () => {
    const [dragging, setDragging] = useState(false);
    return (
      <Box sx={{ flex:1, overflowY:'auto', p:3 }}>
        {graphStats && (
          <Box sx={{ display:'flex', gap:1.5, mb:3, flexWrap:'wrap' }}>
            {[
              { label:'Total nodes', value:graphStats.total_nodes,          color:C.cyan    },
              { label:'From PDFs',   value:graphStats.auto_extracted_nodes, color:'#8b5cf6' },
              { label:'Faults',      value:graphStats.fault_codes,          color:'#ef4444' },
              { label:'Procedures',  value:graphStats.procedures,           color:'#10b981' },
            ].map(s=>(
              <Box key={s.label} sx={{ flex:1, minWidth:110, bgcolor:C.s2, border:`1px solid ${s.color}20`, borderRadius:2, p:2, textAlign:'center' }}>
                <Typography sx={{ fontSize:24, fontWeight:800, color:s.color, lineHeight:1 }}>{s.value??'—'}</Typography>
                <Typography sx={{ color:C.sub, fontSize:'0.68rem', mt:0.5 }}>{s.label}</Typography>
              </Box>
            ))}
          </Box>
        )}
        <Box sx={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:3, maxWidth:960 }}>
          <Box sx={{ bgcolor:C.s2, border:`1px solid ${C.b2}`, borderRadius:3, p:2.5 }}>
            <Box sx={{ display:'flex', alignItems:'center', gap:1, mb:0.5 }}>
              <PdfIcon sx={{ color:'#8b5cf6', fontSize:20 }}/>
              <Typography sx={{ color:C.txt, fontWeight:700 }}>Upload Robot Manual</Typography>
            </Box>
            <Typography sx={{ color:C.sub, fontSize:'0.76rem', mb:0.5 }}>
              AI extracts fault codes, procedures, and specs — updates knowledge graph automatically.
            </Typography>
            <Typography sx={{ color:'rgba(16,185,129,0.8)', fontSize:'0.68rem', mb:2 }}>
              ✓ Deduplication enabled — uploading same manual twice won't create duplicate nodes.
            </Typography>
            <Box
              onDragOver={e=>{ e.preventDefault(); setDragging(true); }}
              onDragLeave={()=>setDragging(false)}
              onDrop={e=>{ e.preventDefault(); setDragging(false); const f=e.dataTransfer.files[0]; if (f) handlePdfUpload(f); }}
              onClick={()=>fileRef.current?.click()}
              sx={{ border:`2px dashed ${dragging?'#8b5cf6':C.b2}`, borderRadius:2, p:2.5, textAlign:'center', cursor:'pointer',
                bgcolor:dragging?'rgba(139,92,246,0.1)':C.s3, transition:'all 0.2s',
                '&:hover':{ borderColor:'#8b5cf6', bgcolor:'rgba(139,92,246,0.08)' } }}>
              <UploadIcon sx={{ fontSize:32, color:'#8b5cf6', mb:0.5 }}/>
              <Typography sx={{ color:C.txt, fontSize:'0.85rem', fontWeight:600 }}>Drop PDF or click to upload</Typography>
              <Typography sx={{ color:C.sub, fontSize:'0.7rem', mt:0.5 }}>ABB · KUKA · Yaskawa · Universal Robots · Fanuc</Typography>
              <input ref={fileRef} type="file" accept=".pdf" style={{ display:'none' }} onChange={e=>e.target.files?.[0]&&handlePdfUpload(e.target.files[0])}/>
            </Box>
            {pdfUploading && (
              <Box sx={{ mt:1.5 }}>
                <Typography sx={{ color:C.cyan, fontSize:'0.72rem', mb:0.75 }}>{pdfMsg}</Typography>
                <LinearProgress variant="determinate" value={pdfProgress} sx={{ borderRadius:99, height:4, bgcolor:C.s3, '& .MuiLinearProgress-bar':{ bgcolor:'#8b5cf6' } }}/>
              </Box>
            )}
            {pdfMsg && !pdfUploading && <Typography sx={{ color:pdfMsg.startsWith('✅')?'#10b981':'#ef4444', fontSize:'0.72rem', mt:1 }}>{pdfMsg}</Typography>}
          </Box>
          <Box sx={{ bgcolor:C.s2, border:`1px solid ${C.b2}`, borderRadius:3, p:2.5 }}>
            <Box sx={{ display:'flex', alignItems:'center', gap:1, mb:0.5 }}>
              <LinkIcon sx={{ color:'#6366f1', fontSize:20 }}/>
              <Typography sx={{ color:C.txt, fontWeight:700 }}>SharePoint Connector</Typography>
            </Box>
            <Typography sx={{ color:C.sub, fontSize:'0.76rem', mb:2 }}>
              Connect your SharePoint — PAIOS auto-pulls documents and builds the knowledge graph continuously.
            </Typography>
            <Typography sx={{ color:C.sub, fontSize:'0.68rem', mb:0.75 }}>SharePoint URL</Typography>
            <InputBase fullWidth value={sharePointUrl} onChange={e=>setSharePointUrl(e.target.value)}
              placeholder="https://company.sharepoint.com/sites/maintenance/documents"
              sx={{ color:C.txt, fontSize:'0.82rem', bgcolor:C.s3, border:`1px solid ${C.b2}`, borderRadius:1.5, px:1.5, py:1, mb:1.5, width:'100%', '&:focus-within':{ borderColor:'#6366f1' } }}/>
            <Box sx={{ display:'flex', gap:1 }}>
              <Box sx={{ flex:1, textAlign:'center', py:1, borderRadius:1.5, cursor:'pointer', bgcolor:'#6366f1', color:'white', fontWeight:600, fontSize:'0.82rem', '&:hover':{ opacity:0.88 } }}>
                Connect & Sync
              </Box>
              <Box sx={{ flex:1, textAlign:'center', py:1, borderRadius:1.5, cursor:'pointer', border:`1px solid ${C.b2}`, color:C.sub, fontSize:'0.82rem', '&:hover':{ bgcolor:C.s3 } }}>
                Test Connection
              </Box>
            </Box>
          </Box>
        </Box>
        {ingestedDocs.length > 0 && (
          <Box sx={{ mt:3, maxWidth:960 }}>
            <Typography sx={{ color:C.sub, fontSize:'0.62rem', textTransform:'uppercase', letterSpacing:'0.08em', mb:1.5 }}>
              Ingested documents ({ingestedDocs.length})
            </Typography>
            {ingestedDocs.map((doc:any) => (
              <Box key={doc.document_id} sx={{ display:'flex', alignItems:'center', gap:2, p:1.5, bgcolor:C.s2, border:`1px solid ${C.b1}`, borderRadius:2, mb:1 }}>
                <PdfIcon sx={{ color:'#8b5cf6', fontSize:20, flexShrink:0 }}/>
                <Box sx={{ flex:1, overflow:'hidden' }}>
                  <Typography sx={{ color:C.txt, fontSize:'0.82rem', fontWeight:600, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{doc.filename}</Typography>
                  <Typography sx={{ color:C.sub, fontSize:'0.68rem' }}>{doc.robots_extracted} robots · {doc.faults_extracted} faults · {doc.procedures_extracted} procedures · +{doc.nodes_added} nodes</Typography>
                </Box>
                <Chip label={doc.status} size="small" sx={{ fontSize:10, height:18,
                  bgcolor:doc.status==='completed'?'rgba(16,185,129,0.15)':'rgba(239,68,68,0.15)',
                  color:doc.status==='completed'?'#10b981':'#ef4444' }}/>
              </Box>
            ))}
          </Box>
        )}
      </Box>
    );
  };

  /* ─── AGENT STORE ─── */
  const AgentsView = () => (
    <Box sx={{ flex:1, overflowY:'auto', p:3 }}>
      <Typography sx={{ color:C.sub, fontSize:'0.82rem', mb:3 }}>
        Specialised AI agents orchestrated by the Reasoning Engine. Click any agent to activate it.
      </Typography>
      <Box sx={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))', gap:2, maxWidth:960 }}>
        {AGENTS.map(a => {
          const sc = a.status==='Active'
            ? { bg:'rgba(16,185,129,0.14)', txt:'#10b981' }
            : a.status==='Building'
            ? { bg:'rgba(245,158,11,0.14)',  txt:'#f59e0b' }
            : { bg:'rgba(100,116,139,0.14)', txt:'#64748b' };
          const clickable = a.status !== 'Planned';
          return (
            <Box key={a.name} onClick={() => clickable && goModule(a.destination)}
              sx={{ p:2.5, borderRadius:3, border:`1px solid ${a.color}28`, bgcolor:`${a.color}06`,
                cursor:clickable?'pointer':'default', transition:'all 0.2s',
                '&:hover':clickable?{ borderColor:`${a.color}60`, transform:'translateY(-3px)', boxShadow:`0 8px 24px ${a.color}20` }:{} }}>
              <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', mb:1 }}>
                <Typography sx={{ color:C.txt, fontWeight:700, fontSize:'0.88rem' }}>{a.name}</Typography>
                <Chip label={a.status} size="small" sx={{ fontSize:10, height:20, bgcolor:sc.bg, color:sc.txt }}/>
              </Box>
              <Typography sx={{ color:C.sub, fontSize:'0.78rem', lineHeight:1.5, mb:1.5 }}>{a.desc}</Typography>
              {clickable && (
                <Box sx={{ display:'flex', alignItems:'center', gap:0.5 }}>
                  <RunIcon sx={{ fontSize:13, color:a.color }}/>
                  <Typography sx={{ color:a.color, fontSize:'0.7rem', fontWeight:600 }}>{a.action}</Typography>
                </Box>
              )}
            </Box>
          );
        })}
      </Box>
    </Box>
  );

  /* ─── RENDER ─── */
  const renderView = () => {
    if (view === 'chat') return (
      <Box sx={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden', bgcolor:'white' }}>
        <Box sx={{ display:'flex', alignItems:'center', gap:1.5, px:2.5, py:1.5, borderBottom:'1px solid #e2e8f0', bgcolor:'#f8fafc', flexShrink:0 }}>
          <IconButton size="small" onClick={goHome} sx={{ color:'#64748b' }}><BackIcon fontSize="small"/></IconButton>
          <RobotIcon sx={{ color:'#06b6d4', fontSize:18 }}/>
          <Typography sx={{ fontWeight:700, color:'#1e293b', fontSize:'0.88rem' }}>PAIOS AI</Typography>
          <Chip label="GraphRAG" size="small" sx={{ fontSize:9, height:18, bgcolor:'#f3e8ff', color:'#8b5cf6' }}/>
          <Chip label="Vision AI" size="small" sx={{ fontSize:9, height:18, bgcolor:'#e0f2fe', color:'#0369a1' }}/>
          {chatQuery && (
            <Typography sx={{ color:'#94a3b8', fontSize:'0.72rem', ml:1, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', maxWidth:280 }}>
              {chatQuery}
            </Typography>
          )}
        </Box>
        <Box sx={{ flex:1, overflow:'hidden' }}>
          <RAGChat initialQuery={chatQuery}/>
        </Box>
      </Box>
    );

    const moduleViews: Record<string, React.ReactNode> = {
      asset:  <><ModHdr label="Asset Registry"            icon={<InventoryIcon/>}   color="#f59e0b"/><AssetView/></>,
      kg:     <><ModHdr label="Enterprise Knowledge Graph" icon={<KGIcon/>}          color="#8b5cf6"/><KGView/></>,
      data:   <><ModHdr label="Data Layer"                icon={<DataIcon/>}         color="#6366f1"/><DataView/></>,
      agents: <><ModHdr label="Agent Store"               icon={<AgentIcon/>}        color="#10b981"/><AgentsView/></>,
      diag:   <><ModHdr label="Diagnostics"               icon={<DiagnosticsIcon/>}  color={C.cyan}/>
                <Box sx={{ p:4, textAlign:'center' }}><Typography sx={{ color:C.sub }}>Predictive maintenance models coming soon.</Typography></Box></>,
      docs:   <><ModHdr label="Repair Documentation"      icon={<DocsIcon/>}         color="#a78bfa"/>
                <Box sx={{ p:4, textAlign:'center' }}><Typography sx={{ color:C.sub }}>Auto-generated repair reports coming soon.</Typography></Box></>,
    };

    if (view in moduleViews) return (
      <Box sx={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden', bgcolor:C.bg }}>
        {moduleViews[view]}
      </Box>
    );

    /* ── HOME ── */
    return (
      <Box sx={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', px:3, pb:6, bgcolor:C.bg, overflowY:'auto' }}>
        <Box sx={{ textAlign:'center', mb:5 }}>
          <Box sx={{ display:'flex', alignItems:'center', justifyContent:'center', gap:1.5, mb:0.75 }}>
            <SparkleIcon sx={{ fontSize:30, color:C.cyan }}/>
            <Typography sx={{ fontSize:30, fontWeight:400, color:C.txt }}>Hi, {user?.first_name||'there'}</Typography>
          </Box>
          <Typography sx={{ fontSize:38, fontWeight:800, color:C.txt, letterSpacing:'-1.5px', mb:1.5 }}>
            Where should we start?
          </Typography>
          {ind && (
            <Chip icon={React.cloneElement(ind.icon as any,{ sx:{ fontSize:13 } })} label={ind.label} size="small"
              onDelete={()=>setIndustry(null)}
              sx={{ bgcolor:`${ind.color}18`, color:ind.color, border:`1px solid ${ind.color}40`, fontWeight:600 }}/>
          )}
        </Box>

        {/* Search bar */}
        <Box sx={{ width:'100%', maxWidth:720, mb:2.5 }}>
          <Box sx={{ display:'flex', alignItems:'center', gap:1, border:`1.5px solid ${C.b2}`, borderRadius:'18px', px:2.5, py:1.5, bgcolor:C.s1,
            '&:focus-within':{ borderColor:C.cyan, boxShadow:`0 0 0 3px ${C.cyanG}` } }}>
            <InputBase inputRef={inputRef} fullWidth value={query} onChange={e=>setQuery(e.target.value)}
              onKeyDown={e=>{ if (e.key==='Enter') handleSearch(); }}
              placeholder={ind?`Ask PAIOS about ${ind.label} equipment, faults or manuals...`:'Ask PAIOS — describe a fault, upload a manual, build an EKG...'}
              sx={{ fontSize:'0.95rem', color:C.txt, '& input::placeholder':{ color:C.sub, opacity:1 } }}/>
            <Box sx={{ display:'flex', alignItems:'center', gap:0.5, flexShrink:0 }}>
              <Tooltip title="Upload PDF or image">
  <IconButton size="small" onClick={handleHomeAttach}
    sx={{ color:C.sub, '&:hover':{ color:C.cyan } }}>
    <AttachIcon sx={{ fontSize:18 }}/>
  </IconButton>
</Tooltip>
<Tooltip title="Voice input — speak your question">
  <IconButton size="small" onClick={handleHomeMic}
    sx={{ color:C.sub, '&:hover':{ color:C.cyan } }}>
    <MicIcon sx={{ fontSize:18 }}/>
  </IconButton>
</Tooltip>
<input
  ref={homeFileRef}
  type="file"
  accept=".pdf,image/*"
  style={{ display:'none' }}
  onChange={e => e.target.files?.[0] && handleHomeFileUpload(e.target.files[0])}
/><IconButton size="small" onClick={handleSearch} disabled={!query.trim()}
                sx={{ bgcolor:query.trim()?C.cyan:'transparent', color:query.trim()?'#000':C.sub, borderRadius:1.5, p:0.8,
                  '&:hover':{ bgcolor:'#0891b2' }, '&:disabled':{ opacity:0.3 }, transition:'all 0.2s' }}>
                <SendIcon sx={{ fontSize:16 }}/>
              </IconButton>
            </Box>
          </Box>
          <Box sx={{ display:'flex', gap:1, mt:1.5, justifyContent:'center', flexWrap:'wrap' }}>
            {[
              { label:'Diagnose fault', color:'#ef4444', mod:'chat'   },
              { label:'Build EKG',      color:'#8b5cf6', mod:'kg'     },
              { label:'Upload manual',  color:'#10b981', mod:'data'   },
              { label:'Asset registry', color:C.cyan,   mod:'asset'  },
              { label:'Agent store',    color:'#f59e0b', mod:'agents' },
            ].map(q=>(
              <Chip key={q.label} label={q.label} size="small" onClick={()=>goModule(q.mod)}
                sx={{ cursor:'pointer', fontSize:12, fontWeight:500, bgcolor:`${q.color}12`, color:q.color,
                  border:`1px solid ${q.color}28`, '&:hover':{ bgcolor:`${q.color}22` } }}/>
            ))}
          </Box>
        </Box>

        {/* Industry icons */}
        <Box sx={{ display:'flex', gap:1.5, mb:4, flexWrap:'wrap', justifyContent:'center' }}>
          {INDUSTRIES.map(i=>(
            <Tooltip key={i.id} title={i.label}>
              <Box onClick={()=>setIndustry(industry===i.id?null:i.id)}
                sx={{ display:'flex', flexDirection:'column', alignItems:'center', gap:0.75, cursor:'pointer', p:1.5, borderRadius:2.5, minWidth:80,
                  border:`1px solid ${industry===i.id?i.color+'70':C.b1}`,
                  bgcolor:industry===i.id?`${i.color}12`:C.s1,
                  transition:'all 0.18s',
                  '&:hover':{ bgcolor:`${i.color}10`, border:`1px solid ${i.color}50`, transform:'translateY(-2px)' } }}>
                <Box sx={{ width:48, height:48, borderRadius:2.5,
                  bgcolor:industry===i.id?`${i.color}20`:C.s2,
                  border:`1px solid ${industry===i.id?i.color+'50':C.b1}`,
                  display:'flex', alignItems:'center', justifyContent:'center', color:i.color }}>
                  {React.cloneElement(i.icon as any, { sx:{ fontSize:24 } })}
                </Box>
                <Typography sx={{ fontSize:'0.68rem', textAlign:'center', color:industry===i.id?i.color:C.sub, fontWeight:industry===i.id?700:400 }}>
                  {i.label}
                </Typography>
              </Box>
            </Tooltip>
          ))}
        </Box>

        {/* Suggestions */}
        <Box sx={{ width:'100%', maxWidth:720 }}>
          <Typography sx={{ fontSize:'0.62rem', color:C.muted, mb:1.5, textAlign:'center', textTransform:'uppercase', letterSpacing:'0.1em' }}>
            {ind ? `${ind.label} quick starts` : 'Try asking'}
          </Typography>
          <Box sx={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:1 }}>
            {suggestions.map((s,i)=>(
              <Box key={i} onClick={()=>goChat(s)}
                sx={{ display:'flex', alignItems:'center', justifyContent:'space-between', px:2, py:1.4, borderRadius:2, cursor:'pointer',
                  border:`1px solid ${C.b1}`, bgcolor:C.s1,
                  '&:hover':{ borderColor:C.b3, bgcolor:C.s2, '& .hint':{ opacity:1, transform:'translateX(3px)' } },
                  transition:'all 0.15s' }}>
                <Box sx={{ display:'flex', alignItems:'center', gap:1.5 }}>
                  <SparkleIcon sx={{ fontSize:14, color:ind?ind.color:C.cyan, flexShrink:0 }}/>
                  <Typography sx={{ fontSize:'0.8rem', color:C.txt, lineHeight:1.4 }}>{s}</Typography>
                </Box>
                <ArrowIcon className="hint" sx={{ fontSize:15, color:C.sub, opacity:0.3, transition:'all 0.15s', flexShrink:0 }}/>
              </Box>
            ))}
          </Box>
        </Box>
      </Box>
    );
  };

  return (
    <Box sx={{ display:'flex', height:'100vh', bgcolor:C.bg, overflow:'hidden' }}>

      {/* ─── SIDEBAR ─── */}
      <Box sx={{ width:SW, flexShrink:0, bgcolor:C.s1, borderRight:`1px solid ${C.b1}`,
        display:'flex', flexDirection:'column', transition:'width 0.22s ease', overflow:'hidden', zIndex:20 }}>

        <Box sx={{ height:56, display:'flex', alignItems:'center', px:expanded?2:0,
          justifyContent:expanded?'space-between':'center', borderBottom:`1px solid ${C.b1}`, flexShrink:0 }}>
          {expanded && (
            <Box sx={{ display:'flex', alignItems:'center', gap:1 }}>
              <RobotIcon sx={{ color:C.cyan, fontSize:26 }}/>
              <Box>
                <Typography sx={{ fontWeight:900, fontSize:'1rem', color:C.txt, letterSpacing:'-0.5px', lineHeight:1 }}>PAIOS</Typography>
                <Typography sx={{ fontSize:'0.46rem', color:C.cyan, letterSpacing:'0.14em', textTransform:'uppercase', fontWeight:700 }}>Physical Agentic AI</Typography>
              </Box>
            </Box>
          )}
          <Tooltip title={expanded?'Collapse':'Expand'} placement="right">
            <IconButton size="small" onClick={()=>setExpanded(!expanded)}
              sx={{ color:C.sub, '&:hover':{ color:C.txt, bgcolor:C.s2 }, borderRadius:1.5 }}>
              {expanded?<CollapseIcon fontSize="small"/>:<ExpandIcon fontSize="small"/>}
            </IconButton>
          </Tooltip>
        </Box>

        <Box sx={{ px:1, pt:1.5, pb:0.5, flexShrink:0 }}>
          <Tooltip title={!expanded?'New conversation':''} placement="right">
            <Box onClick={goHome} sx={{ display:'flex', alignItems:'center', gap:1.5, px:expanded?1.5:0, py:1,
              justifyContent:expanded?'flex-start':'center', borderRadius:2, cursor:'pointer',
              border:`1px solid ${C.b2}`, bgcolor:C.s2, '&:hover':{ bgcolor:C.cyanL, borderColor:C.cyan } }}>
              <NewChatIcon sx={{ color:C.cyan, fontSize:18, flexShrink:0 }}/>
              {expanded && <Typography sx={{ fontSize:'0.82rem', color:C.txt, fontWeight:500 }}>New conversation</Typography>}
            </Box>
          </Tooltip>
        </Box>

        <Divider sx={{ borderColor:C.b1, mx:1, my:1 }}/>

        <Box sx={{ flex:1, overflowY:'auto', px:1,
          '&::-webkit-scrollbar':{ width:3 },
          '&::-webkit-scrollbar-thumb':{ bgcolor:C.s3, borderRadius:4 } }}>
          {expanded && <Typography sx={{ fontSize:'0.58rem', color:C.muted, px:1, pb:0.75, textTransform:'uppercase', letterSpacing:'0.1em' }}>Modules</Typography>}

          <Tooltip title={!expanded?'Asset Registry':''} placement="right">
            <Box onClick={()=>goModule('asset')}
              sx={{ display:'flex', alignItems:'center', gap:1.5, px:expanded?1.5:0,
                justifyContent:expanded?'flex-start':'center', py:1, mb:0.5, borderRadius:2, cursor:'pointer',
                bgcolor:view==='asset'?'rgba(245,158,11,0.15)':'transparent',
                border:`1px solid ${view==='asset'?'rgba(245,158,11,0.35)':'transparent'}`,
                '&:hover':{ bgcolor:'rgba(245,158,11,0.08)', border:'1px solid rgba(245,158,11,0.2)' },
                transition:'all 0.15s' }}>
              <InventoryIcon sx={{ fontSize:19, color:'#f59e0b', flexShrink:0 }}/>
              {expanded && <Typography sx={{ fontSize:'0.82rem', color:view==='asset'?'#f59e0b':C.txt, fontWeight:view==='asset'?700:400 }}>Asset Registry</Typography>}
            </Box>
          </Tooltip>

          {MODULES.filter(m=>m.id!=='asset').map(m=>(
            <Tooltip key={m.id} title={!expanded?m.label:''} placement="right">
              <Box onClick={()=>goModule(m.id)}
                sx={{ display:'flex', alignItems:'center', gap:1.5, px:expanded?1.5:0,
                  justifyContent:expanded?'flex-start':'center', py:1, mb:0.5, borderRadius:2, cursor:'pointer',
                  bgcolor:view===m.id?`${m.color}18`:'transparent',
                  border:`1px solid ${view===m.id?m.color+'38':'transparent'}`,
                  '&:hover':{ bgcolor:`${m.color}10`, border:`1px solid ${m.color}22` },
                  transition:'all 0.15s' }}>
                <Box sx={{ color:m.color, display:'flex', flexShrink:0 }}>
                  {React.cloneElement(m.icon as any, { sx:{ fontSize:19 } })}
                </Box>
                {expanded && <Typography sx={{ fontSize:'0.82rem', color:view===m.id?m.color:C.txt, fontWeight:view===m.id?700:400 }}>{m.label}</Typography>}
              </Box>
            </Tooltip>
          ))}

          {expanded && (
            <>
              <Divider sx={{ borderColor:C.b1, my:1.5 }}/>
              <Typography sx={{ fontSize:'0.58rem', color:C.muted, px:1, pb:0.75, textTransform:'uppercase', letterSpacing:'0.1em' }}>Recent</Typography>
              {RECENT.map(r=>(
                <Box key={r.id} onClick={()=>setView('chat')}
                  sx={{ px:1.5, py:1, borderRadius:2, cursor:'pointer', mb:0.5, '&:hover':{ bgcolor:C.s2 } }}>
                  <Typography sx={{ fontSize:'0.76rem', color:C.txt, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{r.title}</Typography>
                  <Typography sx={{ fontSize:'0.6rem', color:C.sub }}>{r.time}</Typography>
                </Box>
              ))}
            </>
          )}
        </Box>

        <Divider sx={{ borderColor:C.b1 }}/>
        <Box sx={{ px:1, py:1, flexShrink:0 }}>
          <Tooltip title={!expanded?`${user?.first_name} ${user?.last_name}`:''} placement="right">
            <Box onClick={e=>setAnchor(e.currentTarget as any)}
              sx={{ display:'flex', alignItems:'center', gap:1.5, px:expanded?1.5:0, py:1,
                justifyContent:expanded?'flex-start':'center', borderRadius:2, cursor:'pointer', '&:hover':{ bgcolor:C.s2 } }}>
              <Avatar sx={{ width:30, height:30, bgcolor:C.cyan, fontSize:'0.7rem', fontWeight:700, flexShrink:0 }}>
                {user?.first_name?.[0]}{user?.last_name?.[0]}
              </Avatar>
              {expanded && (
                <Box sx={{ overflow:'hidden', flex:1 }}>
                  <Typography sx={{ fontSize:'0.8rem', color:C.txt, fontWeight:600, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                    {user?.first_name} {user?.last_name}
                  </Typography>
                  <Typography sx={{ fontSize:'0.6rem', color:C.sub }}>{user?.role}</Typography>
                </Box>
              )}
            </Box>
          </Tooltip>
        </Box>
      </Box>

      <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={()=>setAnchor(null)}
        PaperProps={{ sx:{ bgcolor:C.s2, border:`1px solid ${C.b2}`, borderRadius:2, minWidth:160 } }}>
        <MenuItem sx={{ color:C.txt }}>
          <ListItemIcon><PersonIcon sx={{ color:C.sub }} fontSize="small"/></ListItemIcon>
          <ListItemText>Profile</ListItemText>
        </MenuItem>
        <Divider sx={{ borderColor:C.b1 }}/>
        <MenuItem onClick={onLogout} sx={{ color:'#ef4444' }}>
          <ListItemIcon><LogoutIcon sx={{ color:'#ef4444' }} fontSize="small"/></ListItemIcon>
          <ListItemText>Logout</ListItemText>
        </MenuItem>
      </Menu>

      <Box sx={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
        {renderView()}
      </Box>
    </Box>
  );
}
