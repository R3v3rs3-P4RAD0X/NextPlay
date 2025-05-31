import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend import crud
from backend import models as pydantic_models
from backend import db_models as sqlalchemy_models

@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    user_in = pydantic_models.UserProfileCreate(
        steam_id="test_steam_id_123",
        persona_name="TestUser123",
        avatar_url="http://example.com/avatar.jpg"
    )
    db_user = await crud.create_user(db_session, user_in)

    assert db_user is not None
    assert db_user.steam_id == user_in.steam_id
    assert db_user.persona_name == user_in.persona_name
    assert db_user.avatar_url == user_in.avatar_url

    retrieved_user = await db_session.get(sqlalchemy_models.User, user_in.steam_id)
    assert retrieved_user is not None
    assert retrieved_user.persona_name == user_in.persona_name

@pytest.mark.asyncio
async def test_get_user_not_found(db_session: AsyncSession):
    user = await crud.get_user(db_session, "non_existent_id")
    assert user is None

@pytest.mark.asyncio
async def test_get_user_found(db_session: AsyncSession):
    user_in = pydantic_models.UserProfileCreate(
        steam_id="test_get_user_found",
        persona_name="GetUserFound",
        avatar_url="http://example.com/avatar.jpg"
    )
    await crud.create_user(db_session, user_in)

    retrieved_user = await crud.get_user(db_session, user_in.steam_id)
    assert retrieved_user is not None
    assert retrieved_user.steam_id == user_in.steam_id
    assert retrieved_user.persona_name == user_in.persona_name

@pytest.mark.asyncio
async def test_create_game(db_session: AsyncSession):
    game_in = pydantic_models.Game(
        id=101,
        name="Test Game 101",
        genres=["Action", "Adventure"],
        tags=["Singleplayer"],
        playtime_forever=0 # Not directly stored on Game model in DB, but part of pydantic model
    )
    db_game = await crud.create_game(db_session, game_in)

    assert db_game is not None
    assert db_game.id == game_in.id
    assert db_game.name == game_in.name
    assert db_game.genres == "Action, Adventure" # Stored as comma-separated string
    assert db_game.tags == "Singleplayer"

    retrieved_game = await db_session.get(sqlalchemy_models.Game, game_in.id)
    assert retrieved_game is not None
    assert retrieved_game.name == game_in.name
    assert retrieved_game.genres == "Action, Adventure"
    assert retrieved_game.tags == "Singleplayer"

@pytest.mark.asyncio
async def test_get_game_not_found(db_session: AsyncSession):
    game = await crud.get_game(db_session, 99999)
    assert game is None

@pytest.mark.asyncio
async def test_get_game_found(db_session: AsyncSession):
    game_in = pydantic_models.Game(id=102, name="Test Game 102", genres=[], tags=[], playtime_forever=0)
    await crud.create_game(db_session, game_in)

    retrieved_game = await crud.get_game(db_session, game_in.id)
    assert retrieved_game is not None
    assert retrieved_game.id == game_in.id

@pytest.mark.asyncio
async def test_add_game_to_user(db_session: AsyncSession):
    # 1. Create user
    user_in = pydantic_models.UserProfileCreate(
        steam_id="user_with_game_test",
        persona_name="UserWithGame",
        avatar_url="http://example.com/avatar.jpg"
    )
    await crud.create_user(db_session, user_in)

    # 2. Game data (Pydantic model, like from "Steam API")
    game_data = pydantic_models.Game(
        id=201,
        name="Awesome Game 201",
        genres=["RPG"],
        tags=["Fantasy"],
        playtime_forever=120 # This is user-specific, passed separately to add_game_to_user
    )

    # 3. Add game to user
    playtime_forever = 120
    playtime_2weeks = 10
    association = await crud.add_game_to_user(
        db_session,
        steam_id=user_in.steam_id,
        game_data=game_data,
        playtime_forever=playtime_forever,
        playtime_2weeks=playtime_2weeks
    )

    assert association is not None
    assert association.user_steam_id == user_in.steam_id
    assert association.game_id == game_data.id
    assert association.playtime_forever == playtime_forever
    assert association.playtime_2weeks == playtime_2weeks

    # Verify game was created
    db_game = await db_session.get(sqlalchemy_models.Game, game_data.id)
    assert db_game is not None
    assert db_game.name == game_data.name
    assert db_game.genres == "RPG" # From game_data
    assert db_game.tags == "Fantasy" # From game_data

    # Verify association exists through User object (optional, get_user would test this)
    db_user = await crud.get_user(db_session, user_in.steam_id)
    assert db_user is not None
    assert len(db_user.game_associations) == 1
    assert db_user.game_associations[0].game_id == game_data.id
    assert db_user.game_associations[0].playtime_forever == playtime_forever

@pytest.mark.asyncio
async def test_add_game_to_user_existing_game(db_session: AsyncSession):
    # 1. Create game first
    existing_game_data = pydantic_models.Game(id=202, name="Existing Game 202", genres=[], tags=[], playtime_forever=0)
    await crud.create_game(db_session, existing_game_data)

    # 2. Create user
    user_in = pydantic_models.UserProfileCreate(
        steam_id="user_with_existing_game",
        persona_name="UserExistingGame",
        avatar_url="http://example.com/avatar.jpg"
    )
    await crud.create_user(db_session, user_in)

    # 3. Add existing game to user
    playtime_forever = 300
    association = await crud.add_game_to_user(
        db_session,
        steam_id=user_in.steam_id,
        game_data=existing_game_data, # Pass the same Pydantic model instance
        playtime_forever=playtime_forever
    )
    assert association is not None
    assert association.game_id == existing_game_data.id
    assert association.playtime_forever == playtime_forever

@pytest.mark.asyncio
async def test_get_user_games(db_session: AsyncSession):
    # 1. Create user
    user_id = "test_get_user_games_id"
    user_in = pydantic_models.UserProfileCreate(steam_id=user_id, persona_name="TestUserGames", avatar_url="")
    await crud.create_user(db_session, user_in)

    # 2. Create and add games
    game1_data = pydantic_models.Game(id=301, name="Game A", genres=["G1", "G2"], tags=["T1"], playtime_forever=100)
    game2_data = pydantic_models.Game(id=302, name="Game B", genres=["G3"], tags=["T2", "T3"], playtime_forever=200)

    await crud.add_game_to_user(db_session, user_id, game1_data, 100)
    await crud.add_game_to_user(db_session, user_id, game2_data, 200)

    # 3. Get user games via CRUD
    user_games_pydantic = await crud.get_user_games(db_session, user_id)

    assert len(user_games_pydantic) == 2
    game_ids_retrieved = {g.id for g in user_games_pydantic}
    assert {301, 302} == game_ids_retrieved

    for game_p in user_games_pydantic:
        if game_p.id == 301:
            assert game_p.name == "Game A"
            assert game_p.playtime_forever == 100
            assert game_p.genres == ["G1", "G2"] # Parsed from DB string
            assert game_p.tags == ["T1"]
        elif game_p.id == 302:
            assert game_p.name == "Game B"
            assert game_p.playtime_forever == 200
            assert game_p.genres == ["G3"]
            assert game_p.tags == ["T2", "T3"]

@pytest.mark.asyncio
async def test_get_user_games_no_user(db_session: AsyncSession):
    games = await crud.get_user_games(db_session, "non_existent_user_for_games")
    assert games == []

@pytest.mark.asyncio
async def test_get_user_games_user_no_games(db_session: AsyncSession):
    user_id = "user_with_no_games_id"
    user_in = pydantic_models.UserProfileCreate(steam_id=user_id, persona_name="UserNoGames", avatar_url="")
    await crud.create_user(db_session, user_in)

    games = await crud.get_user_games(db_session, user_id)
    assert games == []

@pytest.mark.asyncio
async def test_get_games_categorized_by_genre(db_session: AsyncSession):
    user_id = "categorize_user_1"
    await crud.create_user(db_session, pydantic_models.UserProfileCreate(steam_id=user_id, persona_name="CatUser", avatar_url=""))

    game1 = pydantic_models.Game(id=1, name="Game Alpha", genres=["Action", "RPG"], tags=["T1"], playtime_forever=10)
    game2 = pydantic_models.Game(id=2, name="Game Beta", genres=["RPG", "Strategy"], tags=["T2"], playtime_forever=20)
    game3 = pydantic_models.Game(id=3, name="Game Gamma", genres=["Action"], tags=["T3"], playtime_forever=30)
    game4 = pydantic_models.Game(id=4, name="Game Delta", genres=[], tags=["T4"], playtime_forever=40) # No genres
    game5 = pydantic_models.Game(id=5, name="Game Epsilon", genres=None, tags=["T5"], playtime_forever=50) # None genres

    await crud.add_game_to_user(db_session, user_id, game1, 10)
    await crud.add_game_to_user(db_session, user_id, game2, 20)
    await crud.add_game_to_user(db_session, user_id, game3, 30)
    await crud.add_game_to_user(db_session, user_id, game4, 40)
    await crud.add_game_to_user(db_session, user_id, game5, 50)

    categorized_games = await crud.get_games_categorized_by_genre(db_session, user_id)

    assert "Action" in categorized_games
    assert len(categorized_games["Action"]) == 2
    action_game_ids = {g.id for g in categorized_games["Action"]}
    assert {1, 3} == action_game_ids

    assert "RPG" in categorized_games
    assert len(categorized_games["RPG"]) == 2
    rpg_game_ids = {g.id for g in categorized_games["RPG"]}
    assert {1, 2} == rpg_game_ids

    assert "Strategy" in categorized_games
    assert len(categorized_games["Strategy"]) == 1
    assert categorized_games["Strategy"][0].id == 2

    assert "Uncategorized" in categorized_games
    assert len(categorized_games["Uncategorized"]) == 2
    uncategorized_game_ids = {g.id for g in categorized_games["Uncategorized"]}
    assert {4, 5} == uncategorized_game_ids

@pytest.mark.asyncio
async def test_get_games_categorized_by_genre_no_games(db_session: AsyncSession):
    user_id = "categorize_user_no_games"
    await crud.create_user(db_session, pydantic_models.UserProfileCreate(steam_id=user_id, persona_name="CatUserNoGames", avatar_url=""))

    categorized_games = await crud.get_games_categorized_by_genre(db_session, user_id)
    assert categorized_games == {}

@pytest.mark.asyncio
async def test_get_games_categorized_by_genre_user_not_found(db_session: AsyncSession):
    categorized_games = await crud.get_games_categorized_by_genre(db_session, "non_existent_user_for_categories")
    assert categorized_games == {} # Current crud.get_user_games returns [] for non-existent user

# Tests for Deal CRUD operations
from datetime import datetime, timezone, timedelta

@pytest.mark.asyncio
async def test_create_deal(db_session: AsyncSession):
    deal_in = pydantic_models.DealCreate(
        game_name="Test Game for Deal",
        price=19.99,
        store="TestStore",
        url="http://deals.example.com/testgame",
        timestamp=datetime.now(timezone.utc)
    )
    db_deal = await crud.create_deal(db_session, deal_in)

    assert db_deal is not None
    assert db_deal.id is not None
    assert db_deal.game_name == deal_in.game_name
    assert db_deal.price == deal_in.price
    assert db_deal.store == deal_in.store
    assert db_deal.url == deal_in.url
    # Ensure comparison is between aware datetimes if DB returns naive
    # For SQLite, even with DateTime(timezone=True), it might return naive if not configured perfectly
    # or if the default datetime.utcnow was used without explicit tz.
    # The model now uses default=lambda: datetime.now(timezone.utc)
    assert db_deal.timestamp.replace(tzinfo=timezone.utc) == deal_in.timestamp

    retrieved_deal = await db_session.get(sqlalchemy_models.Deal, db_deal.id)
    assert retrieved_deal is not None
    assert retrieved_deal.game_name == deal_in.game_name

@pytest.mark.asyncio
async def test_get_deals_by_game_name(db_session: AsyncSession):
    game_name = "DealsGame"
    now = datetime.now(timezone.utc)

    deal1_in = pydantic_models.DealCreate(game_name=game_name, price=10.00, store="S1", url="u1", timestamp=now - timedelta(minutes=10))
    deal2_in = pydantic_models.DealCreate(game_name=game_name, price=12.00, store="S2", url="u2", timestamp=now - timedelta(minutes=5)) # More recent
    deal3_in = pydantic_models.DealCreate(game_name=game_name, price=9.00, store="S3", url="u3", timestamp=now - timedelta(minutes=20)) # Oldest
    deal_other_game = pydantic_models.DealCreate(game_name="OtherGame", price=5.00, store="S4", url="u4", timestamp=now)

    await crud.create_deal(db_session, deal1_in)
    db_deal2 = await crud.create_deal(db_session, deal2_in) # Store this for assertion
    await crud.create_deal(db_session, deal3_in)
    await crud.create_deal(db_session, deal_other_game)

    # Get deals for "DealsGame"
    retrieved_deals = await crud.get_deals_by_game_name(db_session, game_name, limit=2)

    assert len(retrieved_deals) == 2
    # Deals should be ordered by timestamp desc (most recent first)
    assert retrieved_deals[0].id == db_deal2.id # deal2_in was most recent of the first three for this game
    assert retrieved_deals[0].price == 12.00
    assert retrieved_deals[1].price == 10.00 # deal1_in is next

    # Test limit
    retrieved_deals_limited = await crud.get_deals_by_game_name(db_session, game_name, limit=1)
    assert len(retrieved_deals_limited) == 1
    assert retrieved_deals_limited[0].id == db_deal2.id

    # Test game with no deals
    retrieved_no_deals = await crud.get_deals_by_game_name(db_session, "GameWithNoDeals")
    assert len(retrieved_no_deals) == 0
