# BrightPy
2025 Python wrapper for the Brightpearl API

## Purpose:
This project is meant to provide a python option for calling the Brightpearl API to interact with various Brightpearl objects.

## Functionality for Objects:
- Orders
- Products (in development)

## Example Code
    api = BrightpearlAPI(
        domain="https://use1.brightpearlconnect.com",
        account_id="YOUR_ACCOUNT_ID",
        account_token="YOUR_ACCOUNT_TOKEN",
        app_ref="YOUR_APP_REF",
    )

    # Example: list most recently updated orders
    try:
        results = api.list_orders(page_size=50, order_by="-updatedOn")
        print(results.get("response"))
    except BrightpearlAPIError as e:
        print(f"Error: {e.status} | {e} | {e.payload}")