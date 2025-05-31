from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload


from . import db_models as sqlalchemy_models
from . import models as pydantic_models

async def create_user(db: AsyncSession, user: pydantic_models.UserProfileCreate) -> sqlalchemy_models.User:
    """
    Creates a new user in the database.
    """
    db_user = sqlalchemy_models.User(
        steam_id=user.steam_id,
        persona_name=user.persona_name,
        avatar_url=user.avatar_url
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_user(db: AsyncSession, steam_id: str) -> sqlalchemy_models.User | None:
    """
    Retrieves a user by Steam ID, including their games and playtime.
    """
    result = await db.execute(
        select(sqlalchemy_models.User)
        .where(sqlalchemy_models.User.steam_id == steam_id)
        .options(
            selectinload(sqlalchemy_models.User.game_associations).options(
                selectinload(sqlalchemy_models.UserGameAssociation.game)
            )
        )
    )
    return result.scalars().first()

async def get_game(db: AsyncSession, game_id: int) -> sqlalchemy_models.Game | None:
    """
    Retrieves a game by its ID.
    """
    result = await db.execute(
        select(sqlalchemy_models.Game).where(sqlalchemy_models.Game.id == game_id)
    )
    return result.scalars().first()

async def create_game(db: AsyncSession, game: pydantic_models.Game) -> sqlalchemy_models.Game:
    """
    Creates a new game in the database.
    Note: Pydantic Game model includes genres, tags, playtime.
    SQLAlchemy Game model currently only has id, name.
    This will need adjustment if we want to store genres/tags in db_models.Game.
    """
    db_game = sqlalchemy_models.Game(
        id=game.id,
        name=game.name,
        genres=", ".join(game.genres) if game.genres else None,
        tags=", ".join(game.tags) if game.tags else None
    )
    db.add(db_game)
    await db.commit()
    await db.refresh(db_game)
    return db_game

async def add_game_to_user(
    db: AsyncSession,
    steam_id: str,
    game_data: pydantic_models.Game, # game_data from "Steam API" (Pydantic model)
    playtime_forever: int,
    playtime_2weeks: int | None = None
) -> sqlalchemy_models.UserGameAssociation:
    """
    Adds a game to a user's library with playtime information.
    Creates the game if it doesn't exist.
    """
    # Check if game exists, create if not
    db_game = await get_game(db, game_data.id)
    if not db_game:
        # Create a new pydantic_models.Game to pass to create_game
        # This is a bit redundant as game_data is already that type,
        # but emphasizes that create_game expects a Pydantic Game model.
        db_game = await create_game(db, game_data)

    # Create the association
    association = sqlalchemy_models.UserGameAssociation(
        user_steam_id=steam_id,
        game_id=db_game.id,
        playtime_forever=playtime_forever,
        playtime_2weeks=playtime_2weeks
    )
    db.add(association)
    await db.commit()
    await db.refresh(association)
    return association

async def get_user_games(db: AsyncSession, steam_id: str) -> list[pydantic_models.Game]:
    """
    Retrieves all games owned by a user, including playtime information,
    formatted as Pydantic Game models.
    """
    user = await get_user(db, steam_id) # This get_user already loads game_associations and games
    if not user:
        return []

    games_with_playtime = []
    for assoc in user.game_associations:
        game_model = pydantic_models.Game(
            id=assoc.game.id,
            name=assoc.game.name,
            genres=assoc.game.genres.split(", ") if assoc.game.genres else [],
            tags=assoc.game.tags.split(", ") if assoc.game.tags else [],
            playtime_forever=assoc.playtime_forever
            # playtime_2weeks can be added if needed in the Pydantic model
        )
        games_with_playtime.append(game_model)

    return games_with_playtime

async def get_games_categorized_by_genre(db: AsyncSession, steam_id: str) -> dict[str, list[pydantic_models.Game]]:
    """
    Retrieves and categorizes games for a user by genre.
    Returns a dictionary where keys are genres and values are lists of Game objects.
    """
    user_games = await get_user_games(db, steam_id) # This returns List[pydantic_models.Game]

    categorized_games: dict[str, list[pydantic_models.Game]] = {}

    if not user_games: # Handles case where user has no games, or user not found by get_user_games
        # get_user_games returns [] if user not found or no games.
        # If differentiation for "user not found" vs "user has no games" is needed here,
        # get_user_games would need to change, or call get_user first.
        # For now, an empty list of games results in empty categories.
        return categorized_games

    for game in user_games:
        if game.genres:
            for genre in game.genres:
                if genre not in categorized_games:
                    categorized_games[genre] = []
                categorized_games[genre].append(game)
        else:
            # Handle games with no genres or empty genre list
            # Optionally, could add to a default category like "Uncategorized"
            if "Uncategorized" not in categorized_games:
                categorized_games["Uncategorized"] = []
            categorized_games["Uncategorized"].append(game)

    return categorized_games

# CRUD operations for Deals

async def create_deal(db: AsyncSession, deal: pydantic_models.DealCreate) -> sqlalchemy_models.Deal:
    """
    Creates a new deal in the database.
    """
    db_deal = sqlalchemy_models.Deal(
        game_name=deal.game_name,
        price=deal.price,
        store=deal.store,
        url=deal.url,
        timestamp=deal.timestamp # Assuming DealCreate provides this
    )
    db.add(db_deal)
    await db.commit()
    await db.refresh(db_deal)
    return db_deal

async def get_deals_by_game_name(
    db: AsyncSession, game_name: str, limit: int = 10
) -> list[sqlalchemy_models.Deal]:
    """
    Retrieves recent deals for a game, ordered by timestamp descending.
    """
    result = await db.execute(
        select(sqlalchemy_models.Deal)
        .where(sqlalchemy_models.Deal.game_name == game_name)
        .order_by(sqlalchemy_models.Deal.timestamp.desc())
        .limit(limit)
    )
    return list(result.scalars().all())

async def get_games_by_genre(db: AsyncSession, genre_name: str) -> list[sqlalchemy_models.Game]:
    """
    Retrieves games that have the specified genre in their genre list.
    Uses LIKE query for comma-separated string matching.
    """
    # This is a simple LIKE query. For more robust genre searching (e.g., case-insensitivity,
    # exact word match in a list), a more complex query or different DB schema might be needed.
    # Example: Search for ", Action," or "Action," or ", Action" or "Action"
    # To handle genres at the beginning, end, or as the only genre.
    # This requires careful construction of LIKE patterns.

    # Pattern 1: genre is the only genre (e.g., "Action")
    pattern1 = genre_name
    # Pattern 2: genre is at the beginning (e.g., "Action, RPG")
    pattern2 = f"{genre_name}, %"
    # Pattern 3: genre is in the middle (e.g., "RPG, Action, Strategy")
    pattern3 = f"%, {genre_name}, %"
    # Pattern 4: genre is at the end (e.g., "RPG, Action")
    pattern4 = f"%, {genre_name}"

    result = await db.execute(
        select(sqlalchemy_models.Game).where(
            (sqlalchemy_models.Game.genres == pattern1) |
            (sqlalchemy_models.Game.genres.ilike(pattern2)) |  # Use ilike for case-insensitivity
            (sqlalchemy_models.Game.genres.ilike(pattern3)) |
            (sqlalchemy_models.Game.genres.ilike(pattern4))
        )
    )
    return list(result.scalars().all())
