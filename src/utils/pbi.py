import os
import urllib.parse
from typing import Dict, Any, Optional, List


def build_pbi_deeplink(
    filters: Dict[str, Any], expressions: Optional[List[str]] = None
) -> Optional[str]:
    """Build a Power BI report link with simple filters.

    Requires env vars: `PBI_WORKSPACE_ID`, `PBI_REPORT_ID`.
    Filters is a mapping like {"Table/Column": "Value", ...}.
    """
    ws = os.getenv("PBI_WORKSPACE_ID")
    rep = os.getenv("PBI_REPORT_ID")
    if not ws or not rep:
        return None

    base = f"https://app.powerbi.com/groups/{ws}/reports/{rep}/ReportSection"
    # Build `filter` query with AND of each expression
    # Start with custom expressions (e.g., date ranges) then add equality filters
    exprs: List[str] = []
    if expressions:
        exprs.extend([str(e) for e in expressions if e])
    for col, val in filters.items():
        if isinstance(val, str):
            v = f"'{val}'"
        else:
            v = str(val)
        exprs.append(f"{col} eq {v}")
    q = urllib.parse.urlencode({"filter": " and ".join(exprs)}) if exprs else ""
    return f"{base}?{q}" if q else base
