from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime


# -----------------------------
# DOMAIN MODELS
# -----------------------------
@dataclass
class Home:
    home_id: str
    owner_name: str
    wallet_balance: float = 0.0


@dataclass
class SmartMeterReading:
    home_id: str
    generated_kwh: float
    consumed_kwh: float
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def surplus_kwh(self) -> float:
        return max(0.0, self.generated_kwh - self.consumed_kwh)

    @property
    def deficit_kwh(self) -> float:
        return max(0.0, self.consumed_kwh - self.generated_kwh)


@dataclass
class SellOrder:
    seller_id: str
    available_kwh: float
    price_per_kwh: float


@dataclass
class BuyOrder:
    buyer_id: str
    required_kwh: float
    max_price_per_kwh: float


@dataclass
class Trade:
    seller_id: str
    buyer_id: str
    energy_kwh: float
    price_per_kwh: float
    total_amount: float
    timestamp: datetime = field(default_factory=datetime.now)


# -----------------------------
# SMART METER SERVICE
# -----------------------------
class SmartMeterService:
    def __init__(self):
        self.readings: List[SmartMeterReading] = []

    def ingest_reading(self, reading: SmartMeterReading):
        self.readings.append(reading)

    def latest_market_orders(self, sell_price: float, buy_price: float):
        sell_orders = []
        buy_orders = []

        for reading in self.readings:
            if reading.surplus_kwh > 0:
                sell_orders.append(
                    SellOrder(
                        seller_id=reading.home_id,
                        available_kwh=reading.surplus_kwh,
                        price_per_kwh=sell_price
                    )
                )
            elif reading.deficit_kwh > 0:
                buy_orders.append(
                    BuyOrder(
                        buyer_id=reading.home_id,
                        required_kwh=reading.deficit_kwh,
                        max_price_per_kwh=buy_price
                    )
                )

        return sell_orders, buy_orders


# -----------------------------
# MARKETPLACE SERVICE
# -----------------------------
class MarketplaceService:
    def match_orders(self, sell_orders: List[SellOrder], buy_orders: List[BuyOrder]) -> List[Trade]:
        trades = []

        # cheaper sellers first
        sell_orders.sort(key=lambda x: x.price_per_kwh)
        buy_orders.sort(key=lambda x: x.max_price_per_kwh, reverse=True)

        for buyer in buy_orders:
            remaining_need = buyer.required_kwh

            for seller in sell_orders:
                if remaining_need <= 0:
                    break

                if seller.available_kwh <= 0:
                    continue

                if seller.price_per_kwh > buyer.max_price_per_kwh:
                    continue

                traded_kwh = min(remaining_need, seller.available_kwh)
                total_amount = traded_kwh * seller.price_per_kwh

                trades.append(
                    Trade(
                        seller_id=seller.seller_id,
                        buyer_id=buyer.buyer_id,
                        energy_kwh=traded_kwh,
                        price_per_kwh=seller.price_per_kwh,
                        total_amount=total_amount
                    )
                )

                seller.available_kwh -= traded_kwh
                remaining_need -= traded_kwh

        return trades


# -----------------------------
# FINANCIAL SETTLEMENT SERVICE
# -----------------------------
class SettlementService:
    def settle_trades(self, homes: Dict[str, Home], trades: List[Trade]):
        for trade in trades:
            seller = homes[trade.seller_id]
            buyer = homes[trade.buyer_id]

            if buyer.wallet_balance >= trade.total_amount:
                buyer.wallet_balance -= trade.total_amount
                seller.wallet_balance += trade.total_amount
            else:
                print(f"Settlement failed: Buyer {buyer.home_id} has insufficient balance.")


# -----------------------------
# FITNESS FUNCTIONS / VALIDATION
# -----------------------------
def validate_reading(reading: SmartMeterReading):
    if reading.generated_kwh < 0 or reading.consumed_kwh < 0:
        raise ValueError("Energy values cannot be negative.")


def validate_trade(trade: Trade):
    if trade.energy_kwh <= 0:
        raise ValueError("Trade energy must be greater than zero.")
    if trade.total_amount < 0:
        raise ValueError("Trade amount cannot be negative.")


# -----------------------------
# MAIN PROGRAM
# -----------------------------
def main():
    # Homes in the neighbourhood
    homes = {
        "H1": Home(home_id="H1", owner_name="Ravi", wallet_balance=100.0),
        "H2": Home(home_id="H2", owner_name="Sita", wallet_balance=50.0),
        "H3": Home(home_id="H3", owner_name="Arjun", wallet_balance=80.0),
        "H4": Home(home_id="H4", owner_name="Meena", wallet_balance=60.0),
    }

    meter_service = SmartMeterService()
    marketplace_service = MarketplaceService()
    settlement_service = SettlementService()

    # Sample smart meter readings
    readings = [
        SmartMeterReading(home_id="H1", generated_kwh=15, consumed_kwh=8),   # surplus 7
        SmartMeterReading(home_id="H2", generated_kwh=4, consumed_kwh=10),   # deficit 6
        SmartMeterReading(home_id="H3", generated_kwh=12, consumed_kwh=5),   # surplus 7
        SmartMeterReading(home_id="H4", generated_kwh=3, consumed_kwh=8),    # deficit 5
    ]

    for reading in readings:
        validate_reading(reading)
        meter_service.ingest_reading(reading)

    # Generate marketplace orders from IoT readings
    sell_orders, buy_orders = meter_service.latest_market_orders(
        sell_price=5.0,   # seller asks ₹5 per kWh
        buy_price=6.0     # buyer willing to pay up to ₹6 per kWh
    )

    # Match orders
    trades = marketplace_service.match_orders(sell_orders, buy_orders)

    # Validate trades
    for trade in trades:
        validate_trade(trade)

    # Print matched trades
    print("\n--- MATCHED TRADES ---")
    for trade in trades:
        print(
            f"Seller: {trade.seller_id} -> Buyer: {trade.buyer_id} | "
            f"Energy: {trade.energy_kwh} kWh | "
            f"Rate: ₹{trade.price_per_kwh}/kWh | "
            f"Total: ₹{trade.total_amount}"
        )

    # Settle payments
    settlement_service.settle_trades(homes, trades)

    # Print wallet balances
    print("\n--- FINAL WALLET BALANCES ---")
    for home in homes.values():
        print(f"{home.home_id} ({home.owner_name}): ₹{home.wallet_balance}")


if __name__ == "__main__":
    main()