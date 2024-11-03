import datetime
import json
import logging
from enum import StrEnum

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

log = logging.getLogger("robomaf.databse")

install()

Base = declarative_base()
engine = create_engine("sqlite+pysqlite:///robomaf.db")
Session = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)


class UserStatus(StrEnum):
    CREATING_GAME = "CreatingGame"
    GETTING_PLAYERS = "GettingPlayers"
    CONFIRM_SHUFFLE = "ConfirmShuffle"
    GETTING_GAME_ROLES = "GettingGameRoles"
    DISTRIBUTION_ROLES = "DistributingRoles"
    CREATING_SCENARIO = "CreateScenario"
    GETTING_SCENARIO_ROLES = "GettingScenarioRoles"
    GETTING_SCENARIO_NAME = "GettingScenarioName"


class Game(Base):
    __tablename__ = "games"
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


class Scenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    roles: Mapped[list[str]] = mapped_column(Text, default="[]")

    @property
    def roles_list(self) -> list[str]:
        return json.loads(self.roles)

    @roles_list.setter
    def roles_list(self, value: list[str]):
        self.roles = json.dumps(value)

    @property
    def n_roles(self):
        return len(self.roles_list)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[UserStatus]


def has_unfinished_game(user_id: int) -> bool:
    with Session.begin() as session:
        return session.query(Game).filter(Game.id == user_id).first() is not None


def create_user(owner_id: int, status: UserStatus):
    with Session() as session:
        new_user = User(id=owner_id, status=status)
        session.add(new_user)
        session.commit()


def create_game(owner_id: int, players: list[str]):
    with Session() as session:
        user = session.query(User).filter_by(id=owner_id).first()
        if not user:
            create_user(owner_id, UserStatus.CREATING_GAME)
        new_game = Game(id=owner_id)
        new_game.player_list = players
        session.add(new_game)
        session.commit()


def get_players(owner_id: int) -> list[str]:
    with Session() as session:
        game = session.query(Game).filter_by(id=owner_id).first()
        if game:
            return game.player_list
    log.info("[red] ERROR")
    raise ValueError(f"No user found with id {owner_id}.")


def set_players(owner_id: int, players: list[str]):
    with Session() as session:
        game = session.query(Game).filter_by(id=owner_id).first()
        if game:
            game.player_list = players
            session.commit()
            return

    raise ValueError(f"No user found with id {owner_id}.")


def get_roles(owner_id: int) -> list[str]:
    with Session() as session:
        game = session.query(Game).filter_by(id=owner_id).first()
        if game:
            return game.roles_list

    raise ValueError(f"No user found with id {owner_id}.")


def set_game_roles(owner_id: int, roles: list[str]):
    with Session() as session:
        game = session.query(Game).filter_by(id=owner_id).first()
        if game:
            game.roles_list = roles
            session.commit()
            return

    raise ValueError(f"No user found with id {owner_id}.")


def set_scenario_roles(scenario_name, roles: list[str]):
    with Session() as session:
        scenario = session.query(Scenario).filter_by(name=scenario_name).first()
        if scenario:
            scenario.roles_list = roles
            session.commit()
            return

    raise ValueError(f"No scenarios found with name {scenario_name}.")


def get_assigned_roles(owner_id: int) -> list[str]:
    with Session() as session:
        game = session.query(Game).filter_by(id=owner_id).first()
        if game:
            return game.assigned_roles_list

    raise ValueError(f"No user found with id {owner_id}.")


def set_assigned_roles(owner_id: int, assigned_roles: list[str]):
    with Session() as session:
        game = session.query(Game).filter_by(id=owner_id).first()
        if game:
            game.assigned_roles_list = assigned_roles
            session.commit()
            return

    raise ValueError(f"No user found with id {owner_id}.")


def get_status(owner_id: int) -> UserStatus:
    with Session() as session:
        user = session.query(User).filter_by(id=owner_id).first()
        if user:
            return user.status

    raise ValueError(f"No user found with id {owner_id}")


def set_status(owner_id: int, status: UserStatus) -> None:
    with Session() as session:
        user = session.query(User).filter_by(id=owner_id).first()
        if user:
            user.status = status
            session.commit()
        else:
            create_user(owner_id, status=status)


def delete_game(owner_id: int):
    with Session() as session:
        game = session.query(Game).filter_by(id=owner_id).first()
        if game:
            session.delete(game)
            session.commit()
            return

    raise ValueError(f"No user found with id {owner_id}.")


def get_all_scenarios():
    with Session() as session:
        return session.query(Scenario).all()


def get_scenario_by_name(name: str):
    with Session() as session:
        return session.query(Scenario).filter_by(name=name)


def create_scenario(name: str, roles: list[str]):
    with Session() as session:
        new_scenario = Scenario(name=name)
        new_scenario.roles_list = roles
        session.add(new_scenario)
        session.commit()
