from __future__ import annotations
from typing import Any, Dict, Iterable, Optional, Union, List, Iterator

# Orders mixin lives separate from the base client.
class OrdersMixin:
    # --- Low-level search wrapper (Order Search) ---
    def search_orders(
        self,
        *,
        columns: Optional[List[str]] = None,
        sort: Optional[str] = None,          # e.g. "updatedOn:DESC" or "orderId:ASC"
        page_size: int = 100,
        page: Optional[int] = 1,             # if provided, we'll compute firstResult
        first_result: Optional[int] = None,  # alternative to page
        **filters: Any,                      # e.g. updatedOn, orderStatusId, externalRefSearchString, etc.
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"pageSize": page_size}
        if columns:
            params["columns"] = ",".join(columns)
        if sort:
            # Orders search uses 'orderBy' rather than 'sort'
            params["orderBy"] = sort

        # Pagination: some deployments expect 'page' param, others 'firstResult'.
        # Prefer explicit first_result; otherwise use 'page' to avoid 500s observed with firstResult.
        if first_result is not None:
            params["firstResult"] = int(first_result)
        elif page is not None:
            params["page"] = int(page)

        # Pass through Brightpearl search filters verbatim
        params.update(filters)

        # Order search on this deployment uses GET with query params
        # (keeps filters/pagination applied correctly across accounts)
        return self._request("GET", "order-service/order-search", params=params)

    # --- Backwards-friendly list_* that uses search under the hood ---
    def list_orders(
        self,
        *,
        page_size: int = 100,
        page: int = 1,
        order_by: Optional[str] = None,      # maps to sort
        columns: Optional[List[str]] = None,
        **filters: Any,
    ) -> Dict[str, Any]:
        # Don't force a default projection; some fields vary by account.
        # If provided, keep as-is. If sorting, we don't require the field
        # to be in the projection for orders.
        sort = None
        if order_by:
            # support "updatedOn" or "-updatedOn" style
            if order_by.startswith("-"):
                sort = f"{order_by[1:]}:DESC"
            else:
                sort = f"{order_by}:ASC"

        return self.search_orders(
            columns=columns,
            sort=sort,
            page_size=page_size,
            page=page,
            **filters,
        )

    def list_orders_records(
        self,
        *,
        page_size: int = 100,
        page: int = 1,
        order_by: Optional[str] = None,
        columns: Optional[List[str]] = None,
        **filters: Any,
    ) -> List[Dict[str, Any]]:
        payload = self.list_orders(
            page_size=page_size,
            page=page,
            order_by=order_by,
            columns=columns,
            **filters,
        )
        return self._normalize_search_response(payload)

    def iter_orders(
        self,
        *,
        page_size: int = 100,
        order_by: Optional[str] = None,
        columns: Optional[List[str]] = None,
        **filters: Any,
    ) -> Iterator[Dict[str, Any]]:
        page = 1
        while True:
            payload = self.list_orders(page_size=page_size, page=page,
                                       order_by=order_by, columns=columns, **filters)
            response = payload.get("response") or {}
            results = response.get("results") or []
            if not results:
                break
            yield response
            if len(results) < page_size:
                break
            page += 1

    def iter_orders_records(
        self,
        *,
        page_size: int = 100,
        order_by: Optional[str] = None,
        columns: Optional[List[str]] = None,
        **filters: Any,
    ) -> Iterator[Dict[str, Any]]:
        page = 1
        while True:
            payload = self.list_orders(
                page_size=page_size,
                page=page,
                order_by=order_by,
                columns=columns,
                **filters,
            )
            response = payload.get("response") or {}
            records = self._normalize_search_response_from_response(response)
            if not records:
                break
            for rec in records:
                yield rec
            if len(records) < page_size:
                break
            page += 1

    # --- Other order endpoints that still require IDs ---
    def get_order(self, order_id: Union[int, str]) -> Dict[str, Any]:
        return self._request("GET", f"order-service/order/{order_id}")

    def get_orders_bulk(self, order_ids: Iterable[Union[int, str]]) -> Dict[str, Any]:
        ids = ",".join(str(i) for i in order_ids)
        return self._request("GET", "order-service/order", params={"orderId": ids})

    def create_order(self, order_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "order-service/order", json=order_payload)

    def patch_order(self, order_id: Union[int, str], patch_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("PATCH", f"order-service/order/{order_id}", json=patch_payload)

    def replace_order(self, order_id: Union[int, str], order_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("PUT", f"order-service/order/{order_id}", json=order_payload)

    def add_order_note(self, order_id: Union[int, str], text: str, is_public: bool = True) -> Dict[str, Any]:
        payload = {"text": text, "isPublic": is_public}
        return self._request("POST", f"order-service/order/{order_id}/note", json=payload)

    def list_order_notes(self, order_id: Union[int, str]) -> Dict[str, Any]:
        return self._request("GET", f"order-service/order/{order_id}/note")

    def update_order_status(self, order_id: Union[int, str], status_id: int) -> Dict[str, Any]:
        return self.patch_order(order_id, {"statusId": status_id})
