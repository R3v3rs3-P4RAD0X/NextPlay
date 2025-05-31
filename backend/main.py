from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse # Added for serving static HTML
import os # Added for path manipulation
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from . import models as pydantic_models # Renamed for clarity
from . import crud
from .database import get_db # Import the dependency

app = FastAPI()

# Placeholder function to simulate fetching Steam data
# This now returns data that's closer to what an external API might give,
# not necessarily a fully formed UserProfile Pydantic model directly.
async def fetch_simulated_steam_api_data(steam_id: str) -> dict:
    # Sample data simulating a Steam API response structure
    return {
        "steam_id": steam_id,
        "persona_name": f"User_{steam_id}_FromSteam",
        "avatar_url": f"https://steamcdn-a.akamaihd.net/steamcommunity/public/images/avatars/{steam_id[-2:]}/{steam_id}_full.jpg",
        "owned_games": [
            {
                "id": 10,
                "name": "Counter-Strike: Global Offensive",
                "genres": ["FPS", "Shooter"],
                "tags": ["Multiplayer", "Competitive", "Action"],
                "playtime_forever": 12000,
                "playtime_2weeks": 120
            },
            {
                "id": 20,
                "name": "Dota 2",
                "genres": ["MOBA", "Strategy"],
                "tags": ["Multiplayer", "Competitive", "eSports"],
                "playtime_forever": 25000,
                "playtime_2weeks": None # No playtime in 2 weeks
            },
            {
                "id": 730, # CS:GO, different ID for testing
                "name": "CS:GO (Alt ID)",
                "genres": ["FPS", "Shooter"],
                "tags": ["Multiplayer", "Competitive", "Action"],
                "playtime_forever": 500,
                "playtime_2weeks": 5
            },
            {
                "id": 30,
                "name": "The Witcher 3: Wild Hunt",
                "genres": ["RPG", "Open World"],
                "tags": ["Singleplayer", "Story Rich", "Fantasy"],
                "playtime_forever": 3000,
                # "playtime_2weeks" is missing, so it should be default None
            }
        ]
    }

def format_user_profile_response(db_user: crud.sqlalchemy_models.User) -> pydantic_models.UserProfile:
    """Helper to convert DB User object to Pydantic UserProfile response model."""
    owned_games_pydantic = []
    if db_user.game_associations:
        for assoc in db_user.game_associations:
            if assoc.game: # Ensure game data is loaded
                owned_games_pydantic.append(
                    pydantic_models.Game(
                        id=assoc.game.id,
                        name=assoc.game.name,
                        genres=assoc.game.genres.split(", ") if assoc.game.genres else [],
                        tags=assoc.game.tags.split(", ") if assoc.game.tags else [],
                        playtime_forever=assoc.playtime_forever
                        # playtime_2weeks is part of UserGameAssociation, not directly in Game Pydantic model
                        # but could be added if the Game Pydantic model is extended
                    )
                )

    return pydantic_models.UserProfile(
        steam_id=db_user.steam_id,
        persona_name=db_user.persona_name,
        avatar_url=db_user.avatar_url,
        owned_games=owned_games_pydantic
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/user/{steam_id}/profile", response_model=pydantic_models.UserProfile)
async def get_user_profile_or_ingest(steam_id: str, db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_user(db, steam_id=steam_id)

    if db_user:
        # User found in DB, format and return
        return format_user_profile_response(db_user)

    # User not found, simulate fetching from Steam API and ingest
    simulated_api_data = await fetch_simulated_steam_api_data(steam_id)

    # Create user profile
    user_create_data = pydantic_models.UserProfileCreate(
        steam_id=simulated_api_data["steam_id"],
        persona_name=simulated_api_data["persona_name"],
        avatar_url=simulated_api_data["avatar_url"]
    )
    await crud.create_user(db, user=user_create_data)

    # Add games to user
    if "owned_games" in simulated_api_data:
        for game_dict in simulated_api_data["owned_games"]:
            # Convert game_dict to Pydantic Game model before passing to CRUD
            # Note: Pydantic Game includes playtime_forever, but it's specific to user,
            # so we extract it for add_game_to_user.
            # Genres/tags are part of the Pydantic model but not fully used in db_game yet.
            pydantic_game = pydantic_models.Game(
                id=game_dict["id"],
                name=game_dict["name"],
                genres=game_dict.get("genres", []),
                tags=game_dict.get("tags", []),
                playtime_forever=game_dict["playtime_forever"] # This is specific to user, handled below
            )
            await crud.add_game_to_user(
                db,
                steam_id=simulated_api_data["steam_id"],
                game_data=pydantic_game, # Pass the Pydantic Game model
                playtime_forever=game_dict["playtime_forever"],
                playtime_2weeks=game_dict.get("playtime_2weeks")
            )

    # Retrieve the newly created and populated user profile from DB
    # get_user should now return the user with all game associations
    newly_ingested_user = await crud.get_user(db, steam_id=steam_id)
    if not newly_ingested_user:
        # This should ideally not happen if creation was successful
        # Handle error appropriately, e.g., raise HTTPException
        raise Exception("Failed to retrieve user after ingestion.")

    return format_user_profile_response(newly_ingested_user)

@app.get("/user/{steam_id}/categories", response_model=pydantic_models.CategorizedGamesResponse)
async def get_user_game_categories(steam_id: str, db: AsyncSession = Depends(get_db)):
    # First, check if user exists. If not, crud.get_user returns None.
    db_user = await crud.get_user(db, steam_id=steam_id)
    if not db_user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")

    categorized_games_dict = await crud.get_games_categorized_by_genre(db, steam_id=steam_id)
    return pydantic_models.CategorizedGamesResponse(categories=categorized_games_dict)

@app.get("/deals/{game_name}", response_model=List[pydantic_models.Deal])
async def get_game_deals(game_name: str, db: AsyncSession = Depends(get_db)):
    from . import scraper # Import scraper module

    # Try to fetch recent deals from the database
    db_deals_sqlalchemy = await crud.get_deals_by_game_name(db, game_name=game_name, limit=10) # Default limit

    if db_deals_sqlalchemy:
        # Convert SQLAlchemy models to Pydantic models for response
        pydantic_db_deals = [
            pydantic_models.Deal(
                game_name=deal.game_name,
                price=deal.price,
                store=deal.store,
                url=deal.url,
                timestamp=deal.timestamp
            ) for deal in db_deals_sqlalchemy
        ]
        return pydantic_db_deals

    # No deals in DB (or not recent enough, simplified to "no deals" for now)
    # Call scraper to get fresh deals
    scraped_deals_pydantic = await scraper.fetch_simulated_deals_for_game(game_name)

    if not scraped_deals_pydantic:
        return [] # Scraper found no deals either

    # Store newly scraped deals in the database
    for deal_pydantic in scraped_deals_pydantic:
        # Need to convert Pydantic Deal to Pydantic DealCreate for crud.create_deal
        deal_create_obj = pydantic_models.DealCreate(**deal_pydantic.model_dump())
        await crud.create_deal(db, deal=deal_create_obj)

    # Return the newly fetched (and now stored) deals.
    # The Pydantic models from the scraper are already in the correct response format.
    return scraped_deals_pydantic

@app.get("/user/{steam_id}/recommendations", response_model=pydantic_models.RecommendationsResponse)
async def get_user_recommendations(steam_id: str, db: AsyncSession = Depends(get_db)):
    from . import recommender # Import recommender module

    # Check if user exists
    db_user = await crud.get_user(db, steam_id=steam_id)
    if not db_user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")

    recommended_deals = await recommender.recommend_deals_by_genre(db, steam_id=steam_id)

    return pydantic_models.RecommendationsResponse(deals=recommended_deals)

# Determine the path to the frontend directory relative to main.py
# main.py is in backend/, frontend/ is sibling to backend/
# So, ../frontend/index.html
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
INDEX_HTML_PATH = os.path.join(FRONTEND_DIR, "index.html")

@app.get("/", response_class=FileResponse, include_in_schema=False)
async def serve_index():
    if not os.path.exists(INDEX_HTML_PATH):
        raise HTTPException(status_code=404, detail="Index.html not found")
    return FileResponse(INDEX_HTML_PATH)
