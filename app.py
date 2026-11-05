"""
RoboXY Tail-Spend Sourcing Agent
================================
Streamlit MVP for competitive quoting on low-value procurement needs.

Designed for a Lio Sales Engineering Super Day live demo (~30 min).
Hostable on Streamlit Community Cloud.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.agent import (
    advance_after_matching,
    advance_after_quotes,
    advance_after_send,
    award_quote,
    compare_quotes,
    compose_outreach_emails,
    log_activity,
    match_suppliers,
    simulate_quotes,
    submit_to_sap,
)
from src.models import RequestStatus, STATUS_LABELS_DE
from src.state import STEPS, get_request, init_session_state, set_active_request

st.set_page_config(
    page_title="RoboXY · Tail-Spend Agent",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

html, body, [class*="css"] {
  font-family: 'IBM Plex Sans', sans-serif;
}
h1, h2, h3, .stMarkdown h1, .stMarkdown h2 {
  font-family: 'DM Sans', sans-serif !important;
  letter-spacing: -0.02em;
}
.block-container { padding-top: 1.4rem; max-width: 1200px; }

/* Hide Streamlit chrome / Cloud GitHub toolbar where possible */
header[data-testid="stHeader"] { display: none !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
div[data-testid="stToolbar"] { display: none !important; }
a[href*="github.com"][data-testid="stToolbarActionButton"],
div[data-testid="stDecoration"] { display: none !important; }

div[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0F2A3D 0%, #1B4F72 55%, #245A7A 100%);
}
div[data-testid="stSidebar"] * { color: #E8EEF4 !important; }
div[data-testid="stSidebar"] .stSelectbox label,
div[data-testid="stSidebar"] .stRadio label { color: #C5D4E0 !important; }
div[data-testid="stSidebar"] div[data-baseweb="select"] > div {
  background-color: #163A52 !important;
  border-color: #2E6A8F !important;
}

.hero-banner {
  background: linear-gradient(120deg, #0F2A3D 0%, #1B4F72 45%, #2E86AB 100%);
  border-radius: 12px;
  padding: 1.4rem 1.8rem;
  color: #F7F9FB;
  margin-bottom: 1.2rem;
  box-shadow: 0 8px 24px rgba(15, 42, 61, 0.18);
}
.hero-banner h1 {
  color: #FFFFFF !important;
  font-size: 1.75rem;
  margin: 0 0 0.35rem 0;
  font-weight: 700;
}
.hero-banner p { color: #D6E4EF; margin: 0; font-size: 0.98rem; }
.brand-mark {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #7FDBDA;
  margin-bottom: 0.4rem;
}

.kpi-tile {
  background: #FFFFFF;
  border: 1px solid #D5E0EA;
  border-radius: 10px;
  padding: 1rem 1.1rem;
  height: 100%;
}
.kpi-tile .label { color: #5A6F82; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; }
.kpi-tile .value { font-family: 'DM Sans', sans-serif; font-size: 1.55rem; font-weight: 700; color: #0F2A3D; margin-top: 0.2rem; }
.kpi-tile .hint { color: #7A8FA3; font-size: 0.8rem; margin-top: 0.15rem; }

.step-rail {
  display: flex; gap: 0.35rem; flex-wrap: wrap; margin: 0.6rem 0 1.2rem 0;
}
.step-pill {
  padding: 0.35rem 0.7rem;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 600;
  background: #E8EEF4;
  color: #5A6F82;
}
.step-pill.active { background: #1B4F72; color: #FFFFFF; }
.step-pill.done { background: #D4EDDA; color: #1E5C34; }

.hitl-banner {
  background: #FFF8E8;
  border-left: 4px solid #E0A800;
  padding: 0.85rem 1rem;
  border-radius: 0 8px 8px 0;
  margin: 0.6rem 0 1rem 0;
  color: #5C4A12;
  font-size: 0.92rem;
}
.agent-banner {
  background: #E8F4F8;
  border-left: 4px solid #2E86AB;
  padding: 0.85rem 1rem;
  border-radius: 0 8px 8px 0;
  margin: 0.6rem 0 1rem 0;
  color: #0F2A3D;
  font-size: 0.92rem;
}
.success-banner {
  background: #E7F6EC;
  border-left: 4px solid #2E7D4F;
  padding: 0.85rem 1rem;
  border-radius: 0 8px 8px 0;
  margin: 0.6rem 0 1rem 0;
  color: #1E5C34;
}

.email-box {
  background: #FFFFFF;
  border: 1px solid #D5E0EA;
  border-radius: 8px;
  padding: 1rem;
  font-family: 'IBM Plex Sans', monospace;
  font-size: 0.86rem;
  white-space: pre-wrap;
  line-height: 1.45;
}
.supplier-chip {
  display: inline-block;
  background: #E8EEF4;
  border-radius: 4px;
  padding: 0.15rem 0.45rem;
  font-size: 0.75rem;
  margin-right: 0.3rem;
}
</style>
""",
    unsafe_allow_html=True,
)

init_session_state()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### RoboXY")
    st.caption("Tail-Spend Sourcing Agent")
    st.markdown("---")

    nav = st.radio(
        "Navigation",
        ["Sourcing-Assistent", "Lieferantendatenbank"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("**Aktiver Bedarf**")
    req_options = {f"{r.id} · {r.title[:42]}": r.id for r in st.session_state.requests}
    labels = list(req_options.keys())
    current = st.session_state.active_request_id
    default_idx = 0
    for i, (label, rid) in enumerate(req_options.items()):
        if rid == current:
            default_idx = i
            break
    chosen = st.selectbox("Bedarf wählen", labels, index=default_idx, label_visibility="collapsed")
    if req_options[chosen] != st.session_state.active_request_id:
        set_active_request(req_options[chosen])
        st.rerun()

    active = get_request()
    if active:
        st.caption(f"Status: {STATUS_LABELS_DE[active.status]}")
        st.caption(f"Schätzwert: {active.estimated_value_eur:,.0f} €")

    st.markdown("---")
    if st.button("Demo zurücksetzen", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def render_hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="hero-banner">
          <div class="brand-mark">RoboXY · Einkauf</div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_step_rail(current: int) -> None:
    pills = []
    for i, name in enumerate(STEPS):
        cls = "active" if i == current else ("done" if i < current else "")
        pills.append(f'<span class="step-pill {cls}">{i + 1}. {name}</span>')
    st.markdown(f'<div class="step-rail">{"".join(pills)}</div>', unsafe_allow_html=True)


def fmt_eur(value: float) -> str:
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ===========================================================================
# PAGE: Sourcing-Assistent
# ===========================================================================
if nav == "Sourcing-Assistent":
    req = get_request()
    if req is None:
        st.error("Kein Bedarf ausgewählt.")
        st.stop()

    render_hero(
        "Sourcing-Assistent",
        f"{req.id} · {req.title}",
    )

    # Keep wizard step aligned when jumping between requests
    step = st.session_state.wizard_step
    render_step_rail(step)

    # ---- Step 0: Bedarf ----
    if step == 0:
        c1, c2 = st.columns((1.6, 1))
        with c1:
            st.subheader("Leistungsbeschreibung")
            st.write(req.description)
            st.markdown("**Positionen**")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Beschreibung": li.description,
                            "Menge": li.quantity,
                            "Einheit": li.unit,
                        }
                        for li in req.line_items
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        with c2:
            st.subheader("Metadaten")
            meta = {
                "Anforderer": req.requester,
                "Abteilung": req.department,
                "Kostenstelle": req.cost_center,
                "Standort": req.site,
                "Kategorie": req.category,
                "Unterkategorie": req.subcategory,
                "Schätzwert": fmt_eur(req.estimated_value_eur),
                "Dringlichkeit": req.urgency,
                "Benötigt bis": req.needed_by,
                "Status": STATUS_LABELS_DE[req.status],
            }
            for k, v in meta.items():
                st.markdown(f"**{k}**  \n{v}")

        st.markdown("---")
        if st.button("Agent: Passende Lieferanten suchen", type="primary"):
            matches = match_suppliers(req, st.session_state.suppliers, top_n=4)
            req.matches = matches
            req.status = RequestStatus.MATCHING
            advance_after_matching(req)
            st.session_state.wizard_step = 1
            st.rerun()

    # ---- Step 1: Lieferanten ----
    elif step == 1:
        if not req.matches:
            req.matches = match_suppliers(req, st.session_state.suppliers, top_n=4)
            advance_after_matching(req)

        st.markdown(
            '<div class="agent-banner"><b>Agent-Ergebnis:</b> Aus der internen '
            "Lieferantendatenbank wurden die besten Treffer für Kategorie, Region und "
            "historische Preiskompetitivität gerankt. Bitte Auswahl prüfen.</div>",
            unsafe_allow_html=True,
        )

        for i, match in enumerate(req.matches):
            s = match.supplier
            cols = st.columns((0.08, 1.4, 0.5, 0.5))
            with cols[0]:
                selected = st.checkbox(
                    "Sel",
                    value=match.selected,
                    key=f"match_sel_{req.id}_{s.id}",
                    label_visibility="collapsed",
                )
                match.selected = selected
            with cols[1]:
                st.markdown(f"**{s.name}**  \n{s.city} · {s.category}")
                st.caption(" · ".join(match.reasons[:3]))
            with cols[2]:
                st.metric("Score", f"{match.score:.0f}")
            with cols[3]:
                st.metric("Rating", f"{s.rating}/5")

        selected_count = sum(1 for m in req.matches if m.selected)
        if selected_count < 2:
            st.warning("Für echten Wettbewerb mindestens 2 Lieferanten auswählen.")

        st.markdown("---")
        b1, b2, _ = st.columns((1, 1, 2))
        with b1:
            if st.button("Zurück"):
                st.session_state.wizard_step = 0
                st.rerun()
        with b2:
            if st.button(
                "Anfrage-E-Mails entwerfen",
                type="primary",
                disabled=selected_count < 1,
            ):
                req.emails = compose_outreach_emails(req, req.matches)
                req.status = RequestStatus.AWAITING_OUTREACH
                log_activity(req, f"Entwürfe für {len(req.emails)} Anfragen erstellt.")
                st.session_state.wizard_step = 2
                st.rerun()

    # ---- Step 2: Anfragen freigeben (HITL, optional) ----
    elif step == 2:
        st.markdown(
            '<div class="hitl-banner"><b>Demo – kein echter E-Mail-Versand:</b> '
            "Entwürfe prüfen und freigeben, oder Freigabe überspringen und den "
            "simulierten Versand später nachholen. Es verlassen keine Nachrichten "
            "das System.</div>",
            unsafe_allow_html=True,
        )

        if not req.emails:
            req.emails = compose_outreach_emails(req, req.matches)

        for email in req.emails:
            with st.expander(
                f"{email.supplier_name} → {email.to_address}",
                expanded=True,
            ):
                email.subject = st.text_input(
                    "Betreff",
                    value=email.subject,
                    key=f"subj_{req.id}_{email.supplier_id}",
                )
                email.body = st.text_area(
                    "Nachricht",
                    value=email.body,
                    height=220,
                    key=f"body_{req.id}_{email.supplier_id}",
                )

        st.markdown("---")
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("Zurück", key="back_step2"):
                st.session_state.wizard_step = 1
                st.rerun()
        with b2:
            if st.button(
                "Freigeben & senden (Demo)",
                type="primary",
                disabled=not req.emails,
                key="approve_send",
            ):
                for e in req.emails:
                    e.approved = True
                    e.sent = True
                log_activity(
                    req,
                    "Anfragen freigegeben und Versand simuliert (kein echter Versand).",
                )
                advance_after_send(req)
                st.session_state.wizard_step = 3
                st.rerun()
        with b3:
            if st.button(
                "Überspringen",
                disabled=not req.emails,
                key="skip_approve",
            ):
                for e in req.emails:
                    e.approved = False
                    e.sent = False
                log_activity(
                    req,
                    "Freigabe übersprungen – simulierter Versand kann später erfolgen.",
                )
                st.session_state.wizard_step = 3
                st.rerun()

    # ---- Step 3: Angebote ----
    elif step == 3:
        st.markdown(
            '<div class="agent-banner">In der Realität treffen PDF-Angebote per E-Mail ein. '
            "Für die Demo simuliert der Agent realistische Angebote der kontaktierten "
            "Lieferanten (Header + Positionen + Anfahrt). Es werden keine echten "
            "E-Mails versendet.</div>",
            unsafe_allow_html=True,
        )

        any_sent = bool(req.emails) and any(e.sent for e in req.emails)
        if not any_sent:
            st.info(
                "Anfragen sind noch nicht „versendet“. Der Versand ist nur simuliert "
                "und dient der Demo – es geht keine E-Mail raus."
            )
            if st.button("Anfragen simuliert versenden", type="primary", key="sim_send"):
                for e in req.emails:
                    e.sent = True
                log_activity(
                    req,
                    "Versand der Anfragen simuliert (kein echter E-Mail-Versand).",
                )
                advance_after_send(req)
                st.rerun()
        else:
            sent_to = [e.supplier_name for e in req.emails if e.sent]
            st.write("Anfragen (simuliert) gesendet an:", ", ".join(sent_to))

        if not req.quotes:
            if st.button(
                "Angebote abrufen (Simulation)",
                type="primary",
                disabled=not any_sent,
            ):
                selected_matches = [m for m in req.matches if m.selected]
                req.quotes = simulate_quotes(req, selected_matches)
                req.comparison = compare_quotes(req.quotes)
                advance_after_quotes(req)
                st.rerun()
        else:
            st.success(f"{len(req.quotes)} Angebote eingegangen")
            qdf = pd.DataFrame(
                [
                    {
                        "Angebot": q.id,
                        "Lieferant": q.supplier_name,
                        "Gesamt": q.total,
                        "Arbeit": q.labor_total,
                        "Material": q.materials_total,
                        "Anfahrt": q.travel_total,
                        "Lieferzeit (Tage)": q.lead_time_days,
                        "Stamm?": "Ja" if q.is_preferred_incumbent else "",
                    }
                    for q in req.quotes
                ]
            )
            st.dataframe(
                qdf,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Gesamt": st.column_config.NumberColumn(format="%.2f €"),
                    "Arbeit": st.column_config.NumberColumn(format="%.2f €"),
                    "Material": st.column_config.NumberColumn(format="%.2f €"),
                    "Anfahrt": st.column_config.NumberColumn(format="%.2f €"),
                },
            )

            with st.expander("Positionsdetails je Angebot"):
                for q in req.quotes:
                    st.markdown(f"**{q.supplier_name}** ({q.id})")
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Position": li.description,
                                    "Menge": li.quantity,
                                    "Einheit": li.unit,
                                    "EP": li.unit_price,
                                    "Gesamt": li.total,
                                }
                                for li in q.line_items
                            ]
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.caption(q.notes)

        st.markdown("---")
        b1, b2, _ = st.columns((1, 1, 2))
        with b1:
            if st.button("Zurück", key="back_step3"):
                st.session_state.wizard_step = 2
                st.rerun()
        with b2:
            if req.quotes and st.button("Zum Vergleich", type="primary"):
                if not req.comparison:
                    req.comparison = compare_quotes(req.quotes)
                req.status = RequestStatus.AWAITING_AWARD
                st.session_state.wizard_step = 4
                st.rerun()

    # ---- Step 4: Vergleich & Vergabe (HITL) ----
    elif step == 4:
        if not req.quotes:
            st.warning("Noch keine Angebote – bitte einen Schritt zurück.")
            if st.button("Zu Angebote"):
                st.session_state.wizard_step = 3
                st.rerun()
            st.stop()

        if not req.comparison:
            req.comparison = compare_quotes(req.quotes)

        comp = req.comparison
        recommended = next(q for q in req.quotes if q.id == comp.recommended_quote_id)

        st.markdown(
            '<div class="hitl-banner"><b>Human-in-the-Loop:</b> Der Agent empfiehlt – '
            "die Vergabeentscheidung trifft der Mensch.</div>",
            unsafe_allow_html=True,
        )

        st.subheader("Agent-Empfehlung")
        r1, r2, r3 = st.columns(3)
        r1.metric("Empfohlener Lieferant", recommended.supplier_name)
        r2.metric("Angebotssumme", fmt_eur(recommended.total))
        save_label = (
            fmt_eur(comp.savings_vs_incumbent)
            if comp.savings_vs_incumbent is not None
            else fmt_eur(comp.savings_vs_highest)
        )
        r3.metric(
            "Ersparnis vs. Stamm / Max",
            save_label,
        )

        for line in comp.rationale:
            st.markdown(f"- {line}")

        chart_df = pd.DataFrame(comp.scorecard)
        fig = px.bar(
            chart_df,
            x="supplier",
            y="total",
            color="overall_score",
            color_continuous_scale=["#8FA6B8", "#1B4F72"],
            text="total",
            labels={"supplier": "Lieferant", "total": "Gesamtpreis (€)", "overall_score": "Score"},
        )
        fig.update_traces(texttemplate="%{text:,.0f} €", textposition="outside")
        fig.update_layout(
            height=340,
            margin=dict(l=10, r=10, t=20, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Scorecard**")
        st.dataframe(
            chart_df.rename(
                columns={
                    "quote_id": "Angebot",
                    "supplier": "Lieferant",
                    "total": "Preis €",
                    "lead_time_days": "Lieferzeit",
                    "price_score": "Preis-Score",
                    "lead_score": "Zeit-Score",
                    "overall_score": "Gesamt",
                    "is_incumbent": "Stamm",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Vergabe")
        options = {f"{q.supplier_name} – {fmt_eur(q.total)} ({q.id})": q.id for q in req.quotes}
        default_label = next(
            label for label, qid in options.items() if qid == comp.recommended_quote_id
        )
        choice = st.radio(
            "Lieferant beauftragen",
            list(options.keys()),
            index=list(options.keys()).index(default_label),
        )

        st.markdown("---")
        b1, b2, _ = st.columns((1, 1, 2))
        with b1:
            if st.button("Zurück", key="back_step4"):
                st.session_state.wizard_step = 3
                st.rerun()
        with b2:
            if st.button("Vergabe bestätigen", type="primary"):
                award_quote(req, options[choice])
                st.session_state.wizard_step = 5
                st.rerun()

    # ---- Step 5: SAP ----
    elif step == 5:
        awarded = next((q for q in req.quotes if q.id == req.awarded_quote_id), None)
        st.markdown(
            '<div class="success-banner"><b>Vergabe abgeschlossen.</b> '
            "Nachgelagert: manuelle SAP-Erfassung entfällt perspektivisch – "
            "hier als Mock „Submit to SAP“ dargestellt (sekundäres Problem laut Case).</div>",
            unsafe_allow_html=True,
        )

        if awarded:
            c1, c2, c3 = st.columns(3)
            c1.metric("Lieferant", awarded.supplier_name)
            c2.metric("Auftragswert", fmt_eur(awarded.total))
            c3.metric(
                "Status",
                STATUS_LABELS_DE[req.status],
            )

            if req.comparison and req.comparison.savings_vs_incumbent:
                st.info(
                    f"Gegenüber dem typischen Einzellieferanten-Szenario: "
                    f"**{fmt_eur(max(0, req.comparison.savings_vs_incumbent))}** sichtbar gemacht."
                )

        if req.status != RequestStatus.SUBMITTED_TO_SAP:
            if st.button("In SAP erfassen (Mock)", type="primary"):
                po = submit_to_sap(req)
                st.success(f"Bestellung {po} angelegt (Mock-Schnittstelle).")
                st.rerun()
        else:
            st.success(f"SAP-Bestellung: **{req.sap_po_number}**")
            st.balloons()

        st.subheader("Aktivitätsprotokoll")
        if req.activity_log:
            for entry in reversed(req.activity_log):
                st.markdown(f"`{entry['timestamp']}` — {entry['message']}")
        else:
            st.caption("Noch keine Einträge.")

        st.markdown("---")
        if st.button("Neuen Bedarf starten / zurück zum Bedarf"):
            st.session_state.wizard_step = 0
            st.rerun()


# ===========================================================================
# PAGE: Lieferantendatenbank
# ===========================================================================
elif nav == "Lieferantendatenbank":
    render_hero(
        "Interne Lieferantendatenbank",
        "Bereits vorhanden laut Case-Annahmen – der Agent sucht und rankt, "
        "statt dass Anforderer nur den Bekannten anrufen.",
    )
    suppliers = st.session_state.suppliers
    cats = sorted({s.category for s in suppliers})
    filter_cat = st.multiselect("Kategorie filtern", cats, default=cats)
    rows = [
        {
            "ID": s.id,
            "Name": s.name,
            "Kategorie": s.category,
            "Stadt": s.city,
            "Region": s.region,
            "Rating": s.rating,
            "Antwort (Tage)": s.avg_response_days,
            "Aufträge": s.past_orders,
            "E-Mail": s.email,
            "Zertifikate": ", ".join(s.certifications),
        }
        for s in suppliers
        if s.category in filter_cat
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(f"{len(rows)} Lieferanten · Mock-Stammdaten für die Demo")
