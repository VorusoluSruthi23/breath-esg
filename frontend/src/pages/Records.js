import { useState, useEffect, useCallback } from 'react';
import { getRecords, approveRecord, rejectRecord, flagRecord, bulkApprove, getAuditLog } from '../api';

const STATUS_COLORS = {
  pending: 'var(--text-dim)',
  flagged: 'var(--amber)',
  approved: 'var(--green)',
  locked: 'var(--blue)',
  rejected: 'var(--red)',
};

const Badge = ({ status }) => (
  <span style={{
    fontSize: 10, padding: '3px 8px', borderRadius: 99, fontWeight: 600,
    textTransform: 'uppercase', letterSpacing: 0.5, fontFamily: 'var(--mono)',
    color: STATUS_COLORS[status] || 'var(--text-dim)',
    background: `${STATUS_COLORS[status]}18` || 'var(--surface2)',
    border: `1px solid ${STATUS_COLORS[status]}33`,
  }}>{status}</span>
);

const fmt = (n) => Number(n).toLocaleString('en-US', { maximumFractionDigits: 1 });

export default function Records({ tenant }) {
  const [records, setRecords] = useState([]);
  const [filters, setFilters] = useState({ status: '', scope: '', source_type: '' });
  const [selected, setSelected] = useState(new Set());
  const [detail, setDetail] = useState(null);
  const [auditLog, setAuditLog] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    getRecords(filters).then(r => setRecords(r.data.results || r.data)).finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  const openDetail = async (rec) => {
    setDetail(rec);
    const { data } = await getAuditLog(rec.id);
    setAuditLog(data);
  };

  const doAction = async (fn, ...args) => {
    await fn(...args);
    load();
    if (detail) {
      const { data } = await getAuditLog(detail.id);
      setAuditLog(data);
    }
  };

  const toggleSelect = (id) => {
    const s = new Set(selected);
    s.has(id) ? s.delete(id) : s.add(id);
    setSelected(s);
  };

  const selectAll = () => {
    if (selected.size === records.length) setSelected(new Set());
    else setSelected(new Set(records.map(r => r.id)));
  };

  const FilterBtn = ({ field, value, label }) => (
    <button onClick={() => setFilters(f => ({ ...f, [field]: f[field] === value ? '' : value }))} style={{
      all: 'unset', cursor: 'pointer', fontSize: 11, padding: '4px 10px', borderRadius: 4,
      color: filters[field] === value ? 'var(--green)' : 'var(--text-dim)',
      background: filters[field] === value ? 'var(--green-muted)' : 'transparent',
      border: `1px solid ${filters[field] === value ? 'var(--green)' : 'var(--border)'}`,
      transition: 'all 0.15s',
    }}>{label}</button>
  );

  return (
    <div style={{ display: 'flex', gap: 24 }}>
      <div style={{ flex: 1 }}>
        <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 600 }}>Review Queue</h1>
            <p style={{ color: 'var(--text-dim)', fontSize: 13, marginTop: 4 }}>{records.length} records</p>
          </div>
          {selected.size > 0 && (
            <button onClick={async () => { await bulkApprove([...selected]); setSelected(new Set()); load(); }} style={{
              all: 'unset', cursor: 'pointer', padding: '8px 16px', background: 'var(--green)',
              color: '#000', borderRadius: 6, fontSize: 13, fontWeight: 600,
            }}>
              Approve {selected.size} selected
            </button>
          )}
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          <FilterBtn field="status" value="pending" label="Pending" />
          <FilterBtn field="status" value="flagged" label="Flagged" />
          <FilterBtn field="status" value="approved" label="Approved" />
          <div style={{ width: 1, background: 'var(--border)', margin: '0 4px' }} />
          <FilterBtn field="scope" value="1" label="Scope 1" />
          <FilterBtn field="scope" value="2" label="Scope 2" />
          <FilterBtn field="scope" value="3" label="Scope 3" />
          <div style={{ width: 1, background: 'var(--border)', margin: '0 4px' }} />
          <FilterBtn field="source_type" value="sap_fuel" label="SAP" />
          <FilterBtn field="source_type" value="utility_electricity" label="Utility" />
          <FilterBtn field="source_type" value="corporate_travel" label="Travel" />
        </div>

        {/* Table */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface2)' }}>
                <th style={{ padding: '10px 12px', width: 36 }}>
                  <input type="checkbox" checked={selected.size === records.length && records.length > 0}
                    onChange={selectAll} style={{ cursor: 'pointer', accentColor: 'var(--green)' }} />
                </th>
                {['Scope', 'Category', 'Period', 'Activity', 'CO₂e (kg)', 'Source', 'Status', ''].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '10px 12px', fontSize: 10,
                    color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={9} style={{ padding: 40, textAlign: 'center', color: 'var(--text-dim)' }}>Loading…</td></tr>
              ) : records.length === 0 ? (
                <tr><td colSpan={9} style={{ padding: 40, textAlign: 'center', color: 'var(--text-dim)' }}>No records match filters</td></tr>
              ) : records.map(r => (
                <tr key={r.id} onClick={() => openDetail(r)} style={{
                  borderBottom: '1px solid var(--border)', cursor: 'pointer',
                  background: detail?.id === r.id ? 'var(--green-muted)' : 'transparent',
                  transition: 'background 0.1s',
                }}>
                  <td style={{ padding: '10px 12px' }} onClick={e => { e.stopPropagation(); toggleSelect(r.id); }}>
                    <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggleSelect(r.id)}
                      style={{ cursor: 'pointer', accentColor: 'var(--green)' }} />
                  </td>
                  <td style={{ padding: '10px 12px', fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600 }}>
                    S{r.scope}
                  </td>
                  <td style={{ padding: '10px 12px', fontSize: 12, color: 'var(--text-dim)', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {r.category?.replace(/_/g, ' ')}
                  </td>
                  <td style={{ padding: '10px 12px', fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text-dim)' }}>
                    {r.period_start}
                  </td>
                  <td style={{ padding: '10px 12px', fontSize: 12, maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {fmt(r.activity_value)} {r.activity_unit}
                  </td>
                  <td style={{ padding: '10px 12px', fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color: 'var(--green)' }}>
                    {fmt(r.co2e_kg)}
                  </td>
                  <td style={{ padding: '10px 12px', fontSize: 11, color: 'var(--text-dim)' }}>
                    {r.source_type?.replace(/_/g, ' ')}
                  </td>
                  <td style={{ padding: '10px 12px' }}><Badge status={r.status} /></td>
                  <td style={{ padding: '10px 12px' }}>
                    {r.flag_reason && (
                      <span title={r.flag_reason} style={{ color: 'var(--amber)', fontSize: 14 }}>⚠</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail panel */}
      {detail && (
        <div style={{
          width: 340, background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 8, padding: 24, position: 'sticky', top: 0, maxHeight: '90vh', overflowY: 'auto',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
            <div>
              <Badge status={detail.status} />
              {detail.is_manually_edited && (
                <span style={{ fontSize: 10, color: 'var(--amber)', marginLeft: 6, fontFamily: 'var(--mono)' }}>EDITED</span>
              )}
            </div>
            <button onClick={() => setDetail(null)} style={{ all: 'unset', cursor: 'pointer', color: 'var(--text-dim)', fontSize: 18 }}>×</button>
          </div>

          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4 }}>EMISSION RECORD</div>
          <div style={{ fontSize: 24, fontWeight: 600, fontFamily: 'var(--mono)', color: 'var(--green)', marginBottom: 4 }}>
            {fmt(detail.co2e_kg)} kg
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 20 }}>CO₂e — Scope {detail.scope}</div>

          {detail.flag_reason && (
            <div style={{ background: 'var(--amber-muted)', border: '1px solid var(--amber)33', borderRadius: 6, padding: 12, marginBottom: 16 }}>
              <div style={{ fontSize: 10, color: 'var(--amber)', fontWeight: 600, marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>Auto-flagged</div>
              <div style={{ fontSize: 12, color: 'var(--text)' }}>{detail.flag_reason}</div>
            </div>
          )}

          {[
            ['Category', detail.category?.replace(/_/g, ' ')],
            ['Period', `${detail.period_start} → ${detail.period_end}`],
            ['Activity', `${fmt(detail.activity_value)} ${detail.activity_unit}`],
            ['Location', detail.facility_or_location || '—'],
            ['Source', detail.source_type?.replace(/_/g, ' ')],
            ['EF Used', detail.emission_factor_used ? `${detail.emission_factor_used} kg CO₂e/${detail.activity_unit}` : '—'],
            ['EF Source', detail.emission_factor_source || '—'],
          ].map(([k, v]) => (
            <div key={k} style={{ display: 'flex', gap: 8, marginBottom: 10, fontSize: 12 }}>
              <span style={{ color: 'var(--text-dim)', flexShrink: 0, width: 80 }}>{k}</span>
              <span style={{ color: 'var(--text)', wordBreak: 'break-word' }}>{v}</span>
            </div>
          ))}

          {/* Action buttons */}
          {detail.status !== 'locked' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 20 }}>
              <button onClick={() => doAction(() => approveRecord(detail.id))} style={{
                all: 'unset', cursor: 'pointer', padding: '8px', textAlign: 'center',
                background: 'var(--green)', color: '#000', borderRadius: 6, fontSize: 12, fontWeight: 600,
              }}>Approve</button>
              <button onClick={() => { const r = prompt('Reason for rejection?'); if (r) doAction(() => rejectRecord(detail.id, r)); }} style={{
                all: 'unset', cursor: 'pointer', padding: '8px', textAlign: 'center',
                background: 'var(--red-muted)', color: 'var(--red)', borderRadius: 6, fontSize: 12,
                border: '1px solid var(--red)33',
              }}>Reject</button>
              <button onClick={() => { const r = prompt('Flag reason?'); if (r) doAction(() => flagRecord(detail.id, r)); }} style={{
                all: 'unset', cursor: 'pointer', padding: '8px', textAlign: 'center',
                background: 'var(--amber-muted)', color: 'var(--amber)', borderRadius: 6, fontSize: 12,
                border: '1px solid var(--amber)33', gridColumn: 'span 2',
              }}>Flag for review</button>
            </div>
          )}

          {/* Audit log */}
          {auditLog.length > 0 && (
            <div style={{ marginTop: 24, borderTop: '1px solid var(--border)', paddingTop: 16 }}>
              <div style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
                Audit Trail
              </div>
              {auditLog.map(log => (
                <div key={log.id} style={{ marginBottom: 10, fontSize: 11 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--green)', fontFamily: 'var(--mono)', fontWeight: 600 }}>{log.action}</span>
                    <span style={{ color: 'var(--text-faint)', fontFamily: 'var(--mono)' }}>
                      {new Date(log.timestamp).toLocaleDateString()}
                    </span>
                  </div>
                  <div style={{ color: 'var(--text-dim)' }}>{log.user_name} {log.notes && `— ${log.notes}`}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
