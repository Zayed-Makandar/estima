thinkrobotics_adapter = {
    "name": "ThinkRobotics",
    "base_url": "https://thinkrobotics.com",
    "search_path": "/search?q={query}&options%5Bprefix%5D=last",
    "wait_after_ms": 0,  # Native search is fast DOM, no extra wait needed
    "selectors": {
        "list_item": "div.product-card, .product-card-wrapper, .ws_search_product-card-grid, .wssearchproduct-card-grid, .wssearchproduct-card, div[data-product-id]",
        "title": ".product-card__title, .card__heading a, .ws_search_card-title, .wssearchproduct-title, a[data-product-title]",
        "price": ".price-item--regular .glc-money, .price-item--sale .glc-money, .price__regular .price-item, .price__sale .price-item, .ws-pd-price, .wssearchproduct-price",
        "availability": ".price__badge--sold-out, .product-label--sold-out, .wssearchproduct-inventory",
        "link": "a.product-card__link-title, a.full-unstyled-link, a[data-product-handle], a[href*='/products/']",
        "image": "img.product-card__image, img.product-featured-media, img.ws_card-img-top, img.primary-image",
    },
}

