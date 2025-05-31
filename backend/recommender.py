from typing import Set, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud
from . import models as pydantic_models
from . import db_models as sqlalchemy_models # For type hinting if needed

async def get_user_played_genres(db: AsyncSession, steam_id: str) -> Set[str]:
    """
    Fetches all unique genres from the games a user has played.
    """
    user_games: List[pydantic_models.Game] = await crud.get_user_games(db, steam_id)
    played_genres: Set[str] = set()

    for game in user_games:
        if game.genres:
            for genre in game.genres:
                played_genres.add(genre)

    return played_genres

# Recommendation logic will go here next
async def recommend_deals_by_genre(
    db: AsyncSession,
    steam_id: str,
    max_recommendations_per_genre: int = 3, # Not strictly enforced by current simplified logic
    max_total_recommendations: int = 10
) -> List[pydantic_models.Deal]:

    user_played_genres = await get_user_played_genres(db, steam_id)
    if not user_played_genres:
        return []

    # Get games owned by the user to filter out deals for already owned games
    owned_user_games = await crud.get_user_games(db, steam_id)
    owned_game_names: Set[str] = {game.name for game in owned_user_games}

    potential_deals_map: Dict[str, pydantic_models.Deal] = {} # Use dict to handle duplicates by URL

    for genre in user_played_genres:
        # Find games in the DB that belong to this genre
        games_in_genre: List[sqlalchemy_models.Game] = await crud.get_games_by_genre(db, genre)

        for db_game_in_genre in games_in_genre:
            if db_game_in_genre.name in owned_game_names:
                continue # Skip deals for games the user already owns

            # Fetch deals for this game
            # These are SQLAlchemy Deal models
            deals_for_game_sqla = await crud.get_deals_by_game_name(db, db_game_in_genre.name, limit=max_recommendations_per_genre) # Apply per-genre limit here

            for deal_sqla in deals_for_game_sqla:
                # Convert to Pydantic Deal model
                deal_pydantic = pydantic_models.Deal(
                    game_name=deal_sqla.game_name,
                    price=deal_sqla.price,
                    store=deal_sqla.store,
                    url=deal_sqla.url,
                    timestamp=deal_sqla.timestamp
                )
                # Add to map, ensuring no duplicate URLs for the same deal
                if deal_pydantic.url not in potential_deals_map:
                     # Prioritize deals for games matching more of the user's genres, or cheaper deals?
                     # For now, any deal for a non-owned game in a preferred genre is a candidate.
                     # Simple addition; more sophisticated ranking could be added.
                    potential_deals_map[deal_pydantic.url] = deal_pydantic


    # Convert map values to list and sort by some criteria, e.g., price or timestamp
    # For now, just take the values. A more sophisticated ranking/sorting could be here.
    all_potential_deals = list(potential_deals_map.values())

    # Sort by price (ascending) as a simple ranking heuristic
    all_potential_deals.sort(key=lambda deal: deal.price)

    return all_potential_deals[:max_total_recommendations]
