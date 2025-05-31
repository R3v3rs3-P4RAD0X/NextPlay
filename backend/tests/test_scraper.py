import pytest
from datetime import datetime, timezone

from backend.scraper import fetch_simulated_deals_for_game
from backend.models import Deal # Pydantic Deal model

@pytest.mark.asyncio
async def test_fetch_simulated_deals_known_game():
    game_name = "Cyberpunk 2077"
    deals = await fetch_simulated_deals_for_game(game_name)

    assert len(deals) == 2
    for deal in deals:
        assert isinstance(deal, Deal)
        assert deal.game_name == game_name
        assert deal.price > 0
        assert deal.store.startswith("SimulatedStore")
        assert "http://example.com/" in deal.url
        assert isinstance(deal.timestamp, datetime)
        assert deal.timestamp.tzinfo == timezone.utc

@pytest.mark.asyncio
async def test_fetch_simulated_deals_another_known_game():
    game_name = "The Witcher 3: Wild Hunt"
    deals = await fetch_simulated_deals_for_game(game_name)

    assert len(deals) == 1
    deal = deals[0]
    assert deal.game_name == game_name
    assert deal.price == 9.99
    assert deal.store == "SimulatedStoreA"

@pytest.mark.asyncio
async def test_fetch_simulated_deals_unknown_game():
    game_name = "Unknown Game XYZ"
    deals = await fetch_simulated_deals_for_game(game_name)
    assert len(deals) == 0

@pytest.mark.asyncio
async def test_fetch_simulated_deals_timestamp_is_recent():
    # Check if timestamp is roughly "now"
    # This test might be flaky if execution takes too long between `now` here and `now` in scraper.
    # For simulation, it's okay. For real scraper, timestamp would come from source or DB.
    game_name = "Elden Ring"
    deals = await fetch_simulated_deals_for_game(game_name)

    assert len(deals) == 1
    deal_timestamp = deals[0].timestamp
    current_time_utc = datetime.now(timezone.utc)

    # Allow a small difference, e.g., a few seconds, due to execution time
    time_difference = abs((current_time_utc - deal_timestamp).total_seconds())
    assert time_difference < 5 # Assuming test execution is fast enough

    # Ensure timestamp is aware
    assert deal_timestamp.tzinfo is not None
    assert deal_timestamp.tzinfo == timezone.utc
