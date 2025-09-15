from __future__ import annotations

import time
from typing import Any, Dict, Optional, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class BrightpearlAPIError(Exception):
    """Raised when the Brightpearl API returns an error response."""
    def __init__(self, message: str, status: int | None = None, payload: Any | None = None):
        super().__init__(message)
        self.status = status
        self.payload = payload


class _BaseClient:
    """
    Holds connection details, session, retries, and low-level _request().
    Feature mixins (orders, products, etc.) subclass this.
    """
    def __init__(self,domain: str,account_id: str,account_token: str,app_ref: str,*,timeout: int = 30,max_retries: int = 3,backoff_factor: float = 0.5,):
        if not domain.startswith("http"):
            raise ValueError("domain must include scheme, e.g. https://ws-use.brightpearl.com")

        # Optional host normalization (keeps your current inputs working)
        _raw = domain.strip()
        aliases = {
            "use1.brightpearlconnect.com": "https://use1.brightpearlconnect.com",
            "ws-use.brightpearlconnect.com": "https://ws-use.brightpearlconnect.com",
        }
        host = _raw.replace("https://", "").replace("http://", "").strip("/")
        if host in aliases:
            _raw = aliases[host]

        self.domain = _raw.rstrip("/")
        self.account_id = account_id
        self.base_url = f"{self.domain}/public-api/{self.account_id}"
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "brightpearl-app-ref": app_ref,
            "brightpearl-account-token": account_token,
        })

        retry = Retry(
            total=max_retries,
            read=max_retries,
            connect=max_retries,
            status=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "POST", "PATCH", "PUT"}),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _request(self, method: str,path: str,*,params: Optional[Dict[str, Any]] = None,json: Optional[Dict[str, Any]] = None,) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = self.session.request(method, url, params=params, json=json, timeout=self.timeout)

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                try:
                    time.sleep(float(retry_after))
                except Exception:
                    pass

        if not (200 <= resp.status_code < 300):
            try:
                payload = resp.json()
            except Exception:
                payload = {"text": resp.text}
            raise BrightpearlAPIError(
                f"Brightpearl API {method} {url} failed with {resp.status_code}",
                status=resp.status_code,
                payload=payload,
            )

        try:
            return resp.json()
        except ValueError:
            return {}

    # --- Helpers: normalize Brightpearl search responses ---
    def _normalize_search_response(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert a Brightpearl search payload into a list of dicts.

        Expects a top-level payload with a "response" object that includes
        metaData/columns and results (often a list of arrays). This maps each
        result row to a dict keyed by column names.
        """
        response = payload.get("response") or {}
        return self._normalize_search_response_from_response(response)

    def _normalize_search_response_from_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        meta = response.get("metaData") or {}
        cols = meta.get("columns") or response.get("columns")

        names: List[str] = []
        if isinstance(cols, list):
            if cols and isinstance(cols[0], dict):
                for c in cols:
                    n = (
                        c.get("name")
                        or c.get("columnName")
                        or c.get("code")
                        or c.get("fieldName")
                        or ""
                    )
                    names.append(n)
            else:
                names = [str(c) for c in cols]
        elif isinstance(cols, str):
            names = [c.strip() for c in cols.split(",") if c.strip()]

        results = response.get("results") or []
        records: List[Dict[str, Any]] = []
        for row in results:
            if isinstance(row, dict):
                records.append(row)
            elif isinstance(row, (list, tuple)):
                rec: Dict[str, Any] = {}
                for i, v in enumerate(row):
                    key = names[i] if i < len(names) else f"col_{i}"
                    rec[key] = v
                records.append(rec)
            else:
                records.append({"value": row})
        return records
