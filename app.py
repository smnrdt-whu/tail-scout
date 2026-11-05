"""
RoboXY Tail-Spend Sourcing Agent
================================
Streamlit MVP for competitive quoting on low-value procurement needs.

Designed for a Lio Sales Engineering Super Day live demo (~30 min).
Hostable on Streamlit Community Cloud.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from src.agent import (
    add_manual_supplier,
    advance_after_matching,
    advance_after_send,
    award_quote,
    compare_quotes,
    compose_outreach_emails,
    log_activity,
    match_suppliers,
    submit_to_sap,
)
from src.models import RequestStatus, STATUS_LABELS_DE
from src.state import (
    DEMO_READY_REQUEST_ID,
    STEPS,
    create_request_from_spec,
    get_request,
    init_session_state,
    set_active_request,
)

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

.ticket-card {
  background: #FFFFFF;
  border: 1px solid #D5E0EA;
  border-left: 5px solid #1B4F72;
  border-radius: 10px;
  padding: 1.1rem 1.2rem 1.2rem;
  height: 100%;
  box-shadow: 0 4px 14px rgba(15, 42, 61, 0.06);
}
.ticket-card .ticket-id {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #2E86AB;
  margin-bottom: 0.35rem;
}
.ticket-card .ticket-title {
  font-family: 'DM Sans', sans-serif;
  font-size: 1.05rem;
  font-weight: 700;
  color: #0F2A3D;
  line-height: 1.3;
  margin-bottom: 0.7rem;
  min-height: 2.6rem;
}
.ticket-card .ticket-meta {
  color: #5A6F82;
  font-size: 0.86rem;
  line-height: 1.55;
}
.ticket-card .ticket-value {
  font-family: 'DM Sans', sans-serif;
  font-size: 1.2rem;
  font-weight: 700;
  color: #0F2A3D;
  margin: 0.75rem 0 0.15rem;
}
.ticket-urgency {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.12rem 0.45rem;
  border-radius: 4px;
  background: #E8EEF4;
  color: #1B4F72;
}
.ticket-urgency.hoch { background: #FDECEA; color: #9B1C1C; }
.ticket-urgency.normal { background: #E8F4F8; color: #1B4F72; }
.ticket-urgency.niedrig { background: #EEF2F5; color: #5A6F82; }
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

    active = get_request()
    if active:
        st.markdown("---")
        st.caption("Aktives Ticket")
        st.markdown(f"**{active.id}**")
        st.caption(STATUS_LABELS_DE[active.status])
        if st.button("Zur Ticketauswahl", use_container_width=True):
            set_active_request(None)
            st.rerun()

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


def render_ticket_inbox() -> None:
    render_hero(
        "Offene Bedarfe",
        "Bedarf spezifizieren oder ein vorhandenes Ticket wählen.",
    )

    st.subheader("Bedarf spezifizieren")
    st.caption("Der Anforderer beschreibt die benötigte Leistung – Ausgangspunkt des Prozesses.")

    categories = sorted({s.category for s in st.session_state.suppliers})
    if not categories:
        categories = ["Malerarbeiten", "Hydraulik / Pneumatik", "Elektroarbeiten"]

    with st.form("new_request"):
        title = st.text_input("Titel der Leistung", placeholder="z. B. Neuanstrich Produktionshalle")
        description = st.text_area(
            "Leistungsbeschreibung",
            placeholder="Was wird benötigt? Ort, Umfang, Rahmenbedingungen…",
            height=140,
        )
        c1, c2 = st.columns(2)
        with c1:
            category = st.selectbox("Kategorie", categories)
            requester = st.text_input("Anforderer", placeholder="Vor- und Nachname")
        with c2:
            estimated_value = st.number_input(
                "Geschätzter Wert (€)",
                min_value=0.0,
                max_value=20000.0,
                value=5000.0,
                step=100.0,
            )
            needed_by = st.date_input(
                "Benötigt bis",
                value=date.today() + timedelta(days=30),
            )
        submitted = st.form_submit_button("Bedarf einreichen & starten", type="primary")

    if submitted:
        if not title.strip() or not description.strip():
            st.error("Bitte Titel und Leistungsbeschreibung angeben.")
        else:
            request_id = create_request_from_spec(
                title=title,
                description=description,
                category=category,
                estimated_value_eur=estimated_value,
                needed_by=needed_by.isoformat(),
                requester=requester,
            )
            set_active_request(request_id)
            st.rerun()

    def _render_ticket_cards(ticket_list: list) -> None:
        for row_start in range(0, len(ticket_list), 3):
            row = ticket_list[row_start : row_start + 3]
            cols = st.columns(len(row))
            for col, ticket in zip(cols, row):
                with col:
                    st.markdown(
                        f"""
                        <div class="ticket-card">
                          <div class="ticket-id">{ticket.id}</div>
                          <div class="ticket-title">{ticket.title}</div>
                          <div class="ticket-meta">
                            {ticket.category} · {ticket.site}<br/>
                            Anforderer: {ticket.requester}<br/>
                            Benötigt bis: {ticket.needed_by}
                          </div>
                          <div class="ticket-value">{fmt_eur(ticket.estimated_value_eur)}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.markdown("")
                    if st.button(
                        "Prozess starten",
                        key=f"start_{ticket.id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        set_active_request(ticket.id)
                        st.rerun()

    all_requests = st.session_state.requests
    demo_tickets = [r for r in all_requests if r.id == DEMO_READY_REQUEST_ID]
    own_tickets = [r for r in all_requests if r.id != DEMO_READY_REQUEST_ID]

    st.markdown("---")
    st.subheader("Beispiel-Ticket mit eingegangenen Angeboten")
    st.markdown(
        '<div class="agent-banner">Anfragen wurden vor einiger Zeit versendet – '
        "die Angebote sind bereits einsehbar und vergleichbar.</div>",
        unsafe_allow_html=True,
    )
    _render_ticket_cards(demo_tickets)

    if own_tickets:
        st.markdown("---")
        st.subheader("Ihre spezifizierten Bedarfe")
        _render_ticket_cards(own_tickets)


# ===========================================================================
# PAGE: Sourcing-Assistent
# ===========================================================================
if nav == "Sourcing-Assistent":
    req = get_request()
    if req is None:
        render_ticket_inbox()
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
        st.subheader("Manuell aus Lieferantendatenbank hinzufügen")
        st.caption(
            "Die Bedarfsperson kann bekannte Lieferanten zusätzlich zur "
            "Agent-Empfehlung aufnehmen."
        )
        already_ids = {m.supplier.id for m in req.matches}
        available = [s for s in st.session_state.suppliers if s.id not in already_ids]
        if available:
            options = {
                f"{s.name} · {s.city} · {s.category}": s.id for s in available
            }
            pick_cols = st.columns((3, 1))
            with pick_cols[0]:
                chosen_label = st.selectbox(
                    "Lieferant wählen",
                    list(options.keys()),
                    key=f"manual_supplier_{req.id}",
                    label_visibility="collapsed",
                )
            with pick_cols[1]:
                if st.button("Hinzufügen", use_container_width=True, key=f"add_sup_{req.id}"):
                    supplier = next(s for s in available if s.id == options[chosen_label])
                    add_manual_supplier(req, supplier)
                    st.rerun()
        else:
            st.caption("Alle Lieferanten der Datenbank sind bereits gelistet.")

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
            "Entwürfe prüfen und freigeben, oder Freigabe überspringen. "
            "Nach dem Versand warten Sie auf Angebote – es verlassen keine "
            "Nachrichten das System.</div>",
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

    # ---- Step 3: Vergleich & Auswahl ----
    elif step == 3:
        any_sent = bool(req.emails) and any(e.sent for e in req.emails)

        if not req.quotes:
            if not any_sent:
                st.markdown(
                    '<div class="agent-banner">Noch keine Anfragen versendet. '
                    "Erst nach dem Versand warten Sie auf Angebote der "
                    "Lieferanten.</div>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    "Anfragen simuliert versenden",
                    type="primary",
                    key="sim_send_only",
                ):
                    for e in req.emails:
                        e.sent = True
                    advance_after_send(req)
                    st.rerun()
            else:
                sent_to = [e.supplier_name for e in req.emails if e.sent]
                st.markdown(
                    '<div class="agent-banner"><b>Warten auf Angebote.</b> '
                    "Die Anfragen wurden versendet. Sobald Lieferanten antworten, "
                    "erscheinen die Angebote hier zum Vergleich.</div>",
                    unsafe_allow_html=True,
                )
                st.info(
                    "Versendet an: "
                    + (", ".join(sent_to) if sent_to else "—")
                    + ". Für fertige Angebote öffnen Sie das vorbereitete "
                    f"Beispiel-Ticket ({DEMO_READY_REQUEST_ID})."
                )

            st.markdown("---")
            if st.button("Zurück", key="back_step3_waiting"):
                st.session_state.wizard_step = 2
                st.rerun()
            st.stop()

        if not req.comparison:
            req.comparison = compare_quotes(req.quotes)

        comp = req.comparison
        recommended = next(q for q in req.quotes if q.id == comp.recommended_quote_id)

        st.markdown(
            '<div class="hitl-banner"><b>Angebote eingegangen.</b> Der Agent '
            "empfiehlt – als Bedarfsperson wählen Sie den Lieferanten und reichen "
            "den Auftrag anschließend beim Einkauf ein.</div>",
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

        with st.expander("Angebotsdetails"):
            for q in req.quotes:
                st.markdown(f"**{q.supplier_name}** ({q.id}) – {fmt_eur(q.total)}")
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

        st.subheader("Auswahl")
        options = {f"{q.supplier_name} – {fmt_eur(q.total)} ({q.id})": q.id for q in req.quotes}
        default_label = next(
            label for label, qid in options.items() if qid == comp.recommended_quote_id
        )
        choice = st.radio(
            "Bevorzugter Lieferant",
            list(options.keys()),
            index=list(options.keys()).index(default_label),
        )

        st.markdown("---")
        b1, b2, _ = st.columns((1, 1, 2))
        with b1:
            if st.button("Zurück", key="back_step3"):
                st.session_state.wizard_step = 2
                st.rerun()
        with b2:
            if st.button("Auswahl bestätigen", type="primary"):
                award_quote(req, options[choice])
                st.session_state.wizard_step = 4
                st.rerun()

    # ---- Step 4: Beim Einkauf einreichen (+ SAP) ----
    elif step == 4:
        awarded = next((q for q in req.quotes if q.id == req.awarded_quote_id), None)
        st.markdown(
            '<div class="success-banner"><b>Auswahl steht.</b> Als Bedarfsperson '
            "reichen Sie den Auftrag jetzt beim Einkauf ein – parallel wird er in "
            "SAP hinterlegt (Demo/Mock, keine echte Schnittstelle).</div>",
            unsafe_allow_html=True,
        )

        if awarded:
            c1, c2, c3 = st.columns(3)
            c1.metric("Gewählter Lieferant", awarded.supplier_name)
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
            if st.button(
                "Beim Einkauf einreichen & in SAP hinterlegen",
                type="primary",
            ):
                po = submit_to_sap(req)
                st.success(
                    f"Auftrag an den Einkauf übermittelt und in SAP hinterlegt "
                    f"(Bestellung **{po}**, Demo/Mock)."
                )
                st.rerun()
        else:
            st.success(
                f"Eingereicht beim Einkauf · SAP-Bestellung **{req.sap_po_number}**"
            )
            st.balloons()

        st.subheader("Aktivitätsprotokoll")
        if req.activity_log:
            for entry in reversed(req.activity_log):
                st.markdown(f"`{entry['timestamp']}` — {entry['message']}")
        else:
            st.caption("Noch keine Einträge.")

        st.markdown("---")
        if st.button("Neuen Bedarf starten"):
            set_active_request(None)
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
