from __future__ import annotations
from typing import Any, Dict, Iterable, Iterator, List, Optional, Union

class ProductsMixin:
    # --- Low-level search wrapper (Product Search) ---
    def search_products(
        self,
        *,
        columns: Optional[List[str]] = None,
        sort: Optional[str] = None,          # e.g. "updatedOn:DESC"
        page_size: int = 100,
        page: Optional[int] = 1,             # convenience -> firstResult
        first_result: Optional[int] = None,
        **filters: Any,                      # e.g. SKU="...", productName="...", brandId=..., updatedOn=...
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"pageSize": page_size}
        if columns:
            params["columns"] = ",".join(columns)
        if sort:
            params["sort"] = sort

        # Pagination: mirror orders behavior for compatibility across accounts
        if first_result is not None:
            params["firstResult"] = int(first_result)
        elif page is not None:
            params["page"] = int(page)

        params.update(filters)
        # Product search on this deployment expects GET with query params
        # (JSON bodies on GET are ignored, which led to unfiltered results).
        return self._request("GET", "product-service/product-search", params=params)

    # --- Backwards-friendly list_* that uses search under the hood ---
    def list_products(
        self,
        *,
        page_size: int = 100,
        page: int = 1,
        order_by: Optional[str] = None,      # maps to sort
        columns: Optional[List[str]] = None,
        **filters: Any,
    ) -> Dict[str, Any]:
        if columns is None:
            columns = ["productId", "SKU", "productName", "brandId", "productTypeId", "updatedOn"]
        sort = None
        if order_by:
            sort = f"{order_by[1:]}:DESC" if order_by.startswith("-") else f"{order_by}:ASC"

        return self.search_products(
            columns=columns,
            sort=sort,
            page_size=page_size,
            page=page,
            **filters,
        )

    def list_products_records(
        self,
        *,
        page_size: int = 100,
        page: int = 1,
        order_by: Optional[str] = None,
        columns: Optional[List[str]] = None,
        **filters: Any,
    ) -> List[Dict[str, Any]]:
        payload = self.list_products(
            page_size=page_size,
            page=page,
            order_by=order_by,
            columns=columns,
            **filters,
        )
        return self._normalize_search_response(payload)

    def iter_products(
        self,
        *,
        page_size: int = 100,
        order_by: Optional[str] = None,
        columns: Optional[List[str]] = None,
        **filters: Any,
    ) -> Iterator[Dict[str, Any]]:
        page = 1
        while True:
            payload = self.list_products(page_size=page_size, page=page,
                                         order_by=order_by, columns=columns, **filters)
            response = payload.get("response") or {}
            results = response.get("results") or []
            if not results:
                break
            yield response
            if len(results) < page_size:
                break
            page += 1

    def iter_products_records(
        self,
        *,
        page_size: int = 100,
        order_by: Optional[str] = None,
        columns: Optional[List[str]] = None,
        **filters: Any,
    ) -> Iterator[Dict[str, Any]]:
        page = 1
        while True:
            payload = self.list_products(
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

    # --- ID-based / helper endpoints ---
    def get_product(self, product_id: Union[int, str]) -> Dict[str, Any]:
        return self._request("GET", f"product-service/product/{product_id}")

    def get_products_bulk(self, product_ids: Iterable[Union[int, str]]) -> Dict[str, Any]:
        ids = ",".join(str(i) for i in product_ids)
        return self._request("GET", "product-service/product", params={"productId": ids})

    def create_product(self, product_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "product-service/product", json=product_payload)

    def patch_product(self, product_id: Union[int, str], changes: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("PATCH", f"product-service/product/{product_id}", json=changes)

    def replace_product(self, product_id: Union[int, str], product_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("PUT", f"product-service/product/{product_id}", json=product_payload)

    def find_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        payload = self.search_products(columns=["productId", "SKU", "productName"],
                                       page_size=1, page=1, SKU=sku)
        resp = payload.get("response") or {}
        results = resp.get("results") or []
        return results[0] if results else None

    def get_product_availability(
        self,
        product_ids: Iterable[int] | int,
        warehouse_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        ids = product_ids if isinstance(product_ids, Iterable) and not isinstance(product_ids, (str, bytes)) else [product_ids]  # type: ignore
        params: Dict[str, Any] = {"productId": ",".join(map(str, ids))}
        if warehouse_id is not None:
            params["warehouseId"] = warehouse_id
        return self._request("GET", "product-service/product-availability", params=params)
