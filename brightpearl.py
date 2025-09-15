# brightpearl_orders.py
from __future__ import annotations

import time
from typing import Any, Dict, Iterable, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class BrightpearlAPIError(Exception):
    """Raised when the Brightpearl API returns an error response."""
    def __init__(self, message: str, status: int | None = None, payload: Any | None = None):
        super().__init__(message)
        self.status = status
        self.payload = payload


class BrightpearlAPI:
    """
        domain:        e.g. "https://use1.brightpearlconnect.com" etc.
        account_id:    your Brightpearl ACCOUNT ID (e.g. "mybusinessname")
        account_token: your Brightpearl ACCOUNT TOKEN
        app_ref:       your Brightpearl APP REF

    Example:
        api = BrightpearlAPI(
            domain="https://use1.brightpearlconnect.com",
            account_id="mybusinessname",
            account_token="XXXXXXXXXXXXXXXXXXXXXXXXXXX",
            app_ref="someapprefname",
        )
        order = api.get_order(67890)
        print(order)
    """

    def __init__(
        self,
        domain: str,
        account_id: str,
        account_token: str,
        app_ref: str,
        *,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        if not domain.startswith("http"):
            raise ValueError("domain must include scheme, e.g. https://use1.brightpearlconnect.com")

        self.domain = domain.rstrip("/")
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

        # Robust retries for transient errors and 429s
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

    # ---------------------------
    # Internal helpers
    # ---------------------------

    def _request(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None,) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = self.session.request(method, url, params=params, json=json, timeout=self.timeout)

        # Handle Brightpearl rate-limit guidance if present
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
            # Some endpoints may respond with empty bodies
            return {}

    # ---------------------------
    # Orders: common operations
    # ---------------------------

    def list_orders(self, *, page_size: int = 100, page: int = 1, order_by: Optional[str] = None, **filters: Any,) -> Dict[str, Any]:
        """
        List/search orders.

        Common filters (pass as kwargs): orderTypeId, statusId, createdOn, createdOnFrom, createdOnTo,
            updatedOnFrom, updatedOnTo, reference, customerRef, orderId,
            placedOnFrom, placedOnTo, etc.

        Returns Brightpearl's paging wrapper with 'response'.
        """
        params: Dict[str, Any] = {"pageSize": page_size, "page": page}
        if order_by:
            params["orderBy"] = order_by
        params.update(filters)
        return self._request("GET", "order-service/order", params=params)

    def get_order(self, order_id: Union[int, str]) -> Dict[str, Any]:
        """Fetch a single order by ID."""
        return self._request("GET", f"order-service/order/{order_id}")

    def get_orders_bulk(self, order_ids: Iterable[Union[int, str]]) -> Dict[str, Any]:
        """
        Fetch multiple orders by IDs (server-side batching where supported).
        """
        ids = ",".join(str(i) for i in order_ids)
        return self._request("GET", "order-service/order", params={"orderId": ids})

    def create_order(self, order_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an order.
        The payload should follow Brightpearl's schema for order creation.
        """
        return self._request("POST", "order-service/order", json=order_payload)

    def patch_order(self, order_id: Union[int, str], patch_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Partially update an order (e.g., change statusId, references, custom fields).
        """
        return self._request("PATCH", f"order-service/order/{order_id}", json=patch_payload)

    def replace_order(self, order_id: Union[int, str], order_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replace an order (PUT).
        """
        return self._request("PUT", f"order-service/order/{order_id}", json=order_payload)

    def add_order_note(self, order_id: Union[int, str], text: str, is_public: bool = True) -> Dict[str, Any]:
        """
        Add a note/comment to an order.
        """
        payload = {
            "text": text,
            "isPublic": is_public,
        }
        return self._request("POST", f"order-service/order/{order_id}/note", json=payload)

    def list_order_notes(self, order_id: Union[int, str]) -> Dict[str, Any]:
        """Retrieve notes attached to an order."""
        return self._request("GET", f"order-service/order/{order_id}/note")

    def update_order_status(self, order_id: Union[int, str], status_id: int) -> Dict[str, Any]:
        """
        Convenience: update just the statusId using PATCH.
        """
        return self.patch_order(order_id, {"statusId": status_id})

    # ---------------------------
    # Utility: rate limit info
    # ---------------------------

    @property
    def last_rate_limit(self) -> Dict[str, Optional[str]]:
        """
        Returns the last-known rate-limit headers if any (best-effort).
        Note: requests.Session does not keep per-request headers,
        so consider extending _request to stash them per call if you need this.
        Here we keep as placeholders for future extension.
        """
        # To implement precisely, capture headers inside _request and store on self.
        return {
            "limit": None,
            "remaining": None,
            "reset": None,
        }
