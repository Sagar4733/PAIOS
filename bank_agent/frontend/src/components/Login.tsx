import React, { useState } from 'react';
import { Box, Typography, InputBase, IconButton, Chip, CircularProgress } from '@mui/material';
import {
  PrecisionManufacturing as RobotIcon,
  Visibility as EyeIcon,
  VisibilityOff as EyeOffIcon,
  Send as SendIcon,
  Lock as LockIcon,
  Person as PersonIcon,
  AutoAwesome as SparkleIcon,
} from '@mui/icons-material';

const C = {
  bg:   '#09090f',
  s1:   '#111119',
  s2:   '#1a1a26',
  b1:   'rgba(255,255,255,0.06)',
  b2:   'rgba(255,255,255,0.12)',
  txt:  '#eef2f7',
  sub:  '#64748b',
  cyan: '#06b6d4',
  cyanG:'rgba(6,182,212,0.22)',
};

interface LoginProps {
  onLogin: (user: any, token: string) => void;
}

const DEMO_CREDENTIALS = [
  { label: 'Admin',    username: 'admin',   password: 'admin123',   role: 'admin'   },
  { label: 'Analyst',  username: 'analyst', password: 'analyst123', role: 'analyst' },
];

const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [username,    setUsername]    = useState('');
  const [password,    setPassword]    = useState('');
  const [showPass,    setShowPass]    = useState(false);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState('');

  const API = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

  const handleLogin = async (u = username, p = password) => {
    if (!u.trim() || !p.trim()) { setError('Please enter username and password.'); return; }
    setLoading(true); setError('');
    try {
      const fd = new FormData();
      fd.append('username', u); fd.append('password', p);
      const res = await fetch(`${API}/auth/token`, { method: 'POST', body: fd });
      if (!res.ok) { setError('Invalid username or password.'); setLoading(false); return; }
      const data = await res.json();
      const token = data.access_token;

      // Get user info
      const userRes = await fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
      const user = await userRes.json();

      localStorage.setItem('access_token', token);
      onLogin(user, token);
    } catch {
      setError('Cannot connect to PAIOS backend. Make sure it is running.');
    } finally {
      setLoading(false);
    }
  };

  const quickLogin = (cred: typeof DEMO_CREDENTIALS[0]) => {
    setUsername(cred.username);
    setPassword(cred.password);
    handleLogin(cred.username, cred.password);
  };

  return (
    <Box sx={{
      minHeight: '100vh', bgcolor: C.bg, display: 'flex',
      alignItems: 'center', justifyContent: 'center', px: 2,
      background: `radial-gradient(ellipse at 60% 0%, rgba(6,182,212,0.07) 0%, transparent 60%),
                   radial-gradient(ellipse at 0% 80%, rgba(139,92,246,0.06) 0%, transparent 50%),
                   ${C.bg}`
    }}>
      <Box sx={{ width: '100%', maxWidth: 420 }}>

        {/* Logo */}
        <Box sx={{ textAlign: 'center', mb: 5 }}>
          <Box sx={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 72, height: 72, borderRadius: 4,
            bgcolor: C.s2, border: `1px solid ${C.b2}`, mb: 2.5,
            boxShadow: `0 0 40px rgba(6,182,212,0.15)` }}>
            <RobotIcon sx={{ fontSize: 36, color: C.cyan }} />
          </Box>
          <Typography sx={{ fontSize: 32, fontWeight: 900, color: C.txt, letterSpacing: '-1.5px', lineHeight: 1, mb: 0.75 }}>
            PAIOS
          </Typography>
          <Typography sx={{ fontSize: '0.65rem', color: C.cyan, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 700, mb: 1 }}>
            Physical Agentic AI Operating System
          </Typography>
          <Typography sx={{ fontSize: '0.82rem', color: C.sub, lineHeight: 1.6 }}>
            Enterprise AI platform for manufacturing diagnostics
          </Typography>
        </Box>

        {/* Login card */}
        <Box sx={{ bgcolor: C.s1, border: `1px solid ${C.b1}`, borderRadius: 3, p: 3, mb: 2 }}>
          <Typography sx={{ color: C.txt, fontWeight: 700, fontSize: '0.9rem', mb: 2 }}>
            Sign in to your workspace
          </Typography>

          {/* Username */}
          <Box sx={{ mb: 1.5 }}>
            <Typography sx={{ color: C.sub, fontSize: '0.7rem', mb: 0.75, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Username
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1,
              bgcolor: C.s2, border: `1px solid ${C.b2}`, borderRadius: 2, px: 1.5, py: 1,
              '&:focus-within': { borderColor: C.cyan, boxShadow: `0 0 0 3px ${C.cyanG}` } }}>
              <PersonIcon sx={{ color: C.sub, fontSize: 18, flexShrink: 0 }} />
              <InputBase fullWidth value={username} onChange={e => setUsername(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleLogin()}
                placeholder="Enter username"
                sx={{ color: C.txt, fontSize: '0.9rem', '& input::placeholder': { color: C.sub, opacity: 1 } }} />
            </Box>
          </Box>

          {/* Password */}
          <Box sx={{ mb: 2 }}>
            <Typography sx={{ color: C.sub, fontSize: '0.7rem', mb: 0.75, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Password
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1,
              bgcolor: C.s2, border: `1px solid ${C.b2}`, borderRadius: 2, px: 1.5, py: 1,
              '&:focus-within': { borderColor: C.cyan, boxShadow: `0 0 0 3px ${C.cyanG}` } }}>
              <LockIcon sx={{ color: C.sub, fontSize: 18, flexShrink: 0 }} />
              <InputBase fullWidth value={password} onChange={e => setPassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleLogin()}
                type={showPass ? 'text' : 'password'}
                placeholder="Enter password"
                sx={{ color: C.txt, fontSize: '0.9rem', '& input::placeholder': { color: C.sub, opacity: 1 } }} />
              <IconButton size="small" onClick={() => setShowPass(!showPass)}
                sx={{ color: C.sub, '&:hover': { color: C.txt }, p: 0.5 }}>
                {showPass ? <EyeOffIcon sx={{ fontSize: 16 }} /> : <EyeIcon sx={{ fontSize: 16 }} />}
              </IconButton>
            </Box>
          </Box>

          {/* Error */}
          {error && (
            <Box sx={{ p: 1.25, mb: 1.5, bgcolor: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: 1.5 }}>
              <Typography sx={{ color: '#ef4444', fontSize: '0.78rem' }}>{error}</Typography>
            </Box>
          )}

          {/* Login button */}
          <Box onClick={() => handleLogin()}
            sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1,
              py: 1.25, borderRadius: 2, cursor: 'pointer',
              bgcolor: C.cyan, color: '#000', fontWeight: 700, fontSize: '0.9rem',
              transition: 'all 0.2s', '&:hover': { bgcolor: '#0891b2', transform: 'translateY(-1px)' } }}>
            {loading
              ? <CircularProgress size={18} sx={{ color: '#000' }} />
              : <><SparkleIcon sx={{ fontSize: 18 }} /> Sign in to PAIOS</>}
          </Box>
        </Box>

        {/* Quick login */}
        <Box sx={{ bgcolor: C.s1, border: `1px solid ${C.b1}`, borderRadius: 3, p: 2.5 }}>
          <Typography sx={{ color: C.sub, fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.08em', mb: 1.5 }}>
            Quick access — demo accounts
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {DEMO_CREDENTIALS.map(cred => (
              <Box key={cred.username} onClick={() => quickLogin(cred)} flex={1}
                sx={{ textAlign: 'center', py: 1, px: 1.5, borderRadius: 2, cursor: 'pointer',
                  bgcolor: C.s2, border: `1px solid ${C.b2}`,
                  '&:hover': { borderColor: C.cyan, bgcolor: C.cyanG } }}>
                <Typography sx={{ color: C.txt, fontWeight: 600, fontSize: '0.82rem' }}>{cred.label}</Typography>
                <Typography sx={{ color: C.sub, fontSize: '0.65rem' }}>{cred.username} / {cred.password}</Typography>
              </Box>
            ))}
          </Box>
        </Box>

        {/* Industry tags */}
        <Box sx={{ display: 'flex', gap: 1, mt: 2.5, justifyContent: 'center', flexWrap: 'wrap' }}>
          {['Aviation', 'Oil & Gas', 'Rail', 'Semiconductor', 'Industrial', 'Pharma'].map(tag => (
            <Chip key={tag} label={tag} size="small"
              sx={{ bgcolor: 'rgba(255,255,255,0.04)', color: C.sub, border: `1px solid ${C.b1}`, fontSize: 11 }} />
          ))}
        </Box>

        <Typography sx={{ textAlign: 'center', color: C.sub, fontSize: '0.65rem', mt: 2 }}>
          © 2026 PAIOS · Physical Agentic AI Operating System · MacvaarAI Inc.
        </Typography>
      </Box>
    </Box>
  );
};

export default Login;
