evelta_adapter = {
    "name": "Evelta",
    "base_url": "https://evelta.com",
    "search_path": "/search-results-page?q={query}",
    "wait_after_ms": 0,  # we will use explicit waits in service
    "selectors": {
        # Searchanise injected results - updated based on live DOM inspection
        "list_item": "li.snize-product",
        "title": ".snize-title",  # Clean product title only
        "price": ".snize-price.money, .snize-price, .snize-price-list .snize-price",  # Price element
        "availability": ".snize-stock-status, .stock, .availability, .badge",
        "link": ".snize-item-title a, a.snize-thumbnail, li.snize-product a[href]",
        "image": ".snize-thumbnail img, li.snize-product img",
    },
}

