robocraze_adapter = {
    "name": "Robocraze",
    "base_url": "https://robocraze.com",
    "search_path": "/search?q={query}&options%5Bprefix%5D=last&type=product",
    "wait_after_ms": 500,  # allow lazy bits to settle
    "selectors": {
        # Product cards in search results
        "list_item": "li.product, div.product-item.enablecustomlayoutcard, div.product-grid-item",
        # Clean title is in data-product-title attribute
        "title": "a.card-title[data-product-title], a.card-title span.text, a.full-unstyled-link",
        # Prices appear as sale/regular blocks or numeric attrs
        "price": "span.price-item--sale, span.price-item--regular, div.price-item.price-item--sale, div.price-item.price-item--regular, span[data-last]",
        # Availability inferred from add-to-cart button text/attribute
        "availability": "button[data-btn-addToCart]",
        # Link to product page
        "link": "a.card-link, a.card-title, a.full-unstyled-link",
        # Lazy-loaded images expose srcset/data-srcset
        "image": "img[data-srcset], img.lazyload[data-srcset], img.card-img-top, img[data-src], img[src]",
    },
}

