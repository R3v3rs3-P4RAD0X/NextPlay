from typing import List, Optional, Dict # Added Dict
from pydantic import BaseModel

class Game(BaseModel):
    id: int
    name: str
    genres: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    playtime_forever: int # This is user-specific, but often included in "owned game" details from APIs

class UserProfile(BaseModel):
    steam_id: str
    persona_name: str
    avatar_url: str
    owned_games: List[Game] # This will be populated from DB relation

# Pydantic model for creating a user (e.g., from API input)
class UserProfileCreate(BaseModel):
    steam_id: str
    persona_name: str
    avatar_url: str

class PlayStats(BaseModel):
    game_id: int
    playtime_2weeks: Optional[int] = None
    playtime_forever: int

from datetime import datetime # Added for Deal model

# Response model for categorized games
class CategorizedGamesResponse(BaseModel):
    categories: Dict[str, List[Game]]

# Pydantic model for a game deal
class Deal(BaseModel):
    game_name: str
    price: float
    store: str
    url: str
    timestamp: datetime

# Pydantic model for creating a deal (e.g., from scraper input)
# Timestamp might be auto-generated on DB side or passed from scraper
class DealCreate(BaseModel):
    game_name: str
    price: float
    store: str
    url: str
    timestamp: datetime # Scraper will provide this

# Response model for recommendations
class RecommendationsResponse(BaseModel):
    deals: List[Deal]
    # Could add other recommendation types here in the future, e.g.:
    # unplayed_owned_games: List[Game]
