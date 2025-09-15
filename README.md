# BrightPy
Python client for the Brightpearl API (orders + products).

## Quick Start
- Install deps: `pip install -r requirements.txt`
- Create the client:
  
  ```python
  from brightpearl import BrightpearlAPI, BrightpearlAPIError

  api = BrightpearlAPI(
      domain="https://use1.brightpearlconnect.com",  # include scheme
      account_id="YOUR_ACCOUNT_ID",
      account_token="YOUR_ACCOUNT_TOKEN",
      app_ref="YOUR_APP_REF",
  )
  ```

- Handle errors:
  
  ```python
  try:
      ...
  except BrightpearlAPIError as e:
      print(e.status, e.payload)
  ```

## Orders
- search_orders: Low-level search (GET with query params).
  - Params: `columns: List[str] | None`, `sort: str | None` (e.g., `updatedOn:DESC`), `page_size: int`, `page: int | None`, `first_result: int | None`, plus Brightpearl filters.
  - Pagination: If `first_result` is set it is used; otherwise `page` is sent.
  - Example: `api.search_orders(page_size=50, page=1, sort="orderId:ASC", orderStatusId=1)`

- list_orders: Friendly wrapper over search (builds sort from `order_by`). Returns the raw Brightpearl payload.
  - Params: `page_size`, `page`, `order_by` (e.g., `"-updatedOn"`), `columns`, plus filters.
  - Example: `api.list_orders(page_size=50, order_by="-updatedOn")`

- iter_orders: Paginates through raw search responses (yields each page’s `response`).
  - Example:
    ```python
    for page in api.iter_orders(page_size=200, order_by="orderId"):
        for row in page.get("results", []):
            ...
    ```

- list_orders_records: Returns a list of dicts mapped by column names.
  - Example: `orders = api.list_orders_records(page_size=50, order_by="-updatedOn")`

- iter_orders_records: Streams one normalized record (dict) at a time.
  - Example:
    ```python
    for order in api.iter_orders_records(order_by="-updatedOn"):
        print(order["orderId"], order.get("updatedOn"))
    ```

- get_order: `api.get_order(order_id)`
- get_orders_bulk: `api.get_orders_bulk([1,2,3])`
- create_order: `api.create_order(order_payload)`
- patch_order: `api.patch_order(order_id, patch_payload)`
- replace_order: `api.replace_order(order_id, order_payload)`
- add_order_note: `api.add_order_note(order_id, text, is_public=True)`
- list_order_notes: `api.list_order_notes(order_id)`
- update_order_status: `api.update_order_status(order_id, status_id)`

Notes:
- The set of valid columns can vary by account; omit `columns` to let the API choose.
- `order_by` translates to the underlying API’s sort parameter.

## Products
- search_products: Low-level search (GET with query params).
  - Params: `columns: List[str] | None`, `sort: str | None` (e.g., `updatedOn:DESC`), `page_size: int`, `page: int | None`, `first_result: int | None`, plus Brightpearl filters (e.g., `SKU`, `productName`, `brandId`).
  - Example: `api.search_products(page_size=50, sort="updatedOn:DESC", brandId=10)`

- list_products: Friendly wrapper over search. Returns raw payload.
  - Params: `page_size`, `page`, `order_by` (e.g., `"-updatedOn"`), `columns`, plus filters.
  - Example: `api.list_products(page_size=50, order_by="-updatedOn")`

- iter_products: Paginates through raw search responses (yields each page’s `response`).

- list_products_records: Returns a list of dicts mapped by column names.
  - Example: `products = api.list_products_records(page_size=100, order_by="SKU")`

- iter_products_records: Streams one normalized product (dict) at a time.

- get_product: `api.get_product(product_id)`
- get_products_bulk: `api.get_products_bulk([1,2,3])`
- create_product: `api.create_product(product_payload)`
- patch_product: `api.patch_product(product_id, changes)`
- replace_product: `api.replace_product(product_id, product_payload)`
- find_product_by_sku: `api.find_product_by_sku("ABC123")` -> first matching or `None`
- get_product_availability: `api.get_product_availability([1,2,3], warehouse_id=5)`

## Normalized Records vs. Raw Payloads
- Raw payload: mirrors Brightpearl’s `{"response": {"metaData": {"columns": [...]}, "results": [...]}}` shape.
- Normalized records: helper methods map each result row to a dict using the returned column names.
  - `list_*_records(...)` returns a page of dicts.
  - `iter_*_records(...)` yields dicts across pages.

## Example
```python
from brightpearl import BrightpearlAPI, BrightpearlAPIError

api = BrightpearlAPI(
    domain="https://use1.brightpearlconnect.com",
    account_id="YOUR_ACCOUNT_ID",
    account_token="YOUR_ACCOUNT_TOKEN",
    app_ref="YOUR_APP_REF",
)

try:
    # Most recently updated orders as dicts
    orders = api.list_orders_records(page_size=50, order_by="-updatedOn")
    for o in orders:
        print(o.get("orderId"), o.get("updatedOn"))

    # Recently updated products as dicts
    products = api.list_products_records(page_size=50, order_by="-updatedOn")
    print(len(products))
except BrightpearlAPIError as e:
    print(f"Error: {e.status}: {e.payload}")
```
