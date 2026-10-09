"""Presentation catalogue: variant IDs verified from spreadsheet rows 75/144/55.
Live adapter must confirm availability; these are not a catalogue API substitute.
"""
CATALOGUE = {
    "keychron": dict(variant_id="44554000957529", shop="keychron.com", item="Keychron B40 Wireless Keyboard", colour="deep black", cents=4999),
    "powerbug": dict(variant_id="46441190424633", shop="twelvesouth.com", item="PowerBug 25W (Qi2.2)", colour="white/dune", cents=4999),
    "gmktec": dict(variant_id="49224082620570", shop="gmktec.com", item="GMKtec EVO-X5 Pro, 192GB + 2TB / US", colour="", cents=659900),
}


def find_item(query: str):
    query = query.lower()
    for name, item in CATALOGUE.items():
        if name in query:
            return item
    if "today" in query and "deal" in query:
        return CATALOGUE["gmktec"]
    return None
