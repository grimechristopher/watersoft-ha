// Watersoft Cards v1.0
// Flow card + Salt card for Home Assistant

// ─── Watersoft Flow Card ──────────────────────────────────────────────────────
class WatersoftFlowCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    if (!config.entities) throw new Error('entities required');
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _val(id) {
    if (!id || !this._hass) return null;
    const s = this._hass.states[id];
    if (!s || s.state === 'unavailable' || s.state === 'unknown') return null;
    const n = parseFloat(s.state);
    return isNaN(n) ? s.state : n;
  }

  _render() {
    const e = this._config.entities;
    const dailyUse    = this._val(e.daily_use)     ?? 0;
    const saltLbs     = this._val(e.salt_lbs)      ?? 0;
    const saltPct     = this._val(e.salt_pct)      ?? 0;
    const capacity    = this._val(e.capacity)      ?? 0;
    const drainFlow   = this._val(e.drain_flow)    ?? 0;
    const regen       = this._val(e.regenerating)  === 'on';
    const rawFlow     = e.current_flow ? this._val(e.current_flow) : null;
    const flowDisplay = rawFlow !== null ? `${rawFlow} gal/min` : '--';
    const flowing     = rawFlow !== null && rawFlow > 0;

    const blue   = '#2196F3';
    const orange = '#FF9800';
    const fc     = regen ? orange : blue;
    const speed  = regen ? '2s' : '3s';

    const pipe = (active, color, spd) => `
      <div class="pipe" style="background:${color}22;">
        ${active ? `
          <div class="dot" style="background:${color};animation-duration:${spd}"></div>
          <div class="dot" style="background:${color};animation-duration:${spd};animation-delay:${parseFloat(spd)/3}s"></div>
          <div class="dot" style="background:${color};animation-duration:${spd};animation-delay:${parseFloat(spd)*2/3}s"></div>
        ` : ''}
      </div>`;

    this.shadowRoot.innerHTML = `
      <style>
        ha-card { overflow: hidden; }
        .wrap { padding: 16px; }
        .header {
          display: flex; justify-content: space-between;
          align-items: center; margin-bottom: 18px;
        }
        .title { font-size: 1rem; font-weight: 500; color: var(--primary-text-color); }
        .badge {
          font-size: .72rem; padding: 3px 10px; border-radius: 12px;
          font-weight: 500; color: #fff;
          background: ${regen ? orange : '#4CAF50'};
        }

        .flow { display: flex; align-items: flex-start; gap: 0; }
        .node { display: flex; flex-direction: column; align-items: center; gap: 5px; min-width: 66px; }
        .circle {
          width: 52px; height: 52px; border-radius: 50%;
          border: 2px solid ${fc};
          box-shadow: 0 0 10px ${fc}44;
          display: flex; align-items: center; justify-content: center;
          font-size: 22px;
          background: var(--ha-card-background, var(--card-background-color));
          flex-shrink: 0;
        }
        .circle.dim { border-color: var(--divider-color); box-shadow: none; }
        .node-name { font-size: .72rem; color: var(--secondary-text-color); text-align: center; line-height: 1.3; }
        .node-val  { font-size: .82rem; font-weight: 600; color: var(--primary-text-color); text-align: center; }

        .pipe {
          flex: 1; height: 2px; margin-top: 25px;
          position: relative; overflow: hidden; border-radius: 1px;
        }
        .dot {
          position: absolute; width: 7px; height: 7px; border-radius: 50%;
          top: -2.5px; left: -8px;
          animation: slide linear infinite;
        }
        @keyframes slide { to { left: 100%; } }

        .drain-wrap {
          display: flex; flex-direction: column; align-items: center;
          margin-top: 6px;
          ${regen ? '' : 'opacity:0; height:0; overflow:hidden; margin:0;'}
        }
        .v-pipe {
          width: 2px; height: 28px;
          background: ${orange}33;
          position: relative; overflow: hidden;
        }
        .v-dot {
          position: absolute; width: 7px; height: 7px; border-radius: 50%;
          background: ${orange}; left: -2.5px;
          animation: drop 1s linear infinite;
        }
        .v-dot:nth-child(2) { animation-delay: .33s; }
        .v-dot:nth-child(3) { animation-delay: .66s; }
        @keyframes drop { from { top: -8px; } to { top: 100%; } }
        .drain-circle {
          width: 40px; height: 40px; border-radius: 50%;
          border: 2px solid ${orange}; font-size: 18px;
          display: flex; align-items: center; justify-content: center;
          background: var(--ha-card-background, var(--card-background-color));
        }
        .drain-label { font-size: .7rem; color: var(--secondary-text-color); margin-top: 4px; }

        .divider { height: 1px; background: var(--divider-color); margin: 14px 0 12px; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 2px; }
        .stat { display: flex; flex-direction: column; align-items: center; gap: 2px; }
        .sv { font-size: .95rem; font-weight: 600; color: var(--primary-text-color); }
        .su { font-size: .65rem; font-weight: 400; }
        .sl { font-size: .65rem; color: var(--secondary-text-color); text-align: center; line-height: 1.3; }
      </style>
      <ha-card>
        <div class="wrap">
          <div class="header">
            <div class="title">💧 Water</div>
            <div class="badge">${regen ? '🔄 Regenerating' : '✅ In Service'}</div>
          </div>

          <div class="flow">
            <div class="node">
              <div class="circle">🏛️</div>
              <div class="node-name">Water<br>Main</div>
              ${rawFlow !== null ? `<div class="node-val">${flowDisplay}</div><div class="node-name">gal/min</div>` : ''}
            </div>

            ${pipe(flowing, fc, speed)}

            <div class="node">
              <div class="circle">⚙️</div>
              <div class="node-name">EC5</div>
              <div class="node-val">${saltLbs} lbs</div>
            </div>

            ${pipe(flowing && !regen, regen ? '#cccccc' : blue, speed)}

            <div class="node">
              <div class="circle ${regen ? 'dim' : ''}">🏠</div>
              <div class="node-name">Home</div>
              <div class="node-val">${dailyUse} gal</div>
              <div class="node-name">24h</div>
            </div>
          </div>

          <div class="drain-wrap">
            <div class="v-pipe">
              <div class="v-dot"></div>
              <div class="v-dot"></div>
              <div class="v-dot"></div>
            </div>
            <div class="drain-circle">🚿</div>
            <div class="drain-label">Drain · ${drainFlow} gal/min</div>
          </div>

          <div class="divider"></div>

          <div class="stats">
            <div class="stat">
              <div class="sv">${dailyUse}<span class="su"> gal</span></div>
              <div class="sl">Last<br>24h</div>
            </div>
            <div class="stat">
              <div class="sv">${saltLbs}<span class="su"> lbs</span></div>
              <div class="sl">Salt<br>Level</div>
            </div>
            <div class="stat">
              <div class="sv">${saltPct}<span class="su">%</span></div>
              <div class="sl">Salt<br>Full</div>
            </div>
            <div class="stat">
              <div class="sv">${capacity}<span class="su">%</span></div>
              <div class="sl">Soft<br>Capacity</div>
            </div>
          </div>
        </div>
      </ha-card>
    `;
  }

  getCardSize() { return 4; }
}
customElements.define('watersoft-flow-card', WatersoftFlowCard);


// ─── Watersoft Salt Card ──────────────────────────────────────────────────────
class WatersoftSaltCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _val(id) {
    if (!id || !this._hass) return null;
    const s = this._hass.states[id];
    if (!s || s.state === 'unavailable' || s.state === 'unknown') return null;
    const n = parseFloat(s.state);
    return isNaN(n) ? null : n;
  }

  _render() {
    const e   = this._config.entities;
    const lbs = this._val(e.salt_lbs) ?? 0;
    const pct = this._val(e.salt_pct) ?? 0;
    const max = this._config.max_lbs  ?? 250;

    const saltColor = pct >= 40 ? '#2ecc71' : pct >= 20 ? '#f39c12' : '#e74c3c';
    const saltLabel = pct >= 40 ? '✅ Good' : pct >= 20 ? '⚠️ Getting Low' : '🚨 Refill Now';
    const segColors = ['#e74c3c', '#e67e22', '#f39c12', '#27ae60', '#2ecc71'];
    const segW = 100 / 5;

    const segmentHtml = segColors.map((c, i) => {
      const segStart = i * segW;
      const segEnd   = segStart + segW;
      let fill;
      if (pct >= segEnd)      fill = 100;
      else if (pct <= segStart) fill = 0;
      else fill = ((pct - segStart) / segW) * 100;

      return `<div class="seg" style="${i < 4 ? 'border-right:2px solid var(--ha-card-background,#fff)' : ''}">
        <div class="seg-fill" style="width:${fill}%;background:${c}"></div>
      </div>`;
    }).join('');

    this.shadowRoot.innerHTML = `
      <style>
        ha-card { overflow: hidden; }
        .wrap { padding: 16px; }
        .header {
          display: flex; justify-content: space-between;
          align-items: baseline; margin-bottom: 14px;
        }
        .title { font-size: 1rem; font-weight: 500; color: var(--primary-text-color); }
        .salt-badge {
          font-size: .72rem; padding: 3px 10px; border-radius: 12px;
          font-weight: 500; color: #fff; background: ${saltColor};
        }
        .lbs-value { font-size: 1.5rem; font-weight: 600; color: ${saltColor}; }
        .lbs-unit  { font-size: .85rem; font-weight: 400; color: var(--secondary-text-color); }
        .pct-value { font-size: .85rem; color: var(--secondary-text-color); }

        .bar-outer {
          display: flex; height: 28px; border-radius: 6px;
          overflow: hidden; background: var(--divider-color);
          margin-bottom: 8px;
        }
        .seg { flex: 1; position: relative; overflow: hidden; }
        .seg-fill {
          position: absolute; top: 0; left: 0; height: 100%;
          transition: width .6s ease;
        }

        .ticks {
          display: flex; justify-content: space-between; padding: 0;
        }
        .tick { font-size: .65rem; color: var(--secondary-text-color); }

        .warning {
          margin-top: 10px; padding: 6px 10px; border-radius: 6px;
          background: #e74c3c22; color: #e74c3c;
          font-size: .8rem; font-weight: 500;
          ${pct >= 20 ? 'display:none' : ''}
        }
      </style>
      <ha-card>
        <div class="wrap">
          <div class="header">
            <div class="title">🧂 Salt Level</div>
            <div class="salt-badge">${saltLabel}</div>
          </div>
          <div style="margin-bottom:12px">
            <span class="lbs-value">${lbs}</span>
            <span class="lbs-unit"> lbs</span>
            <span class="pct-value"> · ${pct}%</span>
          </div>

          <div class="bar-outer">${segmentHtml}</div>

          <div class="ticks">
            <span class="tick">0</span>
            <span class="tick">${Math.round(max * 0.25)} lbs</span>
            <span class="tick">${Math.round(max * 0.5)} lbs</span>
            <span class="tick">${Math.round(max * 0.75)} lbs</span>
            <span class="tick">${max} lbs</span>
          </div>

          <div class="warning">⚠️ Salt low — refill soon</div>
        </div>
      </ha-card>
    `;
  }

  getCardSize() { return 2; }
}
customElements.define('watersoft-salt-card', WatersoftSaltCard);


window.customCards = window.customCards || [];
window.customCards.push(
  { type: 'watersoft-flow-card', name: 'Watersoft Flow', description: 'Water softener flow visualization' },
  { type: 'watersoft-salt-card', name: 'Watersoft Salt', description: '5-segment salt level bar' }
);
