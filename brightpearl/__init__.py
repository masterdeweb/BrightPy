from .client import _BaseClient, BrightpearlAPIError
from .orders import OrdersMixin
from .products import ProductsMixin

# Public API class = mixins + base client
class BrightpearlAPI(OrdersMixin, ProductsMixin, _BaseClient):
    """Unified client: orders + products (extend by adding more mixins)."""
    pass

__all__ = ["BrightpearlAPI", "BrightpearlAPIError"]
