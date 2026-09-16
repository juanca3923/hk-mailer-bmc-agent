"""Input validation models for MCP tool parameters."""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from bmc.libs.business_defaults import DEFAULT_INCIDENT_ASSIGNED_GROUP, DEFAULT_WORK_ORDER_ASSIGNED_GROUP
from bmc.libs.constants import (
    DEFAULT_INCIDENT_STATUS,
    DEFAULT_WORK_ORDER_STATUS,
    DEFAULT_WORK_ORDER_UPDATE_STATUS,
    INCIDENT_DESCRIPTION_MAX_LENGTH,
    INCIDENT_STATUSES,
    MAX_TICKETS_BY_EMAIL_RESULTS,
    WORK_ORDER_STATUSES,
)
from bmc.type_defs.ticket_status import (
    validate_incident_status,
    validate_optional_incident_status,
    validate_optional_work_order_status,
    validate_work_order_status,
)

WorkOrderStatusField = Annotated[str, BeforeValidator(validate_work_order_status)]
IncidentStatusField = Annotated[str, BeforeValidator(validate_incident_status)]
OptionalWorkOrderStatusField = Annotated[str | None, BeforeValidator(validate_optional_work_order_status)]
OptionalIncidentStatusField = Annotated[str | None, BeforeValidator(validate_optional_incident_status)]


class WorkOrderIdInput(BaseModel):
    """Input requiring a work order id."""

    work_order_id: str = Field(..., min_length=1, description="Work Order ID (e.g. WO0000000000228).")


class IncidentNumberInput(BaseModel):
    """Input requiring an incident number."""

    incident_number: str = Field(..., min_length=1, description="Incident Number (e.g. INC000000002106).")


class TicketsByEmailInput(BaseModel):
    """Input for listing tickets (work orders or incidents) by requester email."""

    email: str = Field(..., min_length=1, description="Requester email, as given to reporter_email at creation.")
    limit: int = Field(
        default=MAX_TICKETS_BY_EMAIL_RESULTS,
        ge=1,
        le=MAX_TICKETS_BY_EMAIL_RESULTS,
        description="Maximum number of rows to return; silently capped at this tool's own maximum.",
    )


class CreateWorkOrderInput(BaseModel):
    """Parameters to create a work order in BMC.

    Company, customer identity and the Support Company/Organization (BMC only honors
    the caller's ``Support Group Name`` when these two travel together in the same
    payload) are injected from ``business_defaults`` by the tool layer and are not
    part of this input. The submitter's ``First Name``/``Last Name`` are NOT a fixed
    default: they are resolved from ``reporter_email`` via BMC's ``CTM:People``
    (see ``bmc.libs.helpers.person_lookup``) so the ticket is attributed to the real
    person, not this agent's service-account persona. The five categorization fields
    are always required: from a matching ``categorias-<dominio>`` skill row when one
    applies, or from the fixed catch-all combination documented in
    ``guia-creacion-tickets`` (section 1) when no domain applies — never a fixed
    default in code, so the service desk can change that combination by editing the
    skill file alone, without redeploying the agent.
    """

    summary: str = Field(
        ...,
        min_length=1,
        description=(
            "Short, specific subject line: what is requested and for whom or which "
            'system (e.g. "New network user - Juan Perez, Bogota site"), never a '
            'generic label like "User request".'
        ),
    )
    reporter_email: str = Field(
        ...,
        min_length=1,
        description=(
            "Email of the person requesting this, looked up in BMC's CTM:People to "
            "fill the submitter First Name/Last Name (not the fixed Customer "
            "identity) with the real requester. Creation fails with no ticket "
            "created if no matching person is found in BMC."
        ),
    )
    detailed_description: str = Field(
        ...,
        min_length=1,
        description=(
            "Full request detail: who needs it, exactly what must be done, and any "
            "data required to execute it (access, equipment, location, dates) - "
            "enough for the service desk to act without asking the user again."
        ),
    )
    categorization_tier_1: str = Field(
        ...,
        min_length=1,
        description=(
            "Operational categorization tier 1: from the matching categorias-<dominio> "
            "skill row when one applies, otherwise the fixed catch-all combination from "
            "guia-creacion-tickets (section 1) — never invent a value."
        ),
    )
    categorization_tier_2: str = Field(
        ...,
        min_length=1,
        description="Operational categorization tier 2, same row/catch-all as tier 1.",
    )
    product_cat_tier_1: str = Field(
        ...,
        min_length=1,
        description="Product categorization tier 1, same row/catch-all as categorization_tier_1.",
    )
    product_cat_tier_2: str = Field(
        ...,
        min_length=1,
        description="Product categorization tier 2, same row/catch-all as categorization_tier_1.",
    )
    product_cat_tier_3: str = Field(
        ...,
        min_length=1,
        description="Product categorization tier 3, same row/catch-all as categorization_tier_1.",
    )
    status: WorkOrderStatusField = Field(
        default=DEFAULT_WORK_ORDER_STATUS,
        description="Work order status label.",
        json_schema_extra={"enum": list(WORK_ORDER_STATUSES)},
    )
    priority: str = Field(
        default="Medium",
        description="Priority, taken from the same catalog row as the categorization tiers.",
    )

    assigned_group: str = Field(
        default=DEFAULT_WORK_ORDER_ASSIGNED_GROUP,
        min_length=1,
        description=(
            "Support group, taken from the same catalog row; keep the default only when no "
            "domain skill applies."
        ),
    )


class CreateIncidentInput(BaseModel):
    """Parameters to create an incident in BMC.

    Company, assigned group and the Assigned Support Company/Organization (BMC only
    honors the caller's ``Assigned Group`` when these two travel together in the same
    payload) are injected from ``business_defaults`` by the tool layer and are not
    part of this input. The submitter's ``First_Name``/``Last_Name`` are NOT a fixed
    default: they are resolved from ``reporter_email`` via BMC's ``CTM:People`` (see
    ``bmc.libs.helpers.person_lookup``) so the ticket is attributed to the real
    person, not this agent's service-account persona.
    """

    description: str = Field(
        ...,
        min_length=1,
        max_length=INCIDENT_DESCRIPTION_MAX_LENGTH,
        description=(
            f"Short, specific subject line (hard limit: {INCIDENT_DESCRIPTION_MAX_LENGTH} "
            "characters, rejected by BMC above that): which service/system is affected and "
            'the concrete symptom (e.g. "Payroll app down for all users at Medellin site"), '
            'never a generic label like "System not working". Put any extra detail in '
            "``detailed_decription`` instead of exceeding this limit."
        ),
    )
    reporter_email: str = Field(
        ...,
        min_length=1,
        description=(
            "Email of the person reporting this, looked up in BMC's CTM:People to "
            "fill the submitter First_Name/Last_Name (not the fixed Customer "
            "identity) with the real reporter. Creation fails with no ticket "
            "created if no matching person is found in BMC."
        ),
    )
    detailed_decription: str = Field(
        ...,
        min_length=1,
        description=(
            "Full incident detail: who reported it, when it started, the exact "
            "symptom observed, the affected system/application, and scope (how many "
            "users or which site) - enough to diagnose without asking the user again."
        ),
    )
    status: IncidentStatusField = Field(
        default=DEFAULT_INCIDENT_STATUS,
        description="Incident status.",
        json_schema_extra={"enum": list(INCIDENT_STATUSES)},
    )
    reported_source: str = Field(default="Direct Input", description="Reported source.")
    service_type: str = Field(default="User Service Restoration", description="Service type.")
    categorization_tier_1: str = Field(default="", description="Operational categorization tier 1, same catalog row.")
    categorization_tier_2: str = Field(default="", description="Operational categorization tier 2, same catalog row.")
    product_categorization_tier_1: str = Field(
        ...,
        min_length=1,
        description="Product categorization tier 1, from the matching categorias-<dominio> skill row.",
    )
    product_categorization_tier_2: str = Field(
        ..., min_length=1, description="Product categorization tier 2, same catalog row."
    )
    product_categorization_tier_3: str = Field(
        ..., min_length=1, description="Product categorization tier 3, same catalog row."
    )
    assigned_group: str = Field(
        default=DEFAULT_INCIDENT_ASSIGNED_GROUP,
        min_length=1,
        description=(
            "Assigned group, taken from the same catalog row; keep the default only when the "
            "catalog row does not specify one."
        ),
    )


class AddWorkOrderNoteInput(WorkOrderIdInput):
    """Add a work log note to a work order."""

    note_text: str = Field(
        ..., min_length=1, description="Text of the note, written as it should be read by whoever reviews the ticket."
    )
    work_log_type: str = Field(
        default="General Information",
        description="Category of the note in the ticket activity log; keep the default unless asked otherwise.",
    )
    view_access: str = Field(
        default="Public", description="Visibility of the note in BMC; keep the default unless asked otherwise."
    )
    secure_work_log: str = Field(
        default="No",
        description="Whether the note is flagged as secure in BMC; keep the default unless asked otherwise.",
    )


class AddWorkOrderAttachmentInput(AddWorkOrderNoteInput):
    """Add a work log note with file attachment to a work order."""

    file_path: str = Field(..., min_length=1, description="Local path readable by the MCP server.")


class AddIncidentNoteInput(IncidentNumberInput):
    """Add a work log note to an incident."""

    note_text: str = Field(
        ..., min_length=1, description="Text of the note, written as it should be read by whoever reviews the ticket."
    )
    work_log_type: str = Field(
        default="General Information",
        description="Category of the note in the ticket activity log; keep the default unless asked otherwise.",
    )
    view_access: str = Field(
        default="Public", description="Visibility of the note in BMC; keep the default unless asked otherwise."
    )
    secure_work_log: str = Field(
        default="No",
        description="Whether the note is flagged as secure in BMC; keep the default unless asked otherwise.",
    )


class AddIncidentAttachmentInput(AddIncidentNoteInput):
    """Add a work log note with file attachment to an incident."""

    file_path: str = Field(..., min_length=1, description="Local path readable by the MCP server.")


class UpdateWorkOrderStatusInput(WorkOrderIdInput):
    """Update work order status (intermediate step)."""

    description: str = Field(
        ..., min_length=1, description="What changed and why; BMC also uses this text as the ticket title."
    )
    status: WorkOrderStatusField = Field(
        default=DEFAULT_WORK_ORDER_UPDATE_STATUS,
        description="Target status.",
        json_schema_extra={"enum": list(WORK_ORDER_STATUSES)},
    )


class CloseWorkOrderInput(WorkOrderIdInput):
    """Close a work order (orchestrates ownership PUT + Completed PUT + Closed PUT).

    The intermediate ``Status`` is always ``'Completed'`` and the final ``Status`` is
    always ``'Closed'``; neither is a caller-supplied parameter, matching bmc-mcp.
    """

    intermediate_description: str = Field(
        default="Rest API: Resolve WO using RestAPI",
        min_length=1,
        description="Summary of the work actually performed, recorded when moving to Completed.",
    )
    final_description: str = Field(
        default="Rest API: Resolve Work order via Mosaico",
        min_length=1,
        description="Documentation of the final solution, recorded when moving to Closed.",
    )


class CloseIncidentInput(IncidentNumberInput):
    """Close an incident (orchestrates ownership PUT + close PUT).

    The intermediate ``Status`` (ownership) is always ``'In Progress'`` and the final
    ``Status`` is always ``'Resolved'``; neither is a caller-supplied parameter. ``Status
    Reason`` is always ``'Closing'``, matching bmc-mcp.
    """

    description: str = Field(
        ...,
        min_length=1,
        max_length=INCIDENT_DESCRIPTION_MAX_LENGTH,
        description=(
            f"Short closing summary (hard limit: {INCIDENT_DESCRIPTION_MAX_LENGTH} "
            "characters, rejected by BMC above that) — summarize, do not narrate the full "
            "resolution here. Put the full explanation in ``resolution`` instead, or as a "
            "separate note via ``bmc_add_incident_note`` before closing."
        ),
    )
    resolution: str = Field(
        default="Solución no especificada",
        min_length=1,
        description="How the incident was actually solved; replace the placeholder default.",
    )
