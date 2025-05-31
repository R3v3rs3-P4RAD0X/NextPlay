import pytest
from unittest.mock import patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend import main as main_app # To mock functions within main
from backend import models as pydantic_models
from backend import crud
from backend.database import get_db # For checking dependency override

# Sample data for mocking fetch_simulated_steam_api_data
MOCK_STEAM_ID = "mock_steam_user_123"
MOCK_API_DATA = {
    "steam_id": MOCK_STEAM_ID,
    "persona_name": "MockSteamUser",
    "avatar_url": "http://example.com/mock_avatar.jpg",
    "owned_games": [
        {
            "id": 1001,
            "name": "Mock Game Alpha",
            "genres": ["MockGenre"],
            "tags": ["MockTag"],
            "playtime_forever": 100,
            "playtime_2weeks": 10
        },
        {
            "id": 1002,
            "name": "Mock Game Beta",
            "genres": ["TestGenre"],
            "tags": ["TestTag"],
            "playtime_forever": 200,
            "playtime_2weeks": None
        }
    ]
}

@pytest.mark.asyncio
@patch('backend.main.fetch_simulated_steam_api_data') # Patch the function in main.py
async def test_get_user_profile_new_user(
    mock_fetch_api, client: AsyncClient, db_session: AsyncSession
):
    mock_fetch_api.return_value = MOCK_API_DATA # Configure mock return

    response = await client.get(f"/user/{MOCK_STEAM_ID}/profile")

    assert response.status_code == 200
    mock_fetch_api.assert_called_once_with(MOCK_STEAM_ID)

    # Verify response data
    profile_data = response.json()
    assert profile_data["steam_id"] == MOCK_STEAM_ID
    assert profile_data["persona_name"] == MOCK_API_DATA["persona_name"]
    assert profile_data["avatar_url"] == MOCK_API_DATA["avatar_url"]
    assert len(profile_data["owned_games"]) == len(MOCK_API_DATA["owned_games"])

    game_ids_from_response = {game['id'] for game in profile_data["owned_games"]}
    expected_game_ids = {game['id'] for game in MOCK_API_DATA["owned_games"]}
    assert game_ids_from_response == expected_game_ids

    for game_resp in profile_data["owned_games"]:
        original_game = next(g for g in MOCK_API_DATA["owned_games"] if g["id"] == game_resp["id"])
        assert game_resp["name"] == original_game["name"]
        assert game_resp["playtime_forever"] == original_game["playtime_forever"]
        assert game_resp["genres"] == original_game["genres"] # Should now be populated
        assert game_resp["tags"] == original_game["tags"]     # Should now be populated


    # Verify data in DB
    db_user = await crud.get_user(db_session, MOCK_STEAM_ID)
    assert db_user is not None
    assert db_user.persona_name == MOCK_API_DATA["persona_name"]

    assert len(db_user.game_associations) == len(MOCK_API_DATA["owned_games"])

    # Check one game association detail
    assoc1 = next(assoc for assoc in db_user.game_associations if assoc.game_id == 1001)
    assert assoc1 is not None
    assert assoc1.playtime_forever == 100
    assert assoc1.playtime_2weeks == 10
    assert assoc1.game.name == "Mock Game Alpha"
    assert assoc1.game.genres == "MockGenre" # Stored as string
    assert assoc1.game.tags == "MockTag"     # Stored as string

    assoc2 = next(assoc for assoc in db_user.game_associations if assoc.game_id == 1002)
    assert assoc2 is not None
    assert assoc2.playtime_forever == 200
    assert assoc2.playtime_2weeks is None
    assert assoc2.game.name == "Mock Game Beta"
    assert assoc2.game.genres == "TestGenre"
    assert assoc2.game.tags == "TestTag"


@pytest.mark.asyncio
@patch('backend.main.fetch_simulated_steam_api_data') # Patch the function in main.py
async def test_get_user_profile_existing_user(
    mock_fetch_api, client: AsyncClient, db_session: AsyncSession
):
    # 1. Pre-populate DB with a user and a game
    existing_steam_id = "existing_user_001"
    # Create user directly
    db_user_initial = await crud.create_user(
        db_session,
        pydantic_models.UserProfileCreate(
            steam_id=existing_steam_id,
            persona_name="Existing DB User",
            avatar_url="http://example.com/existing.jpg"
        )
    )
    # Add a game to this user directly via CRUD
    game_to_add_pydantic = pydantic_models.Game(
        id=2001,
        name="Pre-existing Game",
        genres=["PersistentGenre1", "PersistentGenre2"],
        tags=["PersistentTag1"],
        playtime_forever=50 # This playtime is for the pydantic model, passed to add_game_to_user separately
    )
    await crud.add_game_to_user(
        db_session,
        steam_id=existing_steam_id,
        game_data=game_to_add_pydantic, # Pass the Pydantic model with genre/tag info
        playtime_forever=50, # Actual playtime for association
        playtime_2weeks=5
    )

    # Refresh user to ensure relations are loaded for assertion if needed, though get_user re-fetches
    await db_session.refresh(db_user_initial, attribute_names=['game_associations'])


    # 2. Call the endpoint
    response = await client.get(f"/user/{existing_steam_id}/profile")

    # 3. Verify
    assert response.status_code == 200
    mock_fetch_api.assert_not_called() # API should not be called

    profile_data = response.json()
    assert profile_data["steam_id"] == existing_steam_id
    assert profile_data["persona_name"] == "Existing DB User"
    assert len(profile_data["owned_games"]) == 1

    game_in_response = profile_data["owned_games"][0]
    assert game_in_response["id"] == 2001
    assert game_in_response["name"] == "Pre-existing Game"
    assert game_in_response["playtime_forever"] == 50
    assert game_in_response["genres"] == ["PersistentGenre1", "PersistentGenre2"]
    assert game_in_response["tags"] == ["PersistentTag1"]

@pytest.mark.asyncio # Added decorator
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_get_user_categories_valid_user(client: AsyncClient, db_session: AsyncSession):
    user_id = "category_test_user"
    await crud.create_user(db_session, pydantic_models.UserProfileCreate(steam_id=user_id, persona_name="CatTestUser", avatar_url=""))

    game1 = pydantic_models.Game(id=101, name="Action RPG Game", genres=["Action", "RPG"], tags=[], playtime_forever=10)
    game2 = pydantic_models.Game(id=102, name="Strategy Game", genres=["Strategy"], tags=[], playtime_forever=20)
    game3 = pydantic_models.Game(id=103, name="Action Game 2", genres=["Action"], tags=[], playtime_forever=30)
    game4 = pydantic_models.Game(id=104, name="No Genre Game", genres=[], tags=[], playtime_forever=40)


    await crud.add_game_to_user(db_session, user_id, game1, 10)
    await crud.add_game_to_user(db_session, user_id, game2, 20)
    await crud.add_game_to_user(db_session, user_id, game3, 30)
    await crud.add_game_to_user(db_session, user_id, game4, 40)

    response = await client.get(f"/user/{user_id}/categories")
    assert response.status_code == 200
    data = response.json()

    assert "categories" in data
    categories = data["categories"]

    assert "Action" in categories
    assert len(categories["Action"]) == 2
    action_game_ids = {g["id"] for g in categories["Action"]}
    assert {101, 103} == action_game_ids
    # Check full game object details for one game
    action_game1 = next(g for g in categories["Action"] if g["id"] == 101)
    assert action_game1["name"] == "Action RPG Game"
    assert action_game1["genres"] == ["Action", "RPG"] # Pydantic model should have list

    assert "RPG" in categories
    assert len(categories["RPG"]) == 1
    assert categories["RPG"][0]["id"] == 101

    assert "Strategy" in categories
    assert len(categories["Strategy"]) == 1
    assert categories["Strategy"][0]["id"] == 102

    assert "Uncategorized" in categories
    assert len(categories["Uncategorized"]) == 1
    assert categories["Uncategorized"][0]["id"] == 104

@pytest.mark.asyncio
async def test_get_user_categories_no_games(client: AsyncClient, db_session: AsyncSession):
    user_id = "category_test_user_no_games"
    await crud.create_user(db_session, pydantic_models.UserProfileCreate(steam_id=user_id, persona_name="CatNoGamesUser", avatar_url=""))

    response = await client.get(f"/user/{user_id}/categories")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert data["categories"] == {}

@pytest.mark.asyncio
async def test_get_user_categories_non_existent_user(client: AsyncClient):
    response = await client.get("/user/non_existent_user_for_cat_test/categories")
    assert response.status_code == 404
    # assert response.status_code == 200 # Removed duplicated incorrect assertion
    assert response.json() == {"detail": "User not found"}


# Tests for /user/{steam_id}/recommendations endpoint
@pytest.mark.asyncio
@patch('backend.recommender.recommend_deals_by_genre')
@patch('backend.crud.get_user') # We also need to control the get_user check in the endpoint
async def test_get_recommendations_user_exists_recommendations_found(
    mock_crud_get_user, mock_recommend_deals, client: AsyncClient, db_session: AsyncSession
):
    steam_id = "reco_endpoint_user_1"
    # Simulate user exists
    mock_crud_get_user.return_value = pydantic_models.UserProfile(
        steam_id=steam_id, persona_name="Test Reco User", avatar_url="", owned_games=[]
    )

    mock_deal_timestamp = datetime.now(timezone.utc)
    mocked_deals_data = [
        pydantic_models.Deal(game_name="Game X Deal", price=19.99, store="StoreR", url="url_rx", timestamp=mock_deal_timestamp),
        pydantic_models.Deal(game_name="Game Y Deal", price=9.99, store="StoreQ", url="url_ry", timestamp=mock_deal_timestamp)
    ]
    mock_recommend_deals.return_value = mocked_deals_data

    response = await client.get(f"/user/{steam_id}/recommendations")

    assert response.status_code == 200
    # Check that the actual db_session from the overridden dependency is passed to crud.get_user
    mock_crud_get_user.assert_called_once_with(db_session, steam_id=steam_id)
    mock_recommend_deals.assert_called_once_with(db_session, steam_id=steam_id)

    data = response.json()
    assert "deals" in data
    assert len(data["deals"]) == 2
    assert data["deals"][0]["game_name"] == "Game X Deal"
    assert data["deals"][1]["price"] == 9.99
    # Timestamps in JSON response are ISO strings
    assert data["deals"][0]["timestamp"] == mocked_deals_data[0].timestamp.isoformat().replace("+00:00", "Z")


@pytest.mark.asyncio
@patch('backend.recommender.recommend_deals_by_genre')
@patch('backend.crud.get_user')
async def test_get_recommendations_user_exists_no_recommendations(
    mock_crud_get_user, mock_recommend_deals, client: AsyncClient, db_session: AsyncSession
):
    steam_id = "reco_endpoint_user_2"
    mock_crud_get_user.return_value = pydantic_models.UserProfile(
        steam_id=steam_id, persona_name="Test Reco User 2", avatar_url="", owned_games=[]
    )
    mock_recommend_deals.return_value = [] # No recommendations found

    response = await client.get(f"/user/{steam_id}/recommendations")

    assert response.status_code == 200
    mock_crud_get_user.assert_called_once_with(db_session, steam_id=steam_id)
    mock_recommend_deals.assert_called_once_with(db_session, steam_id=steam_id)

    data = response.json()
    assert "deals" in data
    assert len(data["deals"]) == 0

@pytest.mark.asyncio
@patch('backend.recommender.recommend_deals_by_genre')
@patch('backend.crud.get_user')
async def test_get_recommendations_user_not_found(
    mock_crud_get_user, mock_recommend_deals, client: AsyncClient, db_session: AsyncSession
    # db_session is injected into client fixture, which then overrides get_db for the app
):
    steam_id = "reco_endpoint_user_nonexistent"
    mock_crud_get_user.return_value = None # Simulate user does not exist

    response = await client.get(f"/user/{steam_id}/recommendations")

    assert response.status_code == 404
    # crud.get_user is called with the actual db_session by the endpoint due to dependency override
    mock_crud_get_user.assert_called_once_with(db_session, steam_id=steam_id)
    mock_recommend_deals.assert_not_called()

    assert response.json() == {"detail": "User not found"}

@pytest.mark.asyncio
async def test_serve_index_html(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    # Check for a known string from index.html
    assert "GameLens API Endpoints" in response.text

@pytest.mark.asyncio
async def test_serve_index_html_not_found(client: AsyncClient):
    # Temporarily mock os.path.exists to simulate file not found
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = False
        response = await client.get("/")
        assert response.status_code == 404
        assert response.json() == {"detail": "Index.html not found"}

# Tests for /deals/{game_name} endpoint
from datetime import datetime, timezone, timedelta

@pytest.mark.asyncio
@patch('backend.scraper.fetch_simulated_deals_for_game')
async def test_get_deals_no_db_scraper_finds(
    mock_fetch_scraper, client: AsyncClient, db_session: AsyncSession
):
    game_name = "Cyberpunk 2077" # Known by scraper
    # Ensure DB has no deals for this game initially
    db_deals = await crud.get_deals_by_game_name(db_session, game_name)
    assert len(db_deals) == 0

    # Mock scraper response
    mock_deal_timestamp_new = datetime.now(timezone.utc)
    mock_deal_timestamp_old = mock_deal_timestamp_new - timedelta(seconds=1)
    mock_scraper_deals = [
        pydantic_models.Deal(game_name=game_name, price=25.99, store="ScraperStore1", url="s_url1", timestamp=mock_deal_timestamp_old), # Older
        pydantic_models.Deal(game_name=game_name, price=26.99, store="ScraperStore2", url="s_url2", timestamp=mock_deal_timestamp_new)  # Newer
    ]
    mock_fetch_scraper.return_value = mock_scraper_deals

    response = await client.get(f"/deals/{game_name}")
    assert response.status_code == 200

    response_deals = response.json()
    assert len(response_deals) == 2
    mock_fetch_scraper.assert_called_once_with(game_name)

    # Verify response data matches scraper data (Pydantic models are JSON serializable directly)
    # Timestamps might have precision differences after JSON conversion, so compare carefully if needed,
    # but here we trust Pydantic's serialization or compare key fields.
    assert response_deals[0]["price"] == mock_scraper_deals[0].price
    assert response_deals[1]["store"] == mock_scraper_deals[1].store
    # Parse response timestamp string back to datetime for proper comparison
    response_timestamp = datetime.fromisoformat(response_deals[0]["timestamp"].replace("Z", "+00:00"))
    assert response_timestamp == mock_scraper_deals[0].timestamp


    # Verify deals were saved to DB
    saved_db_deals = await crud.get_deals_by_game_name(db_session, game_name)
    assert len(saved_db_deals) == 2
    # Check one deal detail in DB
    # Timestamps from DB with aiosqlite might be naive, convert for comparison or ensure test setup handles it.
    # The conftest's db_session should be using DateTime(timezone=True) for the Deal model.
    # And test_crud.py's test_create_deal already handles this comparison.
    # mock_scraper_deals[1] is newer, so it should be saved_db_deals[0]
    assert saved_db_deals[0].price == mock_scraper_deals[1].price
    assert saved_db_deals[0].store == mock_scraper_deals[1].store
    # mock_scraper_deals[0] is older, so it should be saved_db_deals[1]
    assert saved_db_deals[1].price == mock_scraper_deals[0].price
    assert saved_db_deals[1].store == mock_scraper_deals[0].store


@pytest.mark.asyncio
@patch('backend.scraper.fetch_simulated_deals_for_game')
async def test_get_deals_db_has_deals_scraper_not_called(
    mock_fetch_scraper, client: AsyncClient, db_session: AsyncSession
):
    game_name = "PreExistingDealsGame"
    db_timestamp = datetime.now(timezone.utc)

    # Pre-populate DB
    deal1 = await crud.create_deal(db_session, pydantic_models.DealCreate(game_name=game_name, price=15.00, store="DBStore1", url="db_url1", timestamp=db_timestamp))
    deal2 = await crud.create_deal(db_session, pydantic_models.DealCreate(game_name=game_name, price=16.00, store="DBStore2", url="db_url2", timestamp=db_timestamp - timedelta(seconds=1))) # Slightly older

    response = await client.get(f"/deals/{game_name}")
    assert response.status_code == 200

    response_deals = response.json()
    assert len(response_deals) == 2
    mock_fetch_scraper.assert_not_called() # Scraper should not be called

    # Verify response data matches DB data (order is by timestamp desc)
    assert response_deals[0]["price"] == deal1.price
    assert response_deals[0]["store"] == deal1.store
    assert response_deals[1]["price"] == deal2.price
    assert response_deals[1]["store"] == deal2.store

@pytest.mark.asyncio
@patch('backend.scraper.fetch_simulated_deals_for_game')
async def test_get_deals_no_db_scraper_finds_none(
    mock_fetch_scraper, client: AsyncClient, db_session: AsyncSession
):
    game_name = "NoDealsAnywhereGame"
    # Ensure DB has no deals
    db_deals = await crud.get_deals_by_game_name(db_session, game_name)
    assert len(db_deals) == 0

    # Mock scraper to return empty list
    mock_fetch_scraper.return_value = []

    response = await client.get(f"/deals/{game_name}")
    assert response.status_code == 200
    assert response.json() == []
    mock_fetch_scraper.assert_called_once_with(game_name)

    # Verify DB still has no deals
    db_deals_after = await crud.get_deals_by_game_name(db_session, game_name)
    assert len(db_deals_after) == 0

# More tests can be added:
# - User not found in API (mock fetch_simulated_steam_api_data to raise an error or return None/empty)
# - API returns user with no games
# - Test edge cases for playtime data (e.g., missing, zero)
# - Test behavior if DB operations fail (this is harder and might require more complex mocking)
