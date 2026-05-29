import { useState, useEffect } from 'react';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Records from './pages/Records';
import Ingest from './pages/Ingest';
import './index.css';

const NAV = [
  { id: 'dashboard', label: 'Overview' },
  { id: 'records', label: 'Review Queue' },
  { id: 'ingest', label: 'Ingest Data' },
];

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(JSON.parse(localStorage.getItem('user') || 'null'));
  const [page, setPage] = useState('dashboard');

  const handleLogin = (data) => {
    localStorage.setItem('token', data.token);
    localStorage.setItem('user', JSON.stringify({ username: data.username, tenant: data.tenant }));
    setToken(data.token);
    setUser({ username: data.username, tenant: data.tenant });
  };

  const handleLogout = () => {
    localStorage.clear();
    setToken(null);
    setUser(null);
  };

  if (!token) return <Login onLogin={handleLogin} />;

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <nav style={{
        width: 220, background: 'var(--surface)', borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', padding: '24px 0',
        position: 'fixed', top: 0, left: 0, height: '100vh', zIndex: 100,
      }}>
        <div style={{ padding: '0 20px 32px' }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--green)', letterSpacing: 3, marginBottom: 4 }}>
            BREATHE
          </div>
          <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--text)' }}>ESG</div>
          {user?.tenant && (
            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 8,
              background: 'var(--green-muted)', border: '1px solid var(--border)',
              padding: '4px 8px', borderRadius: 4, fontFamily: 'var(--mono)' }}>
              {user.tenant.name}
            </div>
          )}
        </div>

        {NAV.map(n => (
          <button key={n.id} onClick={() => setPage(n.id)} style={{
            all: 'unset', cursor: 'pointer', padding: '12px 20px',
            fontSize: 14, fontWeight: 500,
            color: page === n.id ? 'var(--green)' : 'var(--text-dim)',
            background: page === n.id ? 'var(--green-muted)' : 'transparent',
            borderLeft: page === n.id ? '2px solid var(--green)' : '2px solid transparent',
            transition: 'all 0.15s',
          }}>
            {n.label}
          </button>
        ))}

        <div style={{ marginTop: 'auto', padding: '20px', borderTop: '1px solid var(--border)' }}>
          <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 8 }}>
            {user?.username}
          </div>
          <button onClick={handleLogout} style={{
            all: 'unset', cursor: 'pointer', fontSize: 12, color: 'var(--red)',
          }}>Sign out</button>
        </div>
      </nav>

      {/* Main content */}
      <main style={{ marginLeft: 220, flex: 1, padding: '32px', minHeight: '100vh' }}>
        {page === 'dashboard' && <Dashboard />}
        {page === 'records' && <Records tenant={user?.tenant?.slug} />}
        {page === 'ingest' && <Ingest tenant={user?.tenant?.slug} />}
      </main>
    </div>
  );
}
