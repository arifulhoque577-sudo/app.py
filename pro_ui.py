"""
pro_ui.py  -  Pro terminal-style UI layer (Streamlit).

Eta SHUDHU design. Trading logic, Firebase, engine - kichu chhuy na.
Sob number tomar app er asol variable theke ashe (kono fake/hardcoded stat nai).

Use:
    import pro_ui
    pro_ui.inject(st)                       # ekbar, CSS er por
    st.markdown(pro_ui.hero(...), unsafe_allow_html=True)
    st.markdown(pro_ui.pipeline([...]), unsafe_allow_html=True)
    st.plotly_chart(pro_ui.pro_chart(df, ...), use_container_width=True)
"""
import html as _html
import re
import time

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except Exception:          # plotly na thakle chart function kaj korbe na, baki thik
    go = None

GREEN, RED, CYAN, VIOLET, AMBER = "#22f2a0", "#ff4d6d", "#38bdf8", "#a78bfa", "#f5a623"


def _m(s):
    """HTML minify: Streamlit markdown e indent thakle code-block hoye jay, tai sob newline/indent bad."""
    return re.sub(r">\s+<", "><", re.sub(r"\n\s*", "", s)).strip()


def _e(x):
    return _html.escape(str(x))


def _sign(v):
    return "pos" if v > 0 else ("neg" if v < 0 else "flat")


def _money(v, d=2):
    return f"{'-' if v < 0 else ''}${abs(v):,.{d}f}"


# ------------------------------------------------------------------ CSS
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&family=Space+Grotesk:wght@500;700&display=swap');
:root{--pz-bg:#070b13;--pz-panel:#0b1220;--pz-line:#16233a;--pz-txt:#dbe7f5;--pz-mut:#6b819f;
--pz-g:#22f2a0;--pz-r:#ff4d6d;--pz-c:#38bdf8;--pz-v:#a78bfa;--pz-a:#f5a623;}
.block-container{padding-top:1.2rem !important;max-width:1180px !important;}
.pz-mono{font-family:'JetBrains Mono',ui-monospace,Menlo,Consolas,monospace;}
.pz-win{background:linear-gradient(180deg,#0b1220,#080d18);border:1px solid var(--pz-line);border-radius:16px;
 padding:16px 18px;margin:0 0 14px;box-shadow:0 0 0 1px rgba(56,189,248,.04),0 20px 50px -25px rgba(0,0,0,.8);}
.pz-chrome{display:flex;align-items:center;gap:7px;margin-bottom:12px;font:600 11px 'JetBrains Mono',monospace;color:var(--pz-mut);}
.pz-dot{width:10px;height:10px;border-radius:50%;display:inline-block}
.pz-chrome .t{flex:1;text-align:center;letter-spacing:.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pz-pill{border:1px solid var(--pz-line);border-radius:999px;padding:2px 10px;font:700 10px 'JetBrains Mono',monospace;letter-spacing:.8px}
.pz-pill.live{color:var(--pz-g);border-color:rgba(34,242,160,.4);background:rgba(34,242,160,.07)}
.pz-pill.demo{color:var(--pz-c);border-color:rgba(56,189,248,.4);background:rgba(56,189,248,.07)}
.pz-pill.off{color:var(--pz-mut)}
.pz-hero{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.pz-orb{width:62px;height:62px;border-radius:50%;flex:none;position:relative;
 background:radial-gradient(circle at 32% 28%,#e9d5ff 0%,#a78bfa 38%,#4c1d95 100%);
 box-shadow:0 0 30px rgba(167,139,250,.55),inset 0 0 14px rgba(255,255,255,.25)}
.pz-orb.run{animation:pzpulse 2.2s ease-in-out infinite}
.pz-orb.off{filter:grayscale(.85) brightness(.6);box-shadow:none}
.pz-orb:after{content:"";position:absolute;inset:-7px;border-radius:50%;border:1px solid rgba(167,139,250,.35)}
.pz-orb.run:after{animation:pzring 2.2s ease-out infinite}
@keyframes pzpulse{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}}
@keyframes pzring{0%{transform:scale(.9);opacity:.9}100%{transform:scale(1.35);opacity:0}}
.pz-title{font:700 26px 'Space Grotesk',sans-serif;color:#fff;line-height:1.1}
.pz-title b{color:var(--pz-c)}
.pz-sub{font:400 12px 'JetBrains Mono',monospace;color:var(--pz-mut);margin-top:5px}
.pz-sub i{font-style:normal;color:var(--pz-g)}
.pz-bal{margin-left:auto;text-align:right}
.pz-bal .n{font:800 40px 'JetBrains Mono',monospace;color:#fff;letter-spacing:-1px;line-height:1}
.pz-bal .l{font:400 11px 'JetBrains Mono',monospace;color:var(--pz-mut);margin-top:6px}
.pos{color:var(--pz-g)!important}.neg{color:var(--pz-r)!important}.flat{color:var(--pz-mut)!important}
/* pipeline */
.pz-flow{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;position:relative}
.pz-node{text-align:center;position:relative;padding:6px 2px}
.pz-node:not(:last-child):after{content:"";position:absolute;top:30px;left:calc(50% + 28px);width:calc(100% - 56px);
 border-top:1px dashed #243553}
.pz-node.ok:not(:last-child):after,.pz-node.active:not(:last-child):after{border-top-color:rgba(34,242,160,.55)}
.pz-ring{width:52px;height:52px;border-radius:50%;margin:0 auto 7px;display:flex;align-items:center;justify-content:center;
 font-size:20px;border:2px solid #243553;background:#0a1322;color:var(--pz-mut)}
.pz-node.ok .pz-ring{border-color:var(--pz-g);color:var(--pz-g);box-shadow:0 0 14px rgba(34,242,160,.25)}
.pz-node.active .pz-ring{border-color:var(--pz-c);color:var(--pz-c);box-shadow:0 0 18px rgba(56,189,248,.45);animation:pzpulse 1.4s infinite}
.pz-node.warn .pz-ring{border-color:var(--pz-a);color:var(--pz-a);box-shadow:0 0 14px rgba(245,166,35,.3)}
.pz-node.bad .pz-ring{border-color:var(--pz-r);color:var(--pz-r)}
.pz-node .nm{font:800 10px 'JetBrains Mono',monospace;letter-spacing:1px;color:var(--pz-c)}
.pz-node .mt{font:400 10px 'JetBrains Mono',monospace;color:var(--pz-mut);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* kpis */
.pz-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:0 0 14px}
.pz-kpi{background:var(--pz-panel);border:1px solid var(--pz-line);border-radius:12px;padding:12px 14px;position:relative;overflow:hidden}
.pz-kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--acc,#243553)}
.pz-kpi .k{font:600 10px 'JetBrains Mono',monospace;color:var(--pz-mut);letter-spacing:1px;text-transform:uppercase}
.pz-kpi .v{font:800 22px 'JetBrains Mono',monospace;color:#fff;margin-top:6px;white-space:nowrap}
.pz-kpi .s{font:400 10px 'JetBrains Mono',monospace;color:var(--pz-mut);margin-top:4px}
/* position */
.pz-pos .hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.pz-pos .sym{font:800 24px 'Space Grotesk',sans-serif;color:#fff}
.pz-pos .pnl{margin-left:auto;font:800 30px 'JetBrains Mono',monospace}
.pz-tag{font:800 10px 'JetBrains Mono',monospace;border-radius:6px;padding:3px 8px;letter-spacing:1px}
.pz-tag.long{background:rgba(34,242,160,.12);color:var(--pz-g);border:1px solid rgba(34,242,160,.4)}
.pz-tag.short{background:rgba(255,77,109,.12);color:var(--pz-r);border:1px solid rgba(255,77,109,.4)}
.pz-tag.flat{background:rgba(107,129,159,.12);border:1px solid var(--pz-line)}
.pz-rail{position:relative;height:8px;border-radius:6px;margin:34px 46px 34px;
 background:linear-gradient(90deg,rgba(255,77,109,.55),#1b2a44 50%,rgba(34,242,160,.55))}
.pz-mark{position:absolute;top:-5px;width:2px;height:18px;background:#fff;border-radius:2px}
.pz-mark span{position:absolute;white-space:nowrap;font:700 9px 'JetBrains Mono',monospace;left:50%;transform:translateX(-50%)}
.pz-mark.top span{top:-16px}.pz-mark.bot span{top:22px}
.pz-cur{position:absolute;top:-7px;width:14px;height:22px;border-radius:5px;background:var(--pz-c);
 box-shadow:0 0 12px var(--pz-c);transform:translateX(-50%)}
.pz-grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;font:400 11px 'JetBrains Mono',monospace;color:var(--pz-mut)}
.pz-grid3 b{display:block;color:#fff;font-size:14px;margin:2px 0 6px}
/* terminal */
.pz-term{background:#04070d;border:1px solid var(--pz-line);border-radius:12px;padding:12px 14px;
 font:400 12px/1.75 'JetBrains Mono',monospace;max-height:230px;overflow:auto}
.pz-term div{white-space:pre-wrap;word-break:break-word}
.pz-term .ts{color:#41567a}.pz-term .w{color:var(--pz-g);font-weight:800}.pz-term .l{color:var(--pz-r);font-weight:800}
.pz-term .i{color:var(--pz-c)}.pz-term .a{color:var(--pz-a)}.pz-term .p{color:var(--pz-v)}.pz-term .x{color:#9db0cc}
.pz-term .cur:after{content:"\\2588";color:var(--pz-g);animation:pzblink 1s steps(2) infinite;margin-left:3px}
@keyframes pzblink{50%{opacity:0}}
.pz-h{font:800 11px 'JetBrains Mono',monospace;letter-spacing:1.5px;color:var(--pz-mut);margin:0 0 10px;display:flex;justify-content:space-between}
.pz-h b{color:var(--pz-c)}
.pz-bar{height:6px;border-radius:5px;background:#12203a;overflow:hidden}.pz-bar i{display:block;height:100%}
.pz-wl{display:flex;gap:6px;margin-top:6px}
@media(max-width:720px){.pz-flow{grid-template-columns:repeat(3,1fr);row-gap:14px}.pz-node:after{display:none}
 .pz-bal{margin-left:0;text-align:left;width:100%}.pz-bal .n{font-size:34px}.pz-pos .pnl{margin-left:0}}
</style>
"""


def inject(st):
    st.markdown(_m(_CSS), unsafe_allow_html=True)


# ----------------------------------------------------------------- hero
def hero(balance, mode, exchange, symbol, running, uptime_s=0, wins=0, losses=0, session_pnl=0.0, stage="IDLE"):
    """mode: 'REAL' | 'DEMO'"""
    h, r = divmod(int(max(uptime_s, 0)), 3600)
    mn, s = divmod(r, 60)
    live = mode.upper() == "REAL"
    state = "run" if running else "off"
    return _m(f"""
    <div class="pz-win">
      <div class="pz-chrome">
        <span class="pz-dot" style="background:#ff5f56"></span><span class="pz-dot" style="background:#ffbd2e"></span><span class="pz-dot" style="background:#27c93f"></span>
        <span class="t">scalper-bot &middot; {_e(exchange)} &middot; {_e(symbol)} &middot; ai swarm</span>
        <span class="pz-pill {'live' if live else 'demo'}">{'REAL &bull; LIVE' if live else 'DEMO &bull; PAPER'}</span>
      </div>
      <div class="pz-hero">
        <div class="pz-orb {state}"></div>
        <div>
          <div class="pz-title">AI Scalper <b>Terminal</b></div>
          <div class="pz-sub"><i>{'&#9679; running' if running else '&#9675; stopped'}</i> &middot; {h:02d}:{mn:02d}:{s:02d} &middot; stage: {_e(stage)}</div>
        </div>
        <div class="pz-bal">
          <div class="n">{_money(balance)}</div>
          <div class="l">balance &middot; {wins + losses} trades &middot; <span class="pos">{wins} W</span> &middot; <span class="neg">{losses} L</span> &middot; session <span class="{_sign(session_pnl)}">{_money(session_pnl)}</span></div>
        </div>
      </div>
    </div>""")


# -------------------------------------------------------------- pipeline
_ICONS = {"feed": "&#128225;", "signal": "&#128200;", "ai": "&#129504;", "exec": "&#9889;", "risk": "&#128737;", "log": "&#128221;"}


def pipeline(stages):
    """stages: list of (key, NAME, state, metric). state: ok|active|warn|bad|idle"""
    out = []
    for key, name, state, metric in stages:
        out.append(f'<div class="pz-node {state}"><div class="pz-ring">{_ICONS.get(key, "&#9679;")}</div>'
                   f'<div class="nm">{_e(name)}</div><div class="mt">{_e(metric)}</div></div>')
    return _m(f'<div class="pz-win"><div class="pz-h"><span>LIVE FLOW &middot; <b>HARD HANDOFFS</b></span><span>one job each</span></div>'
              f'<div class="pz-flow">{"".join(out)}</div></div>')


# ------------------------------------------------------------------ kpis
def kpis(items):
    """items: list of (label, value_str, sub_str, accent_hex, css_class_for_value)"""
    cells = []
    for lab, val, sub, acc, cls in items:
        cells.append(f'<div class="pz-kpi" style="--acc:{acc}"><div class="k">{_e(lab)}</div>'
                     f'<div class="v {cls}">{_e(val)}</div><div class="s">{_e(sub)}</div></div>')
    return _m(f'<div class="pz-kpis">{"".join(cells)}</div>')


# -------------------------------------------------------------- position
def position_card(symbol, in_pos, side, entry, price, tp_gap, sl_gap, pnl, notional, lev, dec=4):
    if not in_pos or entry <= 0:
        return _m(f"""<div class="pz-win pz-pos"><div class="hd"><span class="sym">{_e(symbol)}</span>
          <span class="pz-tag flat">NO POSITION</span><span class="pnl flat">$0.00</span></div>
          <div class="pz-sub" style="margin-top:8px">stop-loss ar take-profit exchange e boshe tarpor-i entry hoy &middot; TP gap {tp_gap:g} &middot; SL gap {sl_gap:g} &middot; {lev}x</div></div>""")
    is_long = "LONG" in str(side).upper()
    sgn = 1 if is_long else -1
    tp, sl = entry + sgn * tp_gap, entry - sgn * sl_gap
    lo, hi = min(tp, sl), max(tp, sl)
    span = (hi - lo) or 1.0
    pos = lambda p: max(0.0, min(100.0, (p - lo) / span * 100))
    ep, cp = pos(entry), pos(price)
    tp_p, sl_p = pos(tp), pos(sl)
    cls = _sign(pnl)
    return _m(f"""
    <div class="pz-win pz-pos">
      <div class="hd"><span class="sym">{_e(symbol)}</span><span class="pz-tag {'long' if is_long else 'short'}">{'LONG' if is_long else 'SHORT'} &middot; {lev}x</span>
        <span class="pz-tag flat">OPEN &middot; STOP ARMED</span><span class="pnl {cls}">{'+' if pnl > 0 else ''}{_money(pnl)}</span></div>
      <div class="pz-rail">
        <div class="pz-mark top" style="left:{sl_p:.1f}%;background:var(--pz-r)"><span class="neg">SL {sl:.{dec}f}</span></div>
        <div class="pz-mark top" style="left:{tp_p:.1f}%;background:var(--pz-g)"><span class="pos">TP {tp:.{dec}f}</span></div>
        <div class="pz-mark bot" style="left:{ep:.1f}%"><span style="color:#dbe7f5">entry {entry:.{dec}f}</span></div>
        <div class="pz-cur" style="left:{cp:.1f}%"></div>
      </div>
      <div class="pz-grid3"><div>size<b>{_money(notional, 0)}</b></div><div>live<b>{price:.{dec}f}</b></div>
        <div>to TP / SL<b><span class="pos">{abs(tp - price):.{dec}f}</span> / <span class="neg">{abs(price - sl):.{dec}f}</span></b></div></div>
    </div>""")


# -------------------------------------------------------------- terminal
def terminal(lines, title="tail -f engine.log", n=14):
    rows = []
    for ln in list(lines)[-n:]:
        t = str(ln)
        m = re.match(r"^\[(\d\d:\d\d:\d\d)\]\s*(.*)$", t)
        ts, body = (m.group(1), m.group(2)) if m else ("", t)
        low = body.lower()
        if "closed" in low:
            mm = re.search(r"p&l:\s*([+-]?\d+(?:\.\d+)?)", low)
            win = (float(mm.group(1)) >= 0) if mm else True
            tag, cls = ("WIN ", "w") if win else ("LOSS", "l")
        elif "order opened" in low:
            tag, cls = "OPEN", "i"
        elif "blocked" in low or "error" in low or "unavailable" in low or "failed" in low:
            tag, cls = "WARN", "a"
        elif "signal" in low or "ai" in low:
            tag, cls = "AI  ", "p"
        else:
            tag, cls = "INFO", "x"
        rows.append(f'<div><span class="ts">{_e(ts)}</span>&nbsp;&nbsp;<span class="{cls}">{tag.replace(" ", "&nbsp;")}</span>&nbsp;&nbsp;<span class="x">{_e(body)}</span></div>')
    rows.append('<div><span class="cur"></span></div>')
    return _m(f'<div class="pz-win"><div class="pz-h"><span>$ <b>{_e(title)}</b></span><span>line #{len(lines)}</span></div>'
              f'<div class="pz-term">{"".join(rows)}</div></div>')


def stats_panel(wins, losses, rsi, spread_txt=""):
    tot = wins + losses
    wr = wins / tot * 100 if tot else 0.0
    rsi_c = RED if rsi >= 70 else (GREEN if rsi <= 30 else CYAN)
    return _m(f"""
    <div class="pz-win"><div class="pz-h"><span>STATS &middot; <b>THIS ACCOUNT</b></span><span>{_e(spread_txt)}</span></div>
      <div class="pz-grid3" style="grid-template-columns:1fr">
        <div>win rate <b>{wr:.1f}%</b><div class="pz-bar"><i style="width:{wr:.0f}%;background:{GREEN}"></i></div></div>
        <div>RSI(14) <b style="color:{rsi_c}">{rsi:.1f}</b><div class="pz-bar"><i style="width:{max(0, min(100, rsi)):.0f}%;background:{rsi_c}"></i></div></div>
        <div>W / L <b><span class="pos">{wins}</span> / <span class="neg">{losses}</span></b></div>
      </div></div>""")


# ---------------------------------------------------------------- charts
def _layout(fig, h):
    fig.update_layout(template="plotly_dark", height=h, margin=dict(l=6, r=6, t=8, b=6), paper_bgcolor="#0b1220",
                      plot_bgcolor="#0b1220", xaxis_rangeslider_visible=False, showlegend=False,
                      font=dict(family="JetBrains Mono, monospace", size=10, color="#6b819f"), hovermode="x unified")
    fig.update_xaxes(gridcolor="#101b2e", zeroline=False)
    fig.update_yaxes(gridcolor="#101b2e", zeroline=False, side="right")
    return fig


def pro_chart(df, entry=0.0, tp=None, sl=None, side="", height=430):
    """df columns: open high low close (volume optional). Candles + EMA + volume + RSI + entry/TP/SL lines."""
    if go is None or df is None or len(df) < 3:
        return None
    d = df.copy().reset_index(drop=True)
    c = d["close"].astype(float)
    ema = c.ewm(span=9, adjust=False).mean()
    delta = c.diff()
    g = delta.clip(lower=0).rolling(14).mean()
    l = (-delta.clip(upper=0)).rolling(14).mean()
    rsi = 100 - 100 / (1 + g / (l + 1e-10))
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.66, 0.14, 0.20])
    fig.add_trace(go.Candlestick(x=d.index, open=d["open"], high=d["high"], low=d["low"], close=d["close"],
                                 increasing=dict(line=dict(color=GREEN), fillcolor="rgba(34,242,160,.85)"),
                                 decreasing=dict(line=dict(color=RED), fillcolor="rgba(255,77,109,.85)"), name="price"), 1, 1)
    fig.add_trace(go.Scatter(x=d.index, y=ema, line=dict(color=VIOLET, width=1.6), name="EMA9"), 1, 1)
    if "volume" in d:
        up = (d["close"] >= d["open"]).tolist()
        fig.add_trace(go.Bar(x=d.index, y=d["volume"], marker_color=[("rgba(34,242,160,.45)" if u else "rgba(255,77,109,.45)") for u in up]), 2, 1)
    fig.add_trace(go.Scatter(x=d.index, y=rsi, line=dict(color=CYAN, width=1.4)), 3, 1)
    for lv, col in ((70, "rgba(255,77,109,.5)"), (30, "rgba(34,242,160,.5)")):
        fig.add_hline(y=lv, line=dict(color=col, width=1, dash="dot"), row=3, col=1)
    if entry and entry > 0:
        for y, col, txt in ((entry, "#dbe7f5", "ENTRY"), (tp, GREEN, "TP"), (sl, RED, "SL")):
            if y:
                fig.add_hline(y=y, line=dict(color=col, width=1.2, dash="dash"), row=1, col=1,
                              annotation_text=txt, annotation_position="left", annotation_font=dict(color=col, size=10))
    fig.update_yaxes(range=[0, 100], row=3, col=1)
    return _layout(fig, height)


def equity_chart(points, height=210):
    """points: list of net pnl numbers (chronological). Cumulative curve."""
    if go is None or not points:
        return None
    acc, cur = [], 0.0
    for p in points:
        cur += float(p)
        acc.append(cur)
    col = GREEN if acc[-1] >= 0 else RED
    fig = go.Figure(go.Scatter(x=list(range(1, len(acc) + 1)), y=acc, mode="lines", line=dict(color=col, width=2.2),
                               fill="tozeroy", fillcolor="rgba(34,242,160,.08)" if acc[-1] >= 0 else "rgba(255,77,109,.08)"))
    return _layout(fig, height)
