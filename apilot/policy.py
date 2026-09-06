"""Policy-aware AP controls: exception routing and posting-status rules.

Each matcher finding type routes to a finance owner with a recommended
action; posting status derives from the decision and the latest human review:
clean decisions auto-post, exception decisions block until reviewed, and the
latest review verdict (approve/hold/escalate) resolves the block.
"""
from dataclasses import dataclass
from typing import Optional

# Posting statuses (decision/audit field + live derived value).
STATUS_AUTO_POSTED = "AUTO_POSTED"
STATUS_BLOCKED = "BLOCKED_FOR_REVIEW"
STATUS_OVERRIDE_APPROVED = "OVERRIDE_APPROVED"
STATUS_ON_HOLD = "ON_HOLD"
STATUS_ESCALATED = "ESCALATED"
ALL_STATUSES = (
    STATUS_AUTO_POSTED,
    STATUS_BLOCKED,
    STATUS_OVERRIDE_APPROVED,
    STATUS_ON_HOLD,
    STATUS_ESCALATED,
)

# Review verdict -> posting status once a blocked invoice is reviewed.
VERDICT_TO_STATUS = {
    "approve": STATUS_OVERRIDE_APPROVED,
    "hold": STATUS_ON_HOLD,
    "escalate": STATUS_ESCALATED,
}

# Severity drives which finding owns routing when several fire at once.
SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class Route:
    """Control rule + finance owner + next action for one finding type."""

    policy_rule: str
    review_owner: str
    recommended_action: str


# Exception type -> owner/action routing.
ROUTES = {
    "PRICE_MISMATCH": Route(
        "price tolerance",
        "AP/procurement",
        "reconcile unit price with procurement",
    ),
    "QTY_MISMATCH": Route(
        "qty match",
        "Receiving",
        "verify received quantity",
    ),
    "MISSING_RECEIPT": Route(
        "receipt check",
        "Receiving",
        "confirm goods receipt",
    ),
    "MISSING_PO": Route(
        "po check",
        "Procurement/AP",
        "locate or create the purchase order",
    ),
    "DUPLICATE_INVOICE": Route(
        "duplicate check",
        "AP manager",
        "review the duplicate invoice pair",
    ),
    "TAX_MISMATCH": Route(
        "tax uplift check",
        "Tax/controller",
        "confirm tax handling with tax/controller",
    ),
    "UNKNOWN_VENDOR": Route(
        "vendor & currency check",
        "Vendor master/AP manager",
        "validate vendor master and currency",
    ),
}

AUTO_POST_ROUTE = Route(
    policy_rule="clean three-way match",
    review_owner="",
    recommended_action="post to ERP",
)


def route(findings) -> Route:
    """Resolve a list of findings to one route.

    The highest-severity finding owns routing; ties keep matcher order, so a
    multi-finding invoice gets one deterministic owner/action.
    """
    primary = min(findings, key=lambda f: SEVERITY_RANK[f.severity])
    return ROUTES[primary.type]


def posting_status(action: str, latest_review: Optional[dict] = None) -> str:
    """Effective posting status from the decision action and latest review.

    Clean (AUTO_POST) decisions are posted with no human touch. Exception
    decisions are blocked until the latest review overrides the block.
    """
    if action == "AUTO_POST":
        return STATUS_AUTO_POSTED
    if latest_review is None:
        return STATUS_BLOCKED
    return VERDICT_TO_STATUS[latest_review["verdict"]]
