import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Set, List, Dict
from datetime import datetime, timezone, timedelta

from backend import recommender
from backend import crud
from backend import models as pydantic_models
from backend import db_models as sqlalchemy_models # For creating DB instances directly if needed

@pytest.mark.asyncio
async def test_get_user_played_genres_various_scenarios(db_session: AsyncSession):
    user_id_1 = "user_genres_1" # Has games with genres
    user_id_2 = "user_genres_2" # Has games, some with no/None genres
    user_id_3 = "user_genres_3" # Has no games
    user_id_4 = "user_genres_4" # Non-existent user (get_user_games returns [])

    await crud.create_user(db_session, pydantic_models.UserProfileCreate(steam_id=user_id_1, persona_name="User1", avatar_url=""))
    await crud.create_user(db_session, pydantic_models.UserProfileCreate(steam_id=user_id_2, persona_name="User2", avatar_url=""))
    await crud.create_user(db_session, pydantic_models.UserProfileCreate(steam_id=user_id_3, persona_name="User3", avatar_url=""))

    # Games for User1
    game1_u1 = pydantic_models.Game(id=10, name="G1U1", genres=["Action", "RPG"], tags=[], playtime_forever=100)
    game2_u1 = pydantic_models.Game(id=20, name="G2U1", genres=["RPG", "Strategy"], tags=[], playtime_forever=100)
    await crud.add_game_to_user(db_session, user_id_1, game1_u1, 100)
    await crud.add_game_to_user(db_session, user_id_1, game2_u1, 100)

    # Games for User2
    game1_u2 = pydantic_models.Game(id=30, name="G1U2", genres=["Adventure"], tags=[], playtime_forever=100)
    game2_u2 = pydantic_models.Game(id=40, name="G2U2", genres=[], tags=[], playtime_forever=100) # No genres
    game3_u2 = pydantic_models.Game(id=50, name="G3U2", genres=None, tags=[], playtime_forever=100) # None genres
    await crud.add_game_to_user(db_session, user_id_2, game1_u2, 100)
    await crud.add_game_to_user(db_session, user_id_2, game2_u2, 100)
    await crud.add_game_to_user(db_session, user_id_2, game3_u2, 100)

    # Test User1
    genres_u1 = await recommender.get_user_played_genres(db_session, user_id_1)
    assert genres_u1 == {"Action", "RPG", "Strategy"}

    # Test User2
    genres_u2 = await recommender.get_user_played_genres(db_session, user_id_2)
    assert genres_u2 == {"Adventure"} # Empty/None genres are ignored

    # Test User3 (no games)
    genres_u3 = await recommender.get_user_played_genres(db_session, user_id_3)
    assert genres_u3 == set()

    # Test User4 (non-existent)
    genres_u4 = await recommender.get_user_played_genres(db_session, user_id_4)
    assert genres_u4 == set()

@pytest.mark.asyncio
async def test_recommend_deals_by_genre_basic_scenario(db_session: AsyncSession):
    user_id = "reco_user_1"
    await crud.create_user(db_session, pydantic_models.UserProfileCreate(steam_id=user_id, persona_name="RecoUser1", avatar_url=""))

    # User's played games
    owned_game = pydantic_models.Game(id=100, name="Owned Action Game", genres=["Action"], tags=[], playtime_forever=100)
    await crud.add_game_to_user(db_session, user_id, owned_game, 100)

    # Other games in DB (not owned by user)
    action_game_for_deal = pydantic_models.Game(id=101, name="Action Game With Deal", genres=["Action", "Adventure"], tags=[], playtime_forever=0)
    rpg_game_for_deal = pydantic_models.Game(id=102, name="RPG Game With Deal", genres=["RPG"], tags=[], playtime_forever=0)
    # Game in a genre user hasn't played, but has a deal
    strategy_game_for_deal = pydantic_models.Game(id=103, name="Strategy Game With Deal", genres=["Strategy"], tags=[], playtime_forever=0)

    await crud.create_game(db_session, action_game_for_deal) # Game needs to exist in 'games' table
    await crud.create_game(db_session, rpg_game_for_deal)
    await crud.create_game(db_session, strategy_game_for_deal)


    # Deals for these games
    now = datetime.now(timezone.utc)
    deal1 = pydantic_models.DealCreate(game_name="Action Game With Deal", price=10.0, store="S1", url="u1", timestamp=now)
    deal2 = pydantic_models.DealCreate(game_name="RPG Game With Deal", price=15.0, store="S2", url="u2", timestamp=now)
    deal_owned = pydantic_models.DealCreate(game_name="Owned Action Game", price=5.0, store="S3", url="u3", timestamp=now) # Deal for owned game
    deal_strategy = pydantic_models.DealCreate(game_name="Strategy Game With Deal", price=20.0, store="S4", url="u4", timestamp=now)


    await crud.create_deal(db_session, deal1)
    await crud.create_deal(db_session, deal2)
    await crud.create_deal(db_session, deal_owned)
    await crud.create_deal(db_session, deal_strategy)

    recommendations = await recommender.recommend_deals_by_genre(db_session, user_id)

    assert len(recommendations) == 1 # Only deal1 (Action Game With Deal) should be recommended
                                      # User played "Action". "RPG Game With Deal" is not recommended as user hasn't played RPG.
                                      # Deal for "Owned Action Game" is filtered.
                                      # Deal for "Strategy Game With Deal" is not in user's played genres.

    recommended_deal = recommendations[0]
    assert recommended_deal.game_name == "Action Game With Deal"
    assert recommended_deal.price == 10.0

@pytest.mark.asyncio
async def test_recommend_deals_no_relevant_deals(db_session: AsyncSession):
    user_id = "reco_user_2"
    await crud.create_user(db_session, pydantic_models.UserProfileCreate(steam_id=user_id, persona_name="RecoUser2", avatar_url=""))
    # User played "Action"
    owned_game = pydantic_models.Game(id=200, name="My Action Game", genres=["Action"], tags=[], playtime_forever=100)
    await crud.add_game_to_user(db_session, user_id, owned_game, 100)

    # Deals exist, but not for Action games user doesn't own
    rpg_game = pydantic_models.Game(id=201, name="Some RPG", genres=["RPG"], tags=[], playtime_forever=0)
    await crud.create_game(db_session, rpg_game)
    deal_rpg = pydantic_models.DealCreate(game_name="Some RPG", price=10.0, store="S1", url="u_rpg", timestamp=datetime.now(timezone.utc))
    await crud.create_deal(db_session, deal_rpg)

    recommendations = await recommender.recommend_deals_by_genre(db_session, user_id)
    assert len(recommendations) == 0

@pytest.mark.asyncio
async def test_recommend_deals_user_owns_all_relevant_deal_games(db_session: AsyncSession):
    user_id = "reco_user_3"
    await crud.create_user(db_session, pydantic_models.UserProfileCreate(steam_id=user_id, persona_name="RecoUser3", avatar_url=""))

    # User played "Action", and owns the only game with an Action deal
    owned_action_game_with_deal = pydantic_models.Game(id=300, name="Owned Action Game With Deal", genres=["Action"], tags=[], playtime_forever=100)
    await crud.add_game_to_user(db_session, user_id, owned_action_game_with_deal, 100) # This also creates the game in 'games' table

    deal_owned_action = pydantic_models.DealCreate(game_name="Owned Action Game With Deal", price=10.0, store="S1", url="u_oa", timestamp=datetime.now(timezone.utc))
    await crud.create_deal(db_session, deal_owned_action)

    recommendations = await recommender.recommend_deals_by_genre(db_session, user_id)
    assert len(recommendations) == 0

@pytest.mark.asyncio
async def test_recommend_deals_max_recommendations(db_session: AsyncSession):
    user_id = "reco_user_4"
    await crud.create_user(db_session, pydantic_models.UserProfileCreate(steam_id=user_id, persona_name="RecoUser4", avatar_url=""))
    await crud.add_game_to_user(db_session, user_id, pydantic_models.Game(id=400, name="Game X", genres=["Action"], tags=[], playtime_forever=100), 100)

    now = datetime.now(timezone.utc)
    # Create more deals for "Action" games than max_total_recommendations
    for i in range(15):
        game = pydantic_models.Game(id=401 + i, name=f"Action Game {i+1}", genres=["Action"], tags=[], playtime_forever=0)
        await crud.create_game(db_session, game)
        deal = pydantic_models.DealCreate(game_name=f"Action Game {i+1}", price=float(10 + i), store="S", url=f"u_act_{i}", timestamp=now + timedelta(seconds=i))
        await crud.create_deal(db_session, deal)

    # Test total recommendations limit
    recommendations_total_limit = await recommender.recommend_deals_by_genre(db_session, user_id, max_total_recommendations=5)
    assert len(recommendations_total_limit) == 5

    # Test per-genre limit (less direct to test with current simplified deal fetching, but total limit is primary here)
    # The deals are sorted by price, so we get the cheapest 5.
    assert recommendations_total_limit[0].price == 10.0
    assert recommendations_total_limit[4].price == 14.0


@pytest.mark.asyncio
async def test_recommend_deals_user_no_played_genres(db_session: AsyncSession):
    user_id = "reco_user_5"
    await crud.create_user(db_session, pydantic_models.UserProfileCreate(steam_id=user_id, persona_name="RecoUser5", avatar_url=""))
    # User has a game, but it has no genres
    await crud.add_game_to_user(db_session, user_id, pydantic_models.Game(id=500, name="No Genre Game", genres=[], tags=[], playtime_forever=100), 100)

    recommendations = await recommender.recommend_deals_by_genre(db_session, user_id)
    assert len(recommendations) == 0

@pytest.mark.asyncio
async def test_recommend_deals_duplicate_deal_urls(db_session: AsyncSession):
    user_id = "reco_user_6"
    await crud.create_user(db_session, pydantic_models.UserProfileCreate(steam_id=user_id, persona_name="RecoUser6", avatar_url=""))
    await crud.add_game_to_user(db_session, user_id, pydantic_models.Game(id=600, name="Played Action", genres=["Action"], tags=[], playtime_forever=100), 100)

    game_for_deal = pydantic_models.Game(id=601, name="Action Deal Game", genres=["Action"], tags=[], playtime_forever=0)
    await crud.create_game(db_session, game_for_deal)

    now = datetime.now(timezone.utc)
    # Two deals with same URL but different prices (scraper might produce this, map should deduplicate)
    deal1 = pydantic_models.DealCreate(game_name="Action Deal Game", price=10.0, store="S1", url="unique_url_1", timestamp=now)
    deal2 = pydantic_models.DealCreate(game_name="Action Deal Game", price=9.0, store="S2", url="unique_url_1", timestamp=now + timedelta(seconds=1)) # Newer, different price, same URL

    await crud.create_deal(db_session, deal1)
    await crud.create_deal(db_session, deal2)

    recommendations = await recommender.recommend_deals_by_genre(db_session, user_id)
    assert len(recommendations) == 1 # Should be deduplicated by URL
    assert recommendations[0].url == "unique_url_1"
    # crud.get_deals_by_game_name sorts by timestamp desc.
    # deal2 (price 9.0) is newer and processed first. It's added to potential_deals_map.
    # deal1 (price 10.0) is older, processed next. Its URL is already in the map, so it's skipped.
    # Thus, the deal with price 9.0 is kept.
    assert recommendations[0].price == 9.0

@pytest.mark.asyncio
async def test_get_games_by_genre_crud(db_session: AsyncSession):
    game1 = pydantic_models.Game(id=701, name="GameX", genres=["Action", "RPG"], tags=[], playtime_forever=0)
    game2 = pydantic_models.Game(id=702, name="GameY", genres=["RPG"], tags=[], playtime_forever=0)
    game3 = pydantic_models.Game(id=703, name="GameZ", genres=["Strategy"], tags=[], playtime_forever=0)
    game4 = pydantic_models.Game(id=704, name="GameW", genres=["Action"], tags=[], playtime_forever=0) # Only Action

    await crud.create_game(db_session, game1)
    await crud.create_game(db_session, game2)
    await crud.create_game(db_session, game3)
    await crud.create_game(db_session, game4)

    action_games = await crud.get_games_by_genre(db_session, "Action")
    rpg_games = await crud.get_games_by_genre(db_session, "RPG")
    strategy_games = await crud.get_games_by_genre(db_session, "Strategy")
    unknown_genre_games = await crud.get_games_by_genre(db_session, "UnknownGenre")

    assert len(action_games) == 2
    action_game_ids = {g.id for g in action_games}
    assert {701, 704} == action_game_ids

    assert len(rpg_games) == 2
    rpg_game_ids = {g.id for g in rpg_games}
    assert {701, 702} == rpg_game_ids

    assert len(strategy_games) == 1
    assert strategy_games[0].id == 703

    assert len(unknown_genre_games) == 0
