import { useState, useEffect } from 'react';
import { getSummary } from '../api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const Stat = ({ label, value, sub, accent }) => (
  <div style={{
    background: 'var(--surface)', border: '1px solid var(--border)',
    borderRadius: 8, padding: '20px 24px',
    borderTop: `2px solid ${accent || 'var(--border)'}`,
  }}>
    <div style={{ fontSize: 11, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>{label}</div>
    <div style={{ fontSize: 28, fontWeight: 600, fontFamily: 'var(--mono)', color: accent || 'var(--text)' }}>{value}</div>
    {sub && <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>{sub}</div>}
  </div>
);

const fmt = (n) => {
  if (n >= 1000000) return `${(n/1000000).toFixed(1)}M`;
  if (n >= 1000) return `${(n/1000).toFixed(1)}k`;
  return n.toFixed(0);
};

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getSummary().then(r => setData(r.data)).catch(() => setError('Failed to load summary'));
  }, []);

  if (error) return <div style={{ color: 'var(--red)', padding: 20 }}>{error}</div>;
  if (!data) return <div style={{ color: 'var(--text-dim)', padding: 20 }}>Loading…</div>;

  const scopeData = [1, 2, 3].map(s => ({
    name: `Scope ${s}`,
    co2e: Math.round(data.by_scope[`scope_${s}`]?.co2e_kg || 0),
    count: data.by_scope[`scope_${s}`]?.count || 0,
  }));

  const sourceData = [
    { name: 'SAP Fuel', co2e: Math.round(data.by_source.sap_fuel?.co2e_kg || 0), color: 'var(--green)' },
    { name: 'Electricity', co2e: Math.round(data.by_source.utility_electricity?.co2e_kg || 0), color: 'var(--blue)' },
    { name: 'Travel', co2e: Math.round(data.by_source.corporate_travel?.co2e_kg || 0), color: 'var(--amber)' },
  ];

  const pending = data.by_status.pending || 0;
  const flagged = data.by_status.flagged || 0;
  const approved = data.by_status.approved || 0;

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600 }}>Emissions Overview</h1>
        <p style={{ color: 'var(--text-dim)', fontSize: 13, marginTop: 4 }}>
          All scopes · All sources · Current period
        </p>
      </div>

      {/* Top stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 32 }}>
        <Stat
          label="Total CO₂e"
          value={`${fmt(data.total_co2e_kg)} kg`}
          sub={`${(data.total_co2e_kg/1000).toFixed(1)} tCO₂e`}
          accent="var(--green)"
        />
        <Stat label="Pending Review" value={pending} sub="awaiting analyst sign-off" accent="var(--text-dim)" />
        <Stat label="Flagged" value={flagged} sub="need attention" accent="var(--amber)" />
        <Stat label="Approved" value={approved} sub="ready for audit" accent="var(--blue)" />
      </div>

      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 32 }}>
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: 24 }}>
          <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: 1 }}>
            CO₂e by Scope (kg)
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={scopeData}>
              <XAxis dataKey="name" tick={{ fill: 'var(--text-dim)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-dim)', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={fmt} />
              <Tooltip
                contentStyle={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }}
                formatter={(v) => [`${fmt(v)} kg CO₂e`, 'Emissions']}
              />
              <Bar dataKey="co2e" fill="var(--green)" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: 24 }}>
          <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: 1 }}>
            CO₂e by Source (kg)
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={sourceData}>
              <XAxis dataKey="name" tick={{ fill: 'var(--text-dim)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-dim)', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={fmt} />
              <Tooltip
                contentStyle={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }}
                formatter={(v) => [`${fmt(v)} kg CO₂e`, 'Emissions']}
              />
              <Bar dataKey="co2e" radius={[4,4,0,0]}>
                {sourceData.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Scope breakdown table */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: 24 }}>
        <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: 1 }}>
          Scope Breakdown
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              {['Scope', 'Category', 'Records', 'kg CO₂e', 'tCO₂e'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '8px 12px', fontSize: 11,
                  color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              { scope: 1, label: 'Direct — Fuel combustion', color: 'var(--green)' },
              { scope: 2, label: 'Purchased electricity', color: 'var(--blue)' },
              { scope: 3, label: 'Value chain — Travel, procurement', color: 'var(--amber)' },
            ].map(({ scope, label, color }) => {
              const d = data.by_scope[`scope_${scope}`] || {};
              return (
                <tr key={scope} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '12px', fontFamily: 'var(--mono)', fontSize: 12 }}>
                    <span style={{ color, fontWeight: 600 }}>Scope {scope}</span>
                  </td>
                  <td style={{ padding: '12px', fontSize: 13, color: 'var(--text-dim)' }}>{label}</td>
                  <td style={{ padding: '12px', fontFamily: 'var(--mono)', fontSize: 12 }}>{d.count || 0}</td>
                  <td style={{ padding: '12px', fontFamily: 'var(--mono)', fontSize: 12 }}>{fmt(d.co2e_kg || 0)}</td>
                  <td style={{ padding: '12px', fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--text-dim)' }}>
                    {((d.co2e_kg || 0) / 1000).toFixed(2)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
