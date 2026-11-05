"""AI sourcing agent for RoboXY tail-spend competitive quoting.

This MVP uses deterministic, explainable scoring so the Super Day demo
works offline without API keys. The same interfaces can later call an LLM.
"""

from __future__ import annotations

from datetime import date, timedelta
import random
from typing import Sequence

from .models import (
    OutreachEmail,
    Quote,
    QuoteComparison,
    QuoteLineItem,
    RequestStatus,
    SourcingRequest,
    Supplier,
    SupplierMatch,
)


def match_suppliers(
    request: SourcingRequest,
    suppliers: Sequence[Supplier],
    top_n: int = 4,
) -> list[SupplierMatch]:
    """Rank suppliers from the internal database for a given requirement."""
    scored: list[SupplierMatch] = []

    for supplier in suppliers:
        score = 0.0
        reasons: list[str] = []

        if supplier.category == request.category:
            score += 40
            reasons.append(f"Passende Kategorie: {supplier.category}")
        elif request.category.split()[0] in supplier.category:
            score += 15
            reasons.append(f"Teilweise passende Kategorie: {supplier.category}")
        else:
            score -= 20
            reasons.append(f"Andere Kategorie ({supplier.category}) – weniger geeignet")

        if request.subcategory in supplier.subcategories:
            score += 25
            reasons.append(f"Spezialisierung: {request.subcategory}")
        else:
            overlap = [
                s
                for s in supplier.subcategories
                if any(tok.lower() in s.lower() for tok in request.subcategory.split())
            ]
            if overlap:
                score += 10
                reasons.append(f"Verwandte Leistung: {overlap[0]}")

        if "Bayern" in supplier.region or supplier.city in request.site:
            score += 15
            reasons.append(f"Regionale Nähe: {supplier.city}")
        elif supplier.region:
            score += 5
            reasons.append(f"Bundesweit / {supplier.region}")

        score += min(supplier.rating, 5.0) * 3
        reasons.append(f"Bewertung {supplier.rating}/5.0")

        if supplier.past_orders > 0:
            score += min(supplier.past_orders, 10)
            reasons.append(f"{supplier.past_orders} frühere Aufträge bei RoboXY")
        else:
            score += 4
            reasons.append("Neuer Lieferant – erweitert den Wettbewerb")

        if supplier.avg_response_days <= 2:
            score += 5
            reasons.append(f"Schnelle Antwort (Ø {supplier.avg_response_days} Tag(e))")

        if supplier.typical_markup < 0.95:
            score += 8
            reasons.append("Historisch wettbewerbsfähige Preisgestaltung")
        elif supplier.typical_markup > 1.05:
            score -= 3
            reasons.append("Historisch eher teurer")

        scored.append(SupplierMatch(supplier=supplier, score=round(score, 1), reasons=reasons))

    scored.sort(key=lambda m: m.score, reverse=True)
    top = scored[:top_n]
    for match in top:
        match.selected = match.score >= 40
    return top


def add_manual_supplier(
    request: SourcingRequest,
    supplier: Supplier,
) -> SupplierMatch | None:
    """Let the requester add a supplier from the database to the shortlist."""
    if any(m.supplier.id == supplier.id for m in request.matches):
        return None
    match = SupplierMatch(
        supplier=supplier,
        score=50.0,
        reasons=["Manuell aus der Lieferantendatenbank hinzugefügt"],
        selected=True,
    )
    request.matches.append(match)
    log_activity(request, f"Lieferant manuell hinzugefügt: {supplier.name}")
    return match


def compose_outreach_emails(
    request: SourcingRequest,
    matches: Sequence[SupplierMatch],
) -> list[OutreachEmail]:
    """Draft RFQ emails for human approval before sending."""
    emails: list[OutreachEmail] = []
    line_summary = "\n".join(
        f"  – {li.description}: {li.quantity:g} {li.unit}" for li in request.line_items
    )

    for match in matches:
        if not match.selected:
            continue
        supplier = match.supplier
        subject = f"Anfrage RoboXY {request.id}: {request.title}"
        body = f"""Sehr geehrte Damen und Herren,

im Namen der RoboXY GmbH (Fertigung von Bauteilen für Robotik) bitten wir um ein unverbindliches Angebot für folgende Leistung:

Bedarf:          {request.title}
Anfrage-Nr.:     {request.id}
Standort:        {request.site}
Benötigt bis:    {request.needed_by}
Kostenstelle:    {request.cost_center}

Leistungsbeschreibung:
{request.description}

Positionen:
{line_summary}

Bitte senden Sie uns Ihr Angebot als PDF mit:
  • Aufschlüsselung nach Arbeitsleistung, Material und Anfahrt
  • Gültigkeitsdauer
  • Voraussichtlicher Ausführungszeitraum / Vorlauf

Antwort bitte an: einkauf@roboxy.de
Kennzeichen: {request.id}

Mit freundlichen Grüßen
RoboXY Einkauf – Tail-Spend Agent (Entwurf)
Ansprechpartner Anforderer: {request.requester} ({request.department})
"""
        emails.append(
            OutreachEmail(
                supplier_id=supplier.id,
                supplier_name=supplier.name,
                to_address=supplier.email,
                subject=subject,
                body=body.strip(),
            )
        )
    return emails


def _base_unit_price(description: str, category: str) -> float:
    desc = description.lower()
    if "m²" in desc or "wand" in desc or "anstrich" in desc:
        return 6.5
    if "lfm" in desc or "sockel" in desc:
        return 9.0
    if "abkleb" in desc or "schutz" in desc:
        return 450.0
    if "anfahrt" in desc or "auf-/abbau" in desc or "montage" in desc:
        return 280.0
    if "hydraulik" in desc or "schlauch" in desc:
        return 320.0
    if "dichtung" in desc:
        return 85.0
    if category == "Malerarbeiten":
        return 7.0
    return 150.0


def simulate_quotes(
    request: SourcingRequest,
    matches: Sequence[SupplierMatch],
    seed: int | None = None,
) -> list[Quote]:
    """Simulate supplier PDF quotes arriving by email (demo stand-in)."""
    rng = random.Random(seed if seed is not None else hash(request.id) % 10_000)
    quotes: list[Quote] = []
    today = date.today()

    # Prefer the known requester-favorite as "incumbent" when present
    incumbent_ids = {"SUP-003", "SUP-001"}

    for idx, match in enumerate(matches):
        if not match.selected:
            continue
        supplier = match.supplier
        markup = supplier.typical_markup * rng.uniform(0.97, 1.06)

        line_items: list[QuoteLineItem] = []
        materials = 0.0
        labor = 0.0

        for li in request.line_items:
            base = _base_unit_price(li.description + " " + li.unit, request.category)
            unit_price = round(base * markup, 2)
            total = round(unit_price * li.quantity, 2)
            line_items.append(
                QuoteLineItem(
                    description=li.description,
                    quantity=li.quantity,
                    unit=li.unit,
                    unit_price=unit_price,
                    total=total,
                )
            )
            if any(k in li.description.lower() for k in ("material", "schlauch", "dichtung")):
                materials += total
            else:
                labor += total

        travel = round(120 * markup * rng.uniform(0.8, 1.4), 2)
        other = round(rng.uniform(0, 80), 2)
        # Rebalance: line totals already include labor/materials; travel/other on top
        lines_total = sum(i.total for i in line_items)
        # Split lines into labor vs materials heuristically for display
        materials_total = round(lines_total * 0.25, 2)
        labor_total = round(lines_total - materials_total, 2)
        total = round(lines_total + travel + other, 2)

        is_incumbent = supplier.id in incumbent_ids and supplier.past_orders >= 5

        quotes.append(
            Quote(
                id=f"Q-{request.id[-4:]}-{supplier.id[-3:]}",
                supplier_id=supplier.id,
                supplier_name=supplier.name,
                request_id=request.id,
                currency="EUR",
                labor_total=labor_total,
                materials_total=materials_total,
                travel_total=travel,
                other_total=other,
                total=total,
                valid_until=(today + timedelta(days=30)).isoformat(),
                lead_time_days=int(supplier.avg_response_days + rng.randint(3, 10)),
                notes=_quote_notes(supplier, rng),
                line_items=line_items,
                received_at=today.isoformat(),
                is_preferred_incumbent=is_incumbent,
            )
        )

    quotes.sort(key=lambda q: q.total)
    return quotes


def _quote_notes(supplier: Supplier, rng: random.Random) -> str:
    options = [
        f"Ausführung inkl. Wochenendarbeit möglich. {supplier.notes}",
        "Festpreis, Nachträge nur bei Mehraufwand nach Freigabe.",
        "Material nach RAL-Vorgabe, umweltfreundliche Dispersionsfarbe.",
        "Angebot gilt für den genannten Standort; Anfahrt pauschal.",
    ]
    return rng.choice(options)


def compare_quotes(quotes: Sequence[Quote]) -> QuoteComparison:
    """Score quotes and recommend the most competitive overall option."""
    if not quotes:
        return QuoteComparison(
            quotes=[],
            recommended_quote_id="",
            savings_vs_highest=0.0,
            savings_vs_incumbent=None,
            rationale=["Keine Angebote vorhanden."],
            scorecard=[],
        )

    totals = [q.total for q in quotes]
    min_total = min(totals)
    max_total = max(totals)
    avg_lead = sum(q.lead_time_days for q in quotes) / len(quotes)

    scorecard: list[dict] = []
    best_id = ""
    best_score = -1.0

    for q in quotes:
        price_score = 100 * (1 - (q.total - min_total) / max(max_total - min_total, 1))
        lead_score = max(0, 100 - (q.lead_time_days - 5) * 8)
        completeness = 90 + (5 if q.notes else 0)
        # Slight penalty if only choosing the familiar incumbent without competition benefit
        diversity_bonus = 0 if q.is_preferred_incumbent else 5

        overall = round(0.55 * price_score + 0.25 * lead_score + 0.15 * completeness + diversity_bonus, 1)
        scorecard.append(
            {
                "quote_id": q.id,
                "supplier": q.supplier_name,
                "total": q.total,
                "lead_time_days": q.lead_time_days,
                "price_score": round(price_score, 1),
                "lead_score": round(lead_score, 1),
                "overall_score": overall,
                "is_incumbent": q.is_preferred_incumbent,
            }
        )
        if overall > best_score:
            best_score = overall
            best_id = q.id

    recommended = next(q for q in quotes if q.id == best_id)
    incumbent = next((q for q in quotes if q.is_preferred_incumbent), None)
    savings_vs_highest = round(max_total - recommended.total, 2)
    savings_vs_incumbent = (
        round(incumbent.total - recommended.total, 2) if incumbent else None
    )

    rationale = [
        f"Empfohlen: {recommended.supplier_name} ({recommended.total:,.2f} €).",
        f"Preisvorteil gegenüber teuerstem Angebot: {savings_vs_highest:,.2f} €.",
    ]
    if savings_vs_incumbent is not None and incumbent:
        if savings_vs_incumbent > 0:
            rationale.append(
                f"Gegenüber dem Stamm-lieferanten ({incumbent.supplier_name}): "
                f"{savings_vs_incumbent:,.2f} € Ersparnis."
            )
        elif savings_vs_incumbent < 0:
            rationale.append(
                f"Stamm-lieferant wäre {abs(savings_vs_incumbent):,.2f} € günstiger, "
                f"verliert aber bei Lieferzeit/Gesamtscore."
            )
        else:
            rationale.append("Preisgleich mit dem Stamm-lieferanten – Empfehlung nach Scorecard.")

    rationale.append(
        f"Bewertungsgewichtung: 55 % Preis, 25 % Lieferzeit (Ø {avg_lead:.0f} Tage), "
        "15 % Vollständigkeit, Bonus für Wettbewerbsvielfalt."
    )
    rationale.append(
        "Ohne Agent hätte der Anforderer typischerweise nur den bekannten Lieferanten "
        "angefragt – der Vergleich macht Tail-Spend Einsparungen erstmals sichtbar."
    )

    scorecard.sort(key=lambda s: s["overall_score"], reverse=True)
    return QuoteComparison(
        quotes=list(quotes),
        recommended_quote_id=best_id,
        savings_vs_highest=savings_vs_highest,
        savings_vs_incumbent=savings_vs_incumbent,
        rationale=rationale,
        scorecard=scorecard,
    )


def log_activity(request: SourcingRequest, message: str) -> None:
    from datetime import datetime

    request.activity_log.append(
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "message": message,
        }
    )


def advance_after_matching(request: SourcingRequest) -> None:
    request.status = RequestStatus.AWAITING_OUTREACH
    log_activity(request, "Agent hat passende Lieferanten vorgeschlagen.")


def advance_after_send(request: SourcingRequest) -> None:
    """Mark outreach as done in the demo flow. No real e-mail is sent."""
    request.status = RequestStatus.AWAITING_QUOTES
    sent = sum(1 for e in request.emails if e.sent)
    log_activity(
        request,
        f"{sent} Angebotsanfragen simuliert versendet (kein echter E-Mail-Versand) – "
        "warte auf Angebote.",
    )


def hydrate_demo_with_quotes(
    request: SourcingRequest,
    suppliers: Sequence[Supplier],
) -> None:
    """Preload one example request where outreach was sent earlier and quotes arrived."""
    if request.quotes:
        return

    request.matches = match_suppliers(request, suppliers, top_n=4)
    request.emails = compose_outreach_emails(request, request.matches)
    sent_on = (date.today() - timedelta(days=5)).isoformat()
    for email in request.emails:
        email.approved = True
        email.sent = True

    request.quotes = simulate_quotes(request, request.matches)
    for quote in request.quotes:
        quote.received_at = (date.today() - timedelta(days=2)).isoformat()

    request.comparison = compare_quotes(request.quotes)
    request.status = RequestStatus.AWAITING_AWARD
    request.activity_log = [
        {
            "timestamp": f"{sent_on} 09:15",
            "message": f"{len(request.emails)} Anfragen vor einigen Tagen versendet (Demo).",
        },
        {
            "timestamp": f"{(date.today() - timedelta(days=2)).isoformat()} 14:40",
            "message": f"{len(request.quotes)} Angebote eingegangen – bereit zum Vergleich.",
        },
    ]


def advance_after_quotes(request: SourcingRequest) -> None:
    request.status = RequestStatus.AWAITING_AWARD
    log_activity(request, f"{len(request.quotes)} Angebote eingegangen und verglichen.")


def award_quote(request: SourcingRequest, quote_id: str) -> None:
    request.awarded_quote_id = quote_id
    request.status = RequestStatus.AWARDED
    quote = next(q for q in request.quotes if q.id == quote_id)
    log_activity(
        request,
        f"Auswahl bestätigt: {quote.supplier_name} ({quote.total:,.2f} €).",
    )


def submit_to_sap(request: SourcingRequest) -> str:
    """Mock: requester submits the award to procurement and records it in SAP."""
    po = f"PO-{request.id.replace('REQ-', '')}-{request.awarded_quote_id[-3:]}"
    request.sap_po_number = po
    request.status = RequestStatus.SUBMITTED_TO_SAP
    quote = next(q for q in request.quotes if q.id == request.awarded_quote_id)
    log_activity(
        request,
        f"Auftrag an Einkauf eingereicht und in SAP hinterlegt "
        f"({po}, {quote.supplier_name}) – Demo/Mock, keine echte Schnittstelle.",
    )
    return po
