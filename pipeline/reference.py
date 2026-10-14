VENDORS = {
    0: "Unknown",
    1: "Creative Mobile Technologies",
    2: "VeriFone / Curb Mobility",
    4: "Other vendor (id 4, not in the TLC data dictionary)",
    6: "Myle Technologies",
    7: "Helix",
}

RATE_CODES = {
    1: "Standard rate",
    2: "JFK",
    3: "Newark",
    4: "Nassau or Westchester",
    5: "Negotiated fare",
    6: "Group ride",
    99: "Unknown",
}

PAYMENT_TYPES = {
    0: "Flex fare trip",
    1: "Credit card",
    2: "Cash",
    3: "No charge",
    4: "Dispute",
    5: "Unknown",
    6: "Voided trip",
}

FEE_COLUMNS = ["extra", "mta_tax", "improvement_surcharge", "congestion_surcharge", "airport_fee"]

MONEY_COLUMNS = [
    "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount",
    "improvement_surcharge", "total_amount", "congestion_surcharge", "airport_fee",
]
