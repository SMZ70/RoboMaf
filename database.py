import datetime
import json

from rich.traceback import install
from sqlalchemy import (
    DateTime,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    Mapped,
    declarative_base,
    mapped_column,
    sessionmaker,
)

install()

Base = declarative_base()
engine = create_engine("sqlite+pysqlite:///robomaf.db")
Session = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)


class Game(Base):
    __tablename__ = "game"
    id: Mapped[int] = mapped_column(primary_key=True)
    start_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.datetime.now(datetime.UTC)
    )
    players: Mapped[list[str]] = mapped_column(Text, default="[]")
    roles: Mapped[list[str]] = mapped_column(Text, default="[]")
    assigned_roles: Mapped[list[str]] = mapped_column(Text, default="[]")

    @property
    def player_list(self) -> list[str]:
        return json.loads(self.players)

    @player_list.setter
    def player_list(self, value: list[str]):
        self.players = json.dumps(value)

    @property
    def roles_list(self) -> list[str]:
        return json.loads(self.roles)

    @roles_list.setter
    def roles_list(self, value: list[str]):
        self.roles = json.dumps(value)

    @property
    def assigned_roles_list(self) -> list[str]:
        return json.loads(self.assigned_roles)

    @assigned_roles_list.setter
    def assigned_roles_list(self, value: list[str]):
        self.assigned_roles = json.dumps(value)

    def add_player(self, value: str):
        self.players = json.dumps(json.loads(self.players) + [value])

    def add_role(self, value: str):
        self.roles = json.dumps(json.loads(self.roles) + [value])


def has_unfinished_game(user_id: int) -> bool:
    with Session.begin() as session:
        return (
            session.query(Game).filter(Game.id == user_id).first() is not None
        )


def create_game(owner_id: int, players: list[str]):
    with Session() as session:
        new_game = Game(id=owner_id)
        new_game.player_list = players
        session.add(new_game)
        session.commit()


def get_players(owner_id: int) -> list[str]:
    with Session() as session:
        game = session.query(Game).filter_by(id=owner_id).first()
        if game:
            return game.player_list

    raise ValueError(f"No games found for owner id {owner_id}.")


def set_players(owner_id: int, players: list[str]):
    with Session() as session:
        game = session.query(Game).filter_by(id=owner_id).first()
        if game:
            game.player_list = players
            session.commit()
            return

    raise ValueError(f"No games found for owner id {owner_id}.")


def get_roles(owner_id: int) -> list[str]:
    with Session() as session:
        game = session.query(Game).filter_by(id=owner_id).first()
        if game:
            return game.roles_list

    raise ValueError(f"No games found for owner id {owner_id}.")


def set_roles(owner_id: int, roles: list[str]):
    with Session() as session:
        game = session.query(Game).filter_by(id=owner_id).first()
        if game:
            game.roles_list = roles
            session.commit()
            return

    raise ValueError(f"No games found for owner id {owner_id}.")


def get_assigned_roles(owner_id: int) -> list[str]:
    with Session() as session:
        game = session.query(Game).filter_by(id=owner_id).first()
        if game:
            return game.assigned_roles_list

    raise ValueError(f"No games found for owner id {owner_id}.")


def set_assigned_roles(owner_id: int, assigned_roles: list[str]):
    with Session() as session:
        game = session.query(Game).filter_by(id=owner_id).first()
        if game:
            game.assigned_roles_list = assigned_roles
            session.commit()
            return

    raise ValueError(f"No games found for owner id {owner_id}.")


def delete_game(owner_id: int):
    with Session() as session:
        game = session.query(Game).filter_by(id=owner_id).first()
        if game:
            session.delete(game)
            session.commit()
            return

    raise ValueError(f"No games found for owner id {owner_id}.")
