from typing import List
from datetime import datetime, timezone
from .models import Deal # Pydantic Deal model

async def fetch_simulated_deals_for_game(game_name: str) -> List[Deal]:
    """
    Simulates fetching game deals from various stores.
    Returns a list of Deal objects.
    """
    deals: List[Deal] = []
    now = datetime.now(timezone.utc)

    # Known game names and their simulated deals
    if game_name == "Cyberpunk 2077":
        deals.append(Deal(
            game_name=game_name,
            price=29.99,
            store="SimulatedStoreA",
            url=f"http://example.com/simstoreA/cyberpunk2077?id={int(now.timestamp())}",
            timestamp=now
        ))
        deals.append(Deal(
            game_name=game_name,
            price=27.50,
            store="SimulatedStoreB",
            url=f"http://example.com/simstoreB/cyberpunk2077?ref={int(now.timestamp())}",
            timestamp=now
        ))
    elif game_name == "The Witcher 3: Wild Hunt":
        deals.append(Deal(
            game_name=game_name,
            price=9.99,
            store="SimulatedStoreA",
            url=f"http://example.com/simstoreA/witcher3?id={int(now.timestamp())}",
            timestamp=now
        ))
    elif game_name == "Elden Ring":
        deals.append(Deal(
            game_name=game_name,
            price=49.99,
            store="SimulatedStoreC",
            url=f"http://example.com/simstoreC/eldenring?tracker={int(now.timestamp())}",
            timestamp=now
        ))

    # For any other game name, it returns an empty list, simulating no deals found.
    return deals
