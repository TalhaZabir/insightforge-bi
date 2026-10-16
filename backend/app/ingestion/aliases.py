"""Canonical business schema, header aliases, and normalization maps."""

from __future__ import annotations

import re

CANONICAL_FIELDS = [
    "order_id",
    "order_date",
    "customer_id",
    "customer_name",
    "customer_segment",
    "product_id",
    "product_name",
    "category",
    "subcategory",
    "region",
    "country",
    "sales_channel",
    "sales_rep",
    "quantity",
    "unit_price",
    "discount",
    "cost",
    "shipping_cost",
    "revenue",
    "profit",
    "payment_method",
    "order_status",
]

# At least one of each OR-group must be mapped, plus the singletons.
REQUIRED_SINGLETONS = ["order_id", "order_date", "quantity"]
REQUIRED_GROUPS = [("product_id", "product_name"), ("revenue", "unit_price")]

_ALIASES: dict[str, list[str]] = {
    "order_id": [
        "orderid",
        "ordernumber",
        "orderno",
        "invoiceno",
        "invoiceid",
        "transactionid",
        "order",
        "orderref",
    ],
    "order_date": [
        "date",
        "transactiondate",
        "invoicedate",
        "orderday",
        "saledate",
        "purchasedate",
        "dt",
        "orderdate",
    ],
    "customer_id": ["customerid", "clientid", "buyerid", "custid", "customerno", "clientno"],
    "customer_name": [
        "customername",
        "clientname",
        "buyername",
        "customer",
        "client",
        "buyer",
        "custname",
        "accountname",
        "company",
    ],
    "customer_segment": ["segment", "customersegment", "clientsegment", "marketsegment"],
    "product_id": ["productid", "skuid", "sku", "itemid", "itemcode", "productcode", "productno"],
    "product_name": [
        "productname",
        "product",
        "item",
        "itemname",
        "description",
        "productdescription",
    ],
    "category": ["category", "productcategory", "dept", "department"],
    "subcategory": ["subcategory", "subcat", "productsubcategory"],
    "region": ["region", "state", "territory", "market", "area", "zone", "salesregion"],
    "country": ["country", "nation"],
    "sales_channel": ["saleschannel", "channel", "salesthrough", "platform"],
    "sales_rep": [
        "salesrep",
        "rep",
        "salesperson",
        "agent",
        "salesagent",
        "accountmanager",
        "employee",
        "salesowner",
    ],
    "quantity": ["qty", "units", "quantity", "orderqty", "amountqty"],
    "unit_price": ["unitprice", "price", "saleprice", "rate", "unitrate"],
    "discount": ["discount", "disc", "discountrate", "discountpct", "discountpercent", "promo"],
    "cost": ["cost", "unitcost", "cogs", "productcost"],
    "shipping_cost": ["shippingcost", "shipping", "freight", "deliverycost", "shippingfee"],
    "revenue": [
        "sales",
        "amount",
        "totalamount",
        "revenue",
        "total",
        "salestotal",
        "linetotal",
        "net",
        "netamount",
        "extendedprice",
    ],
    "profit": ["profit", "grossprofit", "netprofit"],
    "payment_method": ["paymentmethod", "payment", "paytype", "paymenttype"],
    "order_status": ["orderstatus", "status", "fulfillmentstatus"],
}

# normalized header -> canonical (first writer wins on collision)
ALIAS_MAP: dict[str, str] = {}
for _canon, _names in _ALIASES.items():
    for _n in _names:
        ALIAS_MAP.setdefault(_n, _canon)


def normalize_header(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.strip().lower())


REGION_MAP = {
    "west": "West",
    "w": "West",
    "western": "West",
    "east": "East",
    "e": "East",
    "eastern": "East",
    "south": "South",
    "s": "South",
    "southern": "South",
    "midwest": "Midwest",
    "mid-west": "Midwest",
    "mid west": "Midwest",
    "north": "North",
    "n": "North",
    "northern": "North",
    "ontario": "Ontario",
    "central": "Central",
}

CATEGORY_MAP = {
    "electronics": "Electronics",
    "electronic": "Electronics",
    "apparel": "Apparel",
    "clothing": "Apparel",
    "fashion": "Apparel",
    "home & kitchen": "Home & Kitchen",
    "home and kitchen": "Home & Kitchen",
    "home/kitchen": "Home & Kitchen",
    "home": "Home & Kitchen",
    "kitchen": "Home & Kitchen",
    "sports": "Sports",
    "sport": "Sports",
    "outdoors": "Sports",
    "beauty": "Beauty",
    "cosmetics": "Beauty",
}

STATUS_MAP = {
    "completed": "Completed",
    "complete": "Completed",
    "delivered": "Completed",
    "closed": "Completed",
    "done": "Completed",
    "pending": "Pending",
    "processing": "Pending",
    "open": "Pending",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
    "cancel": "Cancelled",
    "returned": "Returned",
    "refunded": "Returned",
    "return": "Returned",
}
KNOWN_STATUSES = {"Completed", "Pending", "Cancelled", "Returned"}
