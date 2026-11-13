"""Nombres de los campos AR de BMC Helix."""

from __future__ import annotations

from typing import Final

DETAIL_DESCRIPTION_FIELD: Final[str] = "Detailed Description"


CATEGORIZATION_TIER_1_FIELD: Final[str] = "Categorization Tier 1"


CATEGORIZATION_TIER_2_FIELD: Final[str] = "Categorization Tier 2"


AR_FIELD_WORK_ORDER_ID: Final[str] = "Work Order ID"


AR_FIELD_ASSIGNEE: Final[str] = "Assignee"


AR_FIELD_INCIDENT_NUMBER: Final[str] = "Incident Number"


AR_FIELD_REQUEST_ID: Final[str] = "Request ID"


AR_FIELD_WORK_ORDER_ID_RESPONSE: Final[str] = "WorkOrder_ID"


AR_FIELD_STATUS: Final[str] = "Status"


AR_FIELD_SUBMITTER: Final[str] = "Submitter"


AR_FIELD_CATEGORIZATION_TIER_1: Final[str] = "Categorization Tier 1"


AR_FIELD_CATEGORIZATION_TIER_2: Final[str] = "Categorization Tier 2"


# CTM:People (reporter identity lookup by email — see services.bmc.person_lookup)
AR_FIELD_PEOPLE_LOGIN_ID: Final[str] = "Remedy Login ID"


AR_FIELD_PEOPLE_FIRST_NAME: Final[str] = "First Name"


AR_FIELD_PEOPLE_LAST_NAME: Final[str] = "Last Name"


AR_FIELD_PEOPLE_EMAIL: Final[str] = "Internet E-mail"


# Whether the person is active ("Enabled"; other values: "Offline", "Obsolete", ...). The field name is
# not in BMC's public docs and still has to be confirmed against the real instance (GET a person
# without ``fields`` and look for the one that says "Enabled"); this is the only place it is defined.
AR_FIELD_PEOPLE_STATUS: Final[str] = "Profile Status"


# Requester-email fields used to list tickets by requester (verified empirically
# against BMC: each form stores the raw reporter_email in a different field — WO
# keeps it on the fixed "Customer" identity's email field, INC keeps it on its own
# "Internet E-mail"; neither is the CTM:People-resolved login id).
AR_FIELD_WO_CUSTOMER_EMAIL: Final[str] = "Customer Internet E-mail"


AR_FIELD_INCIDENT_REPORTER_EMAIL: Final[str] = "Internet E-mail"


# Assigned-group fields for reading back a ticket's current group (not the same field
# used to *set* it at creation). For incidents, "Assigned Group" round-trips correctly —
# same alias as CreateIncidentValues.assigned_group. For work orders, the create-time
# alias ("Support Group Name", CreateWorkOrderValues.assigned_group) does NOT round-trip:
# verified empirically against BMC that reading it back always shows the fixed desk
# default ("SOPORTE MESA DE SERVICIO") regardless of what was requested at creation,
# while "ASGRP" (BMC's internal assignment-engine field) does reflect the real group.
AR_FIELD_WORK_ORDER_ASGRP: Final[str] = "ASGRP"


AR_FIELD_INCIDENT_ASSIGNED_GROUP: Final[str] = "Assigned Group"


AR_ACTION_CREATE: Final[str] = "CREATE"


AR_Z1D_ACTION_CREATE: Final[str] = "CREATE"


AR_Z1D_ACTION_FIELD_WO: Final[str] = "z1D_Action"


AR_Z1D_ACTION_FIELD_WORK_INFO: Final[str] = "z1D Action"


WORK_LOG_ATTACHMENT_FIELD: Final[str] = "z2AF Work Log01"
