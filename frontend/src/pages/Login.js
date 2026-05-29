import { useState } from 'react';
import { login } from '../api';

export default function Login({ onLogin }) {
  const [creds, setCreds] = useState({ username: 'analyst', password: 'demo1234' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true); setError('');
    try {
      const { data } = await login(creds.username, creds.password);
      onLogin(data);
    } catch {
      setError('Invalid credentials');
    } finally { setLoading(false); }
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg)',
    }}>
      <div style={{
        width: 380, padding: 40,
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 12,
      }}>
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--green)', letterSpacing: 3 }}>BREATHE</div>
          <h1 style={{ fontSize: 24, fontWeight: 600, marginTop: 4 }}>ESG Data Platform</h1>
          <p style={{ color: 'var(--text-dim)', fontSize: 13, marginTop: 8 }}>
            Emissions ingestion & analyst review
          </p>
        </div>

        {['username', 'password'].map(field => (
          <div key={field} style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 11, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 1, display: 'block', marginBottom: 6 }}>
              {field}
            </label>
            <input
              type={field === 'password' ? 'password' : 'text'}
              value={creds[field]}
              onChange={e => setCreds({ ...creds, [field]: e.target.value })}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              style={{
                width: '100%', padding: '10px 12px',
                background: 'var(--surface2)', border: '1px solid var(--border)',
                borderRadius: 6, color: 'var(--text)', fontSize: 14,
                fontFamily: 'var(--mono)', outline: 'none',
              }}
            />
          </div>
        ))}

        {error && <div style={{ color: 'var(--red)', fontSize: 13, marginBottom: 12 }}>{error}</div>}

        <button onClick={handleSubmit} disabled={loading} style={{
          width: '100%', padding: '12px',
          background: 'var(--green)', color: '#000',
          border: 'none', borderRadius: 6, fontSize: 14, fontWeight: 600,
          cursor: loading ? 'not-allowed' : 'pointer',
        }}>
          {loading ? 'Signing in…' : 'Sign in'}
        </button>

        <div style={{ marginTop: 20, padding: 12, background: 'var(--surface2)', borderRadius: 6, fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>
          Demo: analyst / demo1234
        </div>
      </div>
    </div>
  );
}
