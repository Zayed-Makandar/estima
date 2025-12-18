robu_adapter = {
    "name": "Robu.in",
    "base_url": "https://robu.in",
    # dgwt_wcas=1 matches observed search URLs on the site
    "search_path": "/?s={query}&post_type=product&dgwt_wcas=1",
    "wait_after_ms": 500,
    "selectors": {
        # Broad WooCommerce/Electro selectors to catch both grid and carousel cards
        "list_item": ".products .product, li.product, div.product, .product-grid-item, .product-inner.product-item__inner",
        "title": ".wd-entities-title a, h2.woocommerce-loop-product__title a, h2.woocommerce-loop-producttitle a, h3.woocommerce-loop-product__title a, h2.woocommerce-loop-product__title",
        "price": ".price-add-to-cart, .price .woocommerce-Price-amount, span.woocommerce-Price-amount.amount",
        "availability": ".stock, .wd-out-of-stock, .outofstock, .instock",
        "link": "a.woocommerce-LoopProduct-link, .wd-entities-title a, h2.woocommerce-loop-product__title a, h2.woocommerce-loop-producttitle a",
        "image": ".product-thumb img, .product-thumbnail img, .product-itemthumbnail img, img.attachment-woocommerce_thumbnail, img.wp-post-image",
    },
}

