from sqlalchemy import Column, String, Integer, ForeignKey, Table, Float, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime # For default timestamp

# Association Table for User and Game (Many-to-Many)
user_game_association = Table(
    'user_game_playtime', Base.metadata,
    Column('user_steam_id', String, ForeignKey('users.steam_id'), primary_key=True),
    Column('game_id', Integer, ForeignKey('games.id'), primary_key=True),
    Column('playtime_forever', Integer, default=0),
    Column('playtime_2weeks', Integer, nullable=True)
)

class User(Base):
    __tablename__ = "users"

    steam_id = Column(String, primary_key=True, index=True)
    persona_name = Column(String, index=True)
    avatar_url = Column(String)

    # Relationship to Game through the association table
    # 'games' attribute in User model, 'users' attribute in Game model
    games = relationship(
        "Game",
        secondary=user_game_association,
        back_populates="users",
        lazy="selectin" # Use selectin loading for async
    )
    # Direct access to association table entries for this user
    game_associations = relationship("UserGameAssociation", back_populates="user", lazy="selectin", overlaps="games")


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    genres = Column(String, nullable=True) # Store as comma-separated string
    tags = Column(String, nullable=True)   # Store as comma-separated string

    # Relationship to User through the association table
    users = relationship(
        "User",
        secondary=user_game_association,
        back_populates="games",
        lazy="selectin", # Use selectin loading for async
        overlaps="game_associations" # As per SAWarning
    )
     # Direct access to association table entries for this game
    # This defines how a Game object can get its list of UserGameAssociation objects
    user_associations = relationship("UserGameAssociation", back_populates="game", lazy="selectin", overlaps="users") # Changed as per new SAWarning


# Model to directly interact with the association table if needed,
# for example, to update playtime easily.
# This class maps to the user_game_association Table defined above.
class UserGameAssociation(Base):
    __table__ = user_game_association # Map to the existing Table object

    # The columns are already defined in the Table object.
    # SQLAlchemy will inspect user_game_association to find these.
    # However, for relationship loading and typing, it's good to have them here.
    # We can remove these if they cause issues with the mapping,
    # but usually, SQLAlchemy is smart enough if they match the Table's columns.
    # Columns are inherited from the __table__ object.
    # Type hints can be added for clarity if needed, e.g.:
    # user_steam_id: str
    # game_id: int
    # playtime_forever: int
    # playtime_2weeks: int | None

    # This defines how a UserGameAssociation object gets its User
    user = relationship("User", back_populates="game_associations", lazy="selectin", overlaps="games") # Changed as per new SAWarning
    # This defines how a UserGameAssociation object gets its Game
    game = relationship("Game", back_populates="user_associations", lazy="selectin", overlaps="users") # Changed as per new SAWarning

class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    game_name = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)
    store = Column(String, nullable=False)
    url = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
