"""Domain models for the RoboXY tail-spend sourcing MVP."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class RequestStatus(str, Enum):
    NEW = "new"
    MATCHING = "matching"
    AWAITING_OUTREACH = "awaiting_outreach"
    AWAITING_QUOTES = "awaiting_quotes"
    COMPARING = "comparing"
    AWAITING_AWARD = "awaiting_award"
    AWARDED = "awarded"
    SUBMITTED_TO_SAP = "submitted_to_sap"
    CANCELLED = "cancelled"


STATUS_LABELS_DE = {
    RequestStatus.NEW: "Neu",
    RequestStatus.MATCHING: "Lieferantensuche",
    RequestStatus.AWAITING_OUTREACH: "Freigabe Anfragen",
    RequestStatus.AWAITING_QUOTES: "Warte auf Angebote",
    RequestStatus.COMPARING: "Angebotsvergleich",
    RequestStatus.AWAITING_AWARD: "Auswahl getroffen",
    RequestStatus.AWARDED: "Auswahl bestätigt",
    RequestStatus.SUBMITTED_TO_SAP: "Beim Einkauf & in SAP eingereicht",
    RequestStatus.CANCELLED: "Abgebrochen",
}


@dataclass
class LineItem:
    description: str
    quantity: float
    unit: str


@dataclass
class Supplier:
    id: str
    name: str
    category: str
    subcategories: list[str]
    region: str
    city: str
    email: str
    phone: str
    rating: float
    avg_response_days: int
    typical_markup: float
    certifications: list[str]
    past_orders: int
    notes: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Supplier":
        return cls(**data)


@dataclass
class SupplierMatch:
    supplier: Supplier
    score: float
    reasons: list[str]
    selected: bool = True


@dataclass
class OutreachEmail:
    supplier_id: str
    supplier_name: str
    to_address: str
    subject: str
    body: str
    approved: bool = False
    sent: bool = False


@dataclass
class QuoteLineItem:
    description: str
    quantity: float
    unit: str
    unit_price: float
    total: float


@dataclass
class Quote:
    id: str
    supplier_id: str
    supplier_name: str
    request_id: str
    currency: str
    labor_total: float
    materials_total: float
    travel_total: float
    other_total: float
    total: float
    valid_until: str
    lead_time_days: int
    notes: str
    line_items: list[QuoteLineItem] = field(default_factory=list)
    received_at: str = ""
    is_preferred_incumbent: bool = False


@dataclass
class QuoteComparison:
    quotes: list[Quote]
    recommended_quote_id: str
    savings_vs_highest: float
    savings_vs_incumbent: float | None
    rationale: list[str]
    scorecard: list[dict[str, Any]]


@dataclass
class SourcingRequest:
    id: str
    title: str
    category: str
    subcategory: str
    description: str
    requester: str
    department: str
    cost_center: str
    site: str
    estimated_value_eur: float
    urgency: str
    needed_by: str
    created_at: str
    status: RequestStatus
    spec_quality: str
    line_items: list[LineItem]
    matches: list[SupplierMatch] = field(default_factory=list)
    emails: list[OutreachEmail] = field(default_factory=list)
    quotes: list[Quote] = field(default_factory=list)
    comparison: QuoteComparison | None = None
    awarded_quote_id: str | None = None
    sap_po_number: str | None = None
    activity_log: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourcingRequest":
        line_items = [LineItem(**li) for li in data.get("line_items", [])]
        status = data.get("status", "new")
        if isinstance(status, str):
            status = RequestStatus(status)
        return cls(
            id=data["id"],
            title=data["title"],
            category=data["category"],
            subcategory=data["subcategory"],
            description=data["description"],
            requester=data["requester"],
            department=data["department"],
            cost_center=data["cost_center"],
            site=data["site"],
            estimated_value_eur=data["estimated_value_eur"],
            urgency=data["urgency"],
            needed_by=data["needed_by"],
            created_at=data["created_at"],
            status=status,
            spec_quality=data.get("spec_quality", "high"),
            line_items=line_items,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
