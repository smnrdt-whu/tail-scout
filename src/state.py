"""Session-state helpers and data loading for the Streamlit app."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import streamlit as st

from .models import LineItem, RequestStatus, SourcingRequest, Supplier

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def load_suppliers() -> list[Supplier]:
    with open(DATA / "suppliers.json", encoding="utf-8") as f:
        return [Supplier.from_dict(row) for row in json.load(f)]


def load_sample_requests() -> list[SourcingRequest]:
    with open(DATA / "sample_requests.json", encoding="utf-8") as f:
        return [SourcingRequest.from_dict(row) for row in json.load(f)]


def init_session_state() -> None:
    if "initialized" in st.session_state:
        return

    st.session_state.suppliers = load_suppliers()
    st.session_state.requests = load_sample_requests()
    st.session_state.active_request_id = None
    st.session_state.wizard_step = 0
    st.session_state.demo_mode = True
    st.session_state.annual_cases = 250
    st.session_state.savings_per_case = 750
    st.session_state.initialized = True


def get_request(request_id: str | None = None) -> SourcingRequest | None:
    rid = request_id if request_id is not None else st.session_state.get("active_request_id")
    if not rid:
        return None
    for req in st.session_state.requests:
        if req.id == rid:
            return req
    return None


def set_active_request(request_id: str | None) -> None:
    st.session_state.active_request_id = request_id
    if request_id is None:
        st.session_state.wizard_step = 0
        return
    req = get_request(request_id)
    st.session_state.wizard_step = _step_for_status(req.status) if req else 0


def _next_request_id() -> str:
    max_n = 0
    for req in st.session_state.requests:
        match = re.search(r"REQ-(\d{4})-(\d+)$", req.id)
        if match:
            max_n = max(max_n, int(match.group(2)))
    year = date.today().year
    return f"REQ-{year}-{max_n + 1:04d}"


def create_request_from_spec(
    *,
    title: str,
    description: str,
    category: str,
    estimated_value_eur: float,
    needed_by: str,
    requester: str,
) -> str:
    """Create a new sourcing request from a requester specification form."""
    request_id = _next_request_id()
    today = date.today().isoformat()
    subcategory = category.split("/")[0].strip() if category else "Allgemein"
    req = SourcingRequest(
        id=request_id,
        title=title.strip(),
        category=category,
        subcategory=subcategory,
        description=description.strip(),
        requester=requester.strip() or "Anforderer",
        department="Fachbereich",
        cost_center="CC-0000",
        site="Werk München-Nord",
        estimated_value_eur=float(estimated_value_eur),
        urgency="Normal",
        needed_by=needed_by,
        created_at=today,
        status=RequestStatus.NEW,
        spec_quality="high",
        line_items=[
            LineItem(description=title.strip(), quantity=1, unit="pauschal"),
        ],
    )
    st.session_state.requests.insert(0, req)
    return request_id


def _step_for_status(status: RequestStatus) -> int:
    mapping = {
        RequestStatus.NEW: 0,
        RequestStatus.MATCHING: 1,
        RequestStatus.AWAITING_OUTREACH: 2,
        RequestStatus.AWAITING_QUOTES: 3,
        RequestStatus.COMPARING: 3,
        RequestStatus.AWAITING_AWARD: 3,
        RequestStatus.AWARDED: 4,
        RequestStatus.SUBMITTED_TO_SAP: 4,
        RequestStatus.CANCELLED: 0,
    }
    return mapping.get(status, 0)


def portfolio_kpis() -> dict[str, Any]:
    requests: list[SourcingRequest] = st.session_state.requests
    open_reqs = [
        r
        for r in requests
        if r.status
        not in (RequestStatus.SUBMITTED_TO_SAP, RequestStatus.CANCELLED)
    ]
    awarded = [
        r
        for r in requests
        if r.status in (RequestStatus.AWARDED, RequestStatus.SUBMITTED_TO_SAP)
    ]
    realized = 0.0
    for r in awarded:
        if r.comparison and r.comparison.savings_vs_incumbent is not None:
            realized += max(0.0, r.comparison.savings_vs_incumbent)
        elif r.comparison:
            realized += max(0.0, r.comparison.savings_vs_highest * 0.4)

    annual_potential = st.session_state.annual_cases * st.session_state.savings_per_case
    return {
        "open": len(open_reqs),
        "awarded": len(awarded),
        "total": len(requests),
        "realized_savings": realized,
        "annual_potential": annual_potential,
        "annual_cases": st.session_state.annual_cases,
    }


STEPS = [
    "Bedarf",
    "Lieferanten",
    "Anfragen freigeben",
    "Vergleich & Vergabe",
    "SAP-Übergabe",
]
