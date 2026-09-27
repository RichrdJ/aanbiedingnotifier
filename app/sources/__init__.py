from dataclasses import dataclass, field


@dataclass
class Offer:
    store: str
    product_id: str
    title: str
    brand: str = ""
    size: str = ""
    price: float | None = None          # actieprijs (of huidige prijs)
    old_price: float | None = None      # prijs zonder korting
    deal: str = ""                      # bijv. "2e halve prijs", "1+1 gratis"
    valid_until: str = ""
    url: str = ""
    discount: float | None = None      # kortingspercentage, indien te bepalen
    matched: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.store}:{self.product_id}:{self.deal}:{self.valid_until}"
