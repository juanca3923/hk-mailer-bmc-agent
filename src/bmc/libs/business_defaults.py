"""Business-specific default values for BMC ticket creation.

Constants are resolved at import time: environment variable first,
hardcoded fallback second. To override without touching code, set the
corresponding ``BMC_DEFAULT_*`` variable before starting the process.
"""

import os
from typing import Final

DEFAULT_COMPANY: Final[str] = os.getenv('BMC_DEFAULT_COMPANY', 'ARUS')
DEFAULT_FIRST_NAME: Final[str] = os.getenv('BMC_DEFAULT_FIRST_NAME', 'Agentes')
DEFAULT_LAST_NAME: Final[str] = os.getenv('BMC_DEFAULT_LAST_NAME', 'IA')
DEFAULT_CUSTOMER_FIRST_NAME: Final[str] = os.getenv('BMC_DEFAULT_CUSTOMER_FIRST_NAME', 'Mosaico')
DEFAULT_CUSTOMER_LAST_NAME: Final[str] = os.getenv('BMC_DEFAULT_CUSTOMER_LAST_NAME', 'IA')
DEFAULT_CUSTOMER_COMPANY: Final[str] = os.getenv('BMC_DEFAULT_CUSTOMER_COMPANY', 'ARUS')
DEFAULT_INCIDENT_ASSIGNED_GROUP: Final[str] = os.getenv('BMC_DEFAULT_ASSIGNED_GROUP', 'MESA MARCO')
DEFAULT_INCIDENT_SUPPORT_COMPANY: Final[str] = os.getenv('BMC_DEFAULT_INCIDENT_SUPPORT_COMPANY', 'ARUS')
DEFAULT_INCIDENT_SUPPORT_ORGANIZATION: Final[str] = os.getenv('BMC_DEFAULT_INCIDENT_SUPPORT_ORGANIZATION', 'MAYA')
DEFAULT_WORK_ORDER_ASSIGNED_GROUP: Final[str] = os.getenv('BMC_DEFAULT_WORK_ORDER_ASSIGNED_GROUP', 'MESA MARCO')
DEFAULT_WORK_ORDER_SUPPORT_COMPANY: Final[str] = os.getenv('BMC_DEFAULT_WORK_ORDER_SUPPORT_COMPANY', 'ARUS')
DEFAULT_WORK_ORDER_SUPPORT_ORGANIZATION: Final[str] = os.getenv('BMC_DEFAULT_WORK_ORDER_SUPPORT_ORGANIZATION', 'MAYA')
