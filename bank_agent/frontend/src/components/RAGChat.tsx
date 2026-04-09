import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box, Typography, TextField, IconButton, Avatar, Chip,
  CircularProgress, Divider, Tooltip, Collapse, Select,
  MenuItem, FormControl, InputLabel, Tab, Tabs, LinearProgress
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import PrecisionManufacturingIcon from '@mui/icons-material/PrecisionManufacturing';
import PersonIcon from '@mui/icons-material/Person';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import BugReportIcon from '@mui/icons-material/BugReport';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import ImageIcon from '@mui/icons-material/Image';
import CloseIcon from '@mui/icons-material/Close';
import UploadIcon from '@mui/icons-material/Upload';
import ChatIcon from '@mui/icons-material/Chat';
import WarningIcon from '@mui/icons-material/Warning';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import SourceIcon from '@mui/icons-material/Source';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  graph_context_used?: boolean;
  robot_identified?: string;
  fault_identified?: string;
  image_url?: string;
  severity?: string;
  timestamp: Date;
  isLoading?: boolean;
}

interface RAGChatProps {
  customerId?: number;
  customerName?: string;
  sessionId?: string;
  initialQuery?: string;
}

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
const getToken = () => localStorage.getItem('access_token');

const ROBOTS = [
  { id: 'ABB_GOFA',               name: 'ABB GoFa (CRB 15000)',    manufacturer: 'ABB',      color: '#ef4444' },
  { id: 'KUKA_LBR_IISY',          name: 'KUKA LBR iisy',           manufacturer: 'KUKA',     color: '#f59e0b' },
  { id: 'YASKAWA_ARCWORLD',       name: 'Yaskawa ArcWorld',         manufacturer: 'Yaskawa', color: '#6366f1' },
  { id: 'UNIVERSAL_ROBOTS_UR10E', name: 'Universal Robots UR10e',  manufacturer: 'UR',       color: '#10b981' },
  { id: 'FANUC_CRX',              name: 'Fanuc CRX-10iA',          manufacturer: 'Fanuc',    color: '#06b6d4' },
];

const SEVERITY_COLORS: Record<string, string> = {
  LOW: '#10b981', MEDIUM: '#f59e0b', HIGH: '#ef4444', CRITICAL: '#7c3aed', UNKNOWN: '#6b7280',
};

const CHAT_SUGGESTIONS = [
  'What are the common faults for this robot?',
  'How do I fix a motor overload fault?',
  'What does error E-001 mean?',
  'Robot stopped suddenly — what to check?',
];

const RAGChat: React.FC<RAGChatProps> = ({ customerId, customerName, sessionId, initialQuery }) => {
  const [activeTab, setActiveTab]     = useState(0);
  const [messages,  setMessages]      = useState<Message[]>([{
    id: 'welcome', role: 'assistant',
    content: `👋 Hello! I'm **PAIOS AI** — your expert robotics diagnostic assistant.\n\nI use **GraphRAG + Knowledge Graph + LLaMA 3** to give precise repair guidance.\n\n**How to use:**\n- 💬 **Chat tab** — Ask about any fault, error code or robot\n- 🔍 **Fault Analysis tab** — Upload a fault photo for Vision AI diagnosis\n\nSelect your robot below and let's get started!`,
    timestamp: new Date(),
  }]);
  const [input,         setInput]         = useState('');
  const [isLoading,     setIsLoading]     = useState(false);
  const [selectedRobot, setSelectedRobot] = useState('');
  const [showSources,   setShowSources]   = useState<string | null>(null);

  // Fault analysis tab state
  const [faultImage,    setFaultImage]    = useState<File | null>(null);
  const [faultPreview,  setFaultPreview]  = useState<string | null>(null);
  const [faultSymptom,  setFaultSymptom]  = useState('');
  const [analyzing,     setAnalyzing]     = useState(false);
  const [faultResult,   setFaultResult]   = useState('');
  const [faultSeverity, setFaultSeverity] = useState('');
  const [isDragging,    setIsDragging]    = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef   = useRef<HTMLInputElement>(null);
  const imgInputRef    = useRef<HTMLInputElement>(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  // Auto-send initialQuery when component mounts
  useEffect(() => {
    if (initialQuery && initialQuery.trim()) {
      setTimeout(() => sendMessage(initialQuery), 300);
    }
  }, [initialQuery]);

  /* ── CHAT SEND ── */
  const sendMessage = async (question: string) => {
    if ((!question.trim()) || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(), role: 'user',
      content: question, timestamp: new Date(),
    };
    const loadingMsg: Message = {
      id: (Date.now() + 1).toString(), role: 'assistant',
      content: '', timestamp: new Date(), isLoading: true,
    };
    setMessages(prev => [...prev, userMsg, loadingMsg]);
    setInput('');
    setIsLoading(true);

    const history = messages
      .filter(m => !m.isLoading && m.id !== 'welcome')
      .slice(-6)
      .map(m => ({ role: m.role, content: m.content }));

    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/api/graph-rag/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({
          question,
          robot_id: selectedRobot || undefined,
          conversation_history: history,
        }),
      });
      const data = await res.json();
      const assistantMsg: Message = {
        id: (Date.now() + 2).toString(), role: 'assistant',
        content: data.answer || 'Sorry, I could not generate a response.',
        sources: data.sources || [],
        graph_context_used: data.graph_context_used,
        robot_identified: data.robot_identified,
        fault_identified: data.fault_identified,
        timestamp: new Date(),
      };
      setMessages(prev => prev.filter(m => !m.isLoading).concat(assistantMsg));
      if (data.robot_identified && !selectedRobot) setSelectedRobot(data.robot_identified);
    } catch {
      setMessages(prev => prev.filter(m => !m.isLoading).concat({
        id: (Date.now() + 2).toString(), role: 'assistant',
        content: '❌ Connection error. Please check the backend is running on port 8000.',
        timestamp: new Date(),
      }));
    } finally {
      setIsLoading(false);
    }
  };

  /* ── FAULT ANALYSIS ── */
  const handleImageDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      setFaultImage(file);
      const reader = new FileReader();
      reader.onloadend = () => setFaultPreview(reader.result as string);
      reader.readAsDataURL(file);
    }
  }, []);

  const handleImageSelect = (file: File) => {
    if (!file.type.startsWith('image/')) return;
    setFaultImage(file);
    const reader = new FileReader();
    reader.onloadend = () => setFaultPreview(reader.result as string);
    reader.readAsDataURL(file);
  };

  const analyzeFault = async () => {
    if (!faultImage && !faultSymptom.trim()) return;
    setAnalyzing(true);
    setFaultResult('');
    setFaultSeverity('');

    try {
      const token = getToken();

      if (faultImage) {
        // Vision AI analysis
        const fd = new FormData();
        fd.append('image', faultImage);
        if (faultSymptom) fd.append('context', faultSymptom);
        if (selectedRobot) fd.append('robot_id', selectedRobot);

        const res = await fetch(`${API_BASE}/api/vision/analyze`, {
          method: 'POST',
          headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          body: fd,
        });
        const data = await res.json();
        setFaultResult(data.final_answer || data.answer || 'Vision analysis complete.');
        setFaultSeverity(data.severity || '');

        // Also add to chat history
        const resultMsg: Message = {
          id: Date.now().toString(), role: 'assistant',
          content: `🔍 **Vision AI Diagnosis:**\n\n${data.final_answer || data.answer}`,
          sources: ['Vision AI', 'Knowledge Graph'],
          graph_context_used: !!data.knowledge_graph_diagnosis?.fault,
          robot_identified: data.robot_identified,
          fault_identified: data.fault_code,
          severity: data.severity,
          image_url: faultPreview || undefined,
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, resultMsg]);

      } else if (faultSymptom.trim()) {
        // Text-only diagnosis via GraphRAG
        const res = await fetch(`${API_BASE}/api/graph-rag/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          body: JSON.stringify({
            question: faultSymptom,
            robot_id: selectedRobot || undefined,
          }),
        });
        const data = await res.json();
        setFaultResult(data.answer || 'Diagnosis complete.');
      }
    } catch (e: any) {
      setFaultResult(`Analysis failed: ${e.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const clearFault = () => {
    setFaultImage(null);
    setFaultPreview(null);
    setFaultSymptom('');
    setFaultResult('');
    setFaultSeverity('');
  };

  const fmt = (s: string) =>
    s.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
     .replace(/\*(.*?)\*/g, '<em>$1</em>')
     .replace(/\n/g, '<br/>');

  /* ── RENDER ── */
  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: '#f0f7ff' }}>

      {/* Header */}
      <Box sx={{ p: 1.5, background: 'linear-gradient(135deg, #0c4a6e 0%, #0369a1 60%, #06b6d4 100%)', display: 'flex', alignItems: 'center', gap: 1.5, flexShrink: 0 }}>
        <Avatar sx={{ bgcolor: 'rgba(255,255,255,0.15)', width: 36, height: 36, border: '2px solid rgba(255,255,255,0.3)' }}>
          <PrecisionManufacturingIcon sx={{ color: 'white', fontSize: 20 }} />
        </Avatar>
        <Box sx={{ flex: 1 }}>
          <Typography variant="subtitle2" fontWeight={800} color="white" sx={{ lineHeight: 1.2 }}>PAIOS AI Assistant</Typography>
          <Typography variant="caption" color="rgba(255,255,255,0.7)" sx={{ fontSize: '0.6rem' }}>GraphRAG · Vision AI · Knowledge Graph · LLaMA 3</Typography>
        </Box>
        <Chip icon={<AccountTreeIcon sx={{ fontSize: 11 }} />} label="GraphRAG" size="small" sx={{ bgcolor: 'rgba(139,92,246,0.4)', color: 'white', fontSize: 10, height: 20 }} />
        <Chip icon={<CameraAltIcon sx={{ fontSize: 11 }} />} label="Vision AI" size="small" sx={{ bgcolor: 'rgba(6,182,212,0.4)', color: 'white', fontSize: 10, height: 20 }} />
      </Box>

      {/* Robot selector */}
      <Box sx={{ px: 2, py: 1.25, bgcolor: '#e0f2fe', borderBottom: '1px solid #bae6fd', flexShrink: 0 }}>
        <FormControl fullWidth size="small">
          <InputLabel sx={{ fontSize: '0.78rem' }}>Select Robot / Cobot</InputLabel>
          <Select value={selectedRobot} label="Select Robot / Cobot"
            onChange={e => setSelectedRobot(e.target.value)} sx={{ fontSize: '0.82rem', bgcolor: 'white' }}>
            <MenuItem value=""><em>General question (no specific robot)</em></MenuItem>
            {ROBOTS.map(r => (
              <MenuItem key={r.id} value={r.id}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip label={r.manufacturer} size="small" sx={{ fontSize: 9, height: 18, bgcolor: r.color, color: 'white' }} />
                  {r.name}
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        {selectedRobot && (
          <Typography variant="caption" sx={{ color: '#0369a1', display: 'block', mt: 0.5, fontSize: '0.67rem' }}>
            ✅ Context set — answers will use this robot's knowledge graph data
          </Typography>
        )}
      </Box>

      {/* Tabs */}
      <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)}
        sx={{ bgcolor: '#1e293b', minHeight: 38, flexShrink: 0,
          '& .MuiTab-root': { color: '#64748b', minHeight: 38, fontSize: '0.72rem', fontWeight: 600 },
          '& .Mui-selected': { color: '#06b6d4' },
          '& .MuiTabs-indicator': { backgroundColor: '#06b6d4' } }}>
        <Tab icon={<ChatIcon sx={{ fontSize: 15 }} />} iconPosition="start" label="Chat" />
        <Tab icon={<CameraAltIcon sx={{ fontSize: 15 }} />} iconPosition="start" label="Fault Analysis" />
      </Tabs>

      {/* ── TAB 0: CHAT ── */}
      {activeTab === 0 && (
        <>
          <Box sx={{ flex: 1, overflowY: 'auto', p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            {messages.map(msg => (
              <Box key={msg.id} sx={{ display: 'flex', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row', gap: 1.5, alignItems: 'flex-start' }}>
                <Avatar sx={{ width: 30, height: 30, bgcolor: msg.role === 'user' ? '#0369a1' : '#0c4a6e', flexShrink: 0 }}>
                  {msg.role === 'user' ? <PersonIcon sx={{ fontSize: 16 }} /> : <SmartToyIcon sx={{ fontSize: 16 }} />}
                </Avatar>
                <Box sx={{ maxWidth: '78%' }}>
                  {msg.image_url && (
                    <Box sx={{ mb: 1, borderRadius: 2, overflow: 'hidden', maxWidth: 160, border: '2px solid #06b6d4' }}>
                      <img src={msg.image_url} alt="uploaded" style={{ width: '100%', display: 'block' }} />
                    </Box>
                  )}
                  <Box sx={{ p: 1.5, bgcolor: msg.role === 'user' ? '#0369a1' : '#ffffff',
                    borderRadius: msg.role === 'user' ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
                    {msg.isLoading ? (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <CircularProgress size={14} sx={{ color: '#06b6d4' }} />
                        <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.78rem' }}>Querying knowledge graph...</Typography>
                      </Box>
                    ) : (
                      <Typography variant="body2" sx={{ color: msg.role === 'user' ? 'white' : '#1a2332', lineHeight: 1.7, fontSize: '0.85rem' }}
                        dangerouslySetInnerHTML={{ __html: fmt(msg.content) }} />
                    )}
                  </Box>

                  {/* Metadata chips */}
                  {msg.role === 'assistant' && !msg.isLoading && (
                    <Box sx={{ mt: 0.5, display: 'flex', gap: 0.5, flexWrap: 'wrap', alignItems: 'center' }}>
                      {msg.severity && msg.severity !== 'UNKNOWN' && (
                        <Chip icon={<WarningIcon sx={{ fontSize: 10 }} />} label={`${msg.severity} severity`} size="small"
                          sx={{ fontSize: 9, height: 17, bgcolor: `${SEVERITY_COLORS[msg.severity]}22`, color: SEVERITY_COLORS[msg.severity], border: `1px solid ${SEVERITY_COLORS[msg.severity]}44` }} />
                      )}
                      {msg.graph_context_used && (
                        <Chip icon={<AccountTreeIcon sx={{ fontSize: 10 }} />} label="Graph used" size="small"
                          sx={{ fontSize: 9, height: 17, bgcolor: '#f3e8ff', color: '#8b5cf6' }} />
                      )}
                      {msg.robot_identified && (
                        <Chip icon={<PrecisionManufacturingIcon sx={{ fontSize: 10 }} />}
                          label={msg.robot_identified.replace(/_/g, ' ')} size="small"
                          sx={{ fontSize: 9, height: 17, bgcolor: '#e0f2fe', color: '#0369a1' }} />
                      )}
                      {msg.fault_identified && msg.fault_identified !== 'Not visible' && (
                        <Chip icon={<BugReportIcon sx={{ fontSize: 10 }} />} label={`Fault: ${msg.fault_identified}`} size="small"
                          sx={{ fontSize: 9, height: 17, bgcolor: '#fee2e2', color: '#ef4444' }} />
                      )}
                      {msg.sources && msg.sources.length > 0 && (
                        <Tooltip title="Click to see sources">
                          <Chip icon={<SourceIcon sx={{ fontSize: 10 }} />} label={`${msg.sources.length} sources`} size="small" variant="outlined"
                            onClick={() => setShowSources(showSources === msg.id ? null : msg.id)}
                            sx={{ fontSize: 9, height: 17, cursor: 'pointer', borderColor: '#06b6d4', color: '#06b6d4' }} />
                        </Tooltip>
                      )}
                    </Box>
                  )}
                  {msg.sources && msg.sources.length > 0 && (
                    <Collapse in={showSources === msg.id}>
                      <Box sx={{ mt: 0.5, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        {msg.sources.map((src, i) => (
                          <Chip key={i} label={src} size="small" sx={{ fontSize: 9, height: 17, bgcolor: '#e0f2fe', color: '#0c4a6e' }} />
                        ))}
                      </Box>
                    </Collapse>
                  )}
                  <Typography variant="caption" color="text.disabled" sx={{ ml: 0.5, fontSize: '0.62rem' }}>
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </Typography>
                </Box>
              </Box>
            ))}
            <div ref={messagesEndRef} />
          </Box>

          {/* Suggestions */}
          {messages.length <= 2 && (
            <Box sx={{ px: 2, pb: 1, flexShrink: 0 }}>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 0.75, display: 'block', fontSize: '0.67rem' }}>💡 Try asking:</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {CHAT_SUGGESTIONS.map((q, i) => (
                  <Chip key={i} label={q} size="small" onClick={() => sendMessage(q)}
                    sx={{ fontSize: 10, cursor: 'pointer', bgcolor: '#e0f2fe', color: '#0c4a6e', '&:hover': { bgcolor: '#0369a1', color: 'white' } }} />
                ))}
              </Box>
            </Box>
          )}

          <Divider />

          {/* Input */}
          <Box sx={{ p: 1.5, bgcolor: 'white', display: 'flex', gap: 1, alignItems: 'flex-end', flexShrink: 0 }}>
            <TextField fullWidth multiline maxRows={3} size="small"
              placeholder="Describe a fault, ask about error codes, or ask anything..."
              value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }}
              disabled={isLoading}
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: 3, fontSize: '0.85rem' } }} />
            <IconButton onClick={() => sendMessage(input)} disabled={!input.trim() || isLoading}
              sx={{ background: 'linear-gradient(135deg, #0c4a6e, #06b6d4)', color: 'white', '&:hover': { background: 'linear-gradient(135deg, #06b6d4, #0c4a6e)' }, '&:disabled': { bgcolor: '#ccc' }, width: 38, height: 38 }}>
              {isLoading ? <CircularProgress size={16} color="inherit" /> : <SendIcon fontSize="small" />}
            </IconButton>
          </Box>
        </>
      )}

      {/* ── TAB 1: FAULT ANALYSIS ── */}
      {activeTab === 1 && (
        <Box sx={{ flex: 1, overflowY: 'auto', p: 2 }}>
          <Typography sx={{ color: '#64748b', fontSize: '0.8rem', mb: 2 }}>
            Upload a photo of the faulty machine or describe symptoms. PAIOS Vision AI + Knowledge Graph will diagnose instantly.
          </Typography>

          {/* Image drop zone */}
          <Box
            onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleImageDrop}
            onClick={() => !faultPreview && imgInputRef.current?.click()}
            sx={{
              border: `2px dashed ${isDragging ? '#06b6d4' : '#bae6fd'}`,
              borderRadius: 3, p: 2.5, textAlign: 'center', mb: 2,
              cursor: faultPreview ? 'default' : 'pointer', minHeight: 160,
              bgcolor: isDragging ? '#e0f2fe' : '#f0f9ff',
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              transition: 'all 0.2s',
              '&:hover': !faultPreview ? { borderColor: '#06b6d4', bgcolor: '#e0f2fe' } : {}
            }}>
            {faultPreview ? (
              <Box sx={{ position: 'relative', display: 'inline-block' }}>
                <img src={faultPreview} alt="fault" style={{ maxHeight: 180, maxWidth: '100%', borderRadius: 8, display: 'block' }} />
                <IconButton size="small" onClick={e => { e.stopPropagation(); setFaultImage(null); setFaultPreview(null); }}
                  sx={{ position: 'absolute', top: -10, right: -10, bgcolor: '#ef4444', color: 'white', width: 24, height: 24, '&:hover': { bgcolor: '#dc2626' } }}>
                  <CloseIcon sx={{ fontSize: 14 }} />
                </IconButton>
              </Box>
            ) : (
              <>
                <CameraAltIcon sx={{ fontSize: 40, color: '#06b6d4', mb: 1 }} />
                <Typography sx={{ color: '#0369a1', fontWeight: 600, fontSize: '0.9rem', mb: 0.5 }}>
                  Drop fault image here
                </Typography>
                <Typography variant="caption" sx={{ color: '#64748b' }}>
                  or click to upload — JPG, PNG, WebP
                </Typography>
              </>
            )}
            <input ref={imgInputRef} type="file" accept="image/*" style={{ display: 'none' }}
              onChange={e => e.target.files?.[0] && handleImageSelect(e.target.files[0])} />
          </Box>

          {/* Symptom description */}
          <Box sx={{ mb: 2 }}>
            <Typography sx={{ color: '#64748b', fontSize: '0.72rem', mb: 0.75, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Describe symptoms (optional)
            </Typography>
            <TextField multiline rows={3} fullWidth value={faultSymptom}
              onChange={e => setFaultSymptom(e.target.value)}
              placeholder="e.g. Robot stopped suddenly, error E-001 on display, joint 3 making grinding noise, motor feels hot..."
              sx={{ '& .MuiOutlinedInput-root': { fontSize: '0.85rem', bgcolor: 'white', borderRadius: 2 } }} />
          </Box>

          {/* Analyze button */}
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            <Box onClick={analyzeFault}
              sx={{
                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1,
                py: 1.25, borderRadius: 2, cursor: (faultImage || faultSymptom.trim()) ? 'pointer' : 'not-allowed',
                bgcolor: (faultImage || faultSymptom.trim()) ? '#06b6d4' : '#e2e8f0',
                color: (faultImage || faultSymptom.trim()) ? 'white' : '#94a3b8',
                fontWeight: 700, fontSize: '0.9rem', transition: 'all 0.2s',
                '&:hover': (faultImage || faultSymptom.trim()) ? { bgcolor: '#0891b2' } : {}
              }}>
              {analyzing
                ? <><CircularProgress size={18} sx={{ color: 'white' }} /> Analyzing with Vision AI...</>
                : <><CameraAltIcon sx={{ fontSize: 18 }} /> {faultImage ? 'Analyze with Vision AI' : 'Diagnose from symptoms'}</>
              }
            </Box>
            {(faultImage || faultSymptom || faultResult) && (
              <Box onClick={clearFault}
                sx={{ px: 2, py: 1.25, borderRadius: 2, cursor: 'pointer', border: '1px solid #e2e8f0', color: '#64748b', fontSize: '0.85rem', '&:hover': { bgcolor: '#f1f5f9' } }}>
                Clear
              </Box>
            )}
          </Box>

          {/* Severity badge */}
          {faultSeverity && faultSeverity !== 'UNKNOWN' && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5, p: 1, bgcolor: `${SEVERITY_COLORS[faultSeverity]}12`, border: `1px solid ${SEVERITY_COLORS[faultSeverity]}30`, borderRadius: 2 }}>
              <WarningIcon sx={{ color: SEVERITY_COLORS[faultSeverity], fontSize: 18 }} />
              <Typography sx={{ color: SEVERITY_COLORS[faultSeverity], fontWeight: 700, fontSize: '0.85rem' }}>
                Severity: {faultSeverity}
              </Typography>
            </Box>
          )}

          {/* Result */}
          {faultResult && (
            <Box sx={{ p: 2, bgcolor: 'white', border: '1px solid #e2e8f0', borderRadius: 2, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                <CheckCircleIcon sx={{ color: '#10b981', fontSize: 18 }} />
                <Typography sx={{ color: '#1e293b', fontWeight: 700, fontSize: '0.88rem' }}>AI Diagnosis Result</Typography>
                <Chip label="GraphRAG" size="small" sx={{ fontSize: 9, height: 18, bgcolor: '#f3e8ff', color: '#8b5cf6', ml: 'auto' }} />
              </Box>
              <Typography sx={{ color: '#334155', fontSize: '0.85rem', lineHeight: 1.7 }}
                dangerouslySetInnerHTML={{ __html: fmt(faultResult) }} />
              <Box sx={{ mt: 1.5, pt: 1.5, borderTop: '1px solid #f1f5f9' }}>
                <Typography sx={{ color: '#94a3b8', fontSize: '0.72rem' }}>
                  Switch to the Chat tab to ask follow-up questions about this diagnosis.
                </Typography>
              </Box>
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
};

export default RAGChat;
