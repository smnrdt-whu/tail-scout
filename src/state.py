"""Session-state helpers and data loading for the Streamlit app."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from .models import RequestStatus, SourcingRequest, Supplier

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
    st.session_state.active_request_id = st.session_state.requests[0].id
    st.session_state.wizard_step = 0
    st.session_state.demo_mode = True
    st.session_state.annual_cases = 250
    st.session_state.savings_per_case = 750
    st.session_state.initialized = True


def get_request(request_id: str | None = None) -> SourcingRequest | None:
    rid = request_id or st.session_state.get("active_request_id")
    for req in st.session_state.requests:
        if req.id == rid:
            return req
    return None


def set_active_request(request_id: str) -> None:
    st.session_state.active_request_id = request_id
    st.session_state.wizard_step = _step_for_status(get_request(request_id).status)


def _step_for_status(status: RequestStatus) -> int:
    mapping = {
        RequestStatus.NEW: 0,
        RequestStatus.MATCHING: 1,
        RequestStatus.AWAITING_OUTREACH: 2,
        RequestStatus.AWAITING_QUOTES: 3,
        RequestStatus.COMPARING: 4,
        RequestStatus.AWAITING_AWARD: 4,
        RequestStatus.AWARDED: 5,
        RequestStatus.SUBMITTED_TO_SAP: 5,
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
    "Angebote",
    "Vergleich & Vergabe",
    "SAP-Übergabe",
]
