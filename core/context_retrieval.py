"""
Step 4: Bring the right context into the discussion.

Before extraction, pull:
  1. The compliance policy / script relevant to this call type (RAG over a
     policy doc store).
  2. Prior history for this customer/deal (CRM lookup), if available.

Context is returned as a clearly-labelled block so the extraction prompt
can keep "policy text" and "what the speaker actually said" separate --
this is what stops the model from treating policy language as a quote.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

# --- Mock policy store -----------------------------------------------------
# In production: vector DB (e.g. Chroma/pgvector) over your compliance docs,
# queried by call_type. Kept as a plain dict here to keep the module runnable
# without external services.
POLICY_STORE = {
    "collections": (
        "FDCPA-aligned collections policy:\n"
        "- Agent must not threaten legal action unless action is actually intended and lawful.\n"
        "- Any payment plan / settlement that deviates from standard terms requires supervisor approval.\n"
        "- If a consumer says any variant of 'stop calling me' / 'don't contact me' / "
        "'take me off your list', this is a cease-and-desist request and must be honored; "
        "flag for compliance review immediately.\n"
        "- If a consumer mentions bankruptcy, collections activity must pause pending verification.\n"
        "- Consumer consent to recording must be confirmed at call start where required by state law."
    ),
    "support": (
        "Support policy:\n"
        "- Agent should not promise refunds/credits beyond their authorization tier without escalation.\n"
        "- Data changes to a customer's account require identity verification."
    ),
    "sales": (
        "Sales policy:\n"
        "- Pricing discounts beyond the published discount table require manager approval.\n"
        "- Do not make guarantees about future product features not yet released."
    ),
    "standup": "No special compliance policy; general internal meeting norms apply.",
}


@dataclass
class RetrievedContext:
    policy_text: str
    crm_summary: Optional[str]


def get_policy_context(call_type: str) -> str:
    return POLICY_STORE.get(call_type, POLICY_STORE["support"])


def get_crm_context(customer_id: Optional[str]) -> Optional[str]:
    """
    Placeholder for a real CRM lookup (Salesforce/HubSpot/internal API).
    Returns None if no customer_id is available -- extraction prompts must
    treat missing context as missing, not paper over it.
    """
    if customer_id is None:
        return None
    # Mock example record
    return (
        f"Customer {customer_id}: 2 prior collections calls, "
        f"last payment plan agreed 2026-05-01, no prior cease-and-desist on file."
    )


def retrieve_context(call_type: str, customer_id: Optional[str] = None) -> RetrievedContext:
    return RetrievedContext(
        policy_text=get_policy_context(call_type),
        crm_summary=get_crm_context(customer_id),
    )


def render_context_block(ctx: RetrievedContext) -> str:
    """Rendered with explicit tags so the model never mistakes policy text
    or CRM history for something a speaker said on this call."""
    parts = [f"<policy>\n{ctx.policy_text}\n</policy>"]
    if ctx.crm_summary:
        parts.append(f"<crm_history>\n{ctx.crm_summary}\n</crm_history>")
    return "\n\n".join(parts)
