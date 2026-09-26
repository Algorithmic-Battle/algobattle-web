import json
from contextlib import asynccontextmanager
from importlib.resources import as_file, files
from pathlib import Path

from alembic.command import stamp, upgrade
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy import URL, create_engine, text

from algobattle_web.api import SchemaRoute, router as api
from algobattle_web.models import Base, ServerSettings, User
from algobattle_web.util import EnvConfig, PermissionExcpetion, SessionLocal, ValueTaken


def database_exists(url: URL) -> bool:
    """Checks whether the configured database already exists."""
    backend = url.get_backend_name()

    if backend == "sqlite":
        database = url.database
        if database in (None, ":memory:"):
            return True
        return Path(database).exists()

    admin_url = url.set(database=None)
    try:
        with create_engine(admin_url).connect() as connection:
            if backend == "mysql":
                exists = connection.execute(
                    text(
                        "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
                        "WHERE SCHEMA_NAME = :name"
                    ),
                    {"name": url.database},
                ).scalar_one_or_none()
                return exists is not None
            if backend == "postgresql":
                exists = connection.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :name"),
                    {"name": url.database},
                ).scalar_one_or_none()
                return exists is not None
    except Exception:
        return False

    return False


def create_database(url: URL) -> None:
    """Creates the configured database if it does not already exist."""
    backend = url.get_backend_name()
    database_name = url.database

    if backend == "sqlite":
        if database_name and database_name != ":memory:":
            Path(database_name).parent.mkdir(parents=True, exist_ok=True)
        return

    if database_name is None:
        raise ValueError("A database name is required to create the database.")

    admin_url = url.set(database=None)
    with create_engine(admin_url).connect() as connection:
        if backend == "mysql":
            connection.execute(text(f"CREATE DATABASE `{database_name}`"))
        elif backend == "postgresql":
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        else:
            raise ValueError(f"Unsupported database backend: {backend}")
        connection.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine(EnvConfig.get().db_url)
    SessionLocal.configure(bind=engine)

    # this creates the database itself, alembic/sqlalchemy code below creates the tables in it
    if not database_exists(engine.url):
        create_database(engine.url)

    # because python packaged may be installed to eg zipfiles we need make sure all the data is actually on disk
    # however, that isn't easy here since alembic (presumably) expects a bunch of files in a certain structure.
    # this code's invocation of alembic will (probably) just break if you use esoteric install options 🤷‍♀️
    data_files = files("algobattle_web.alembic")
    with as_file(data_files / "alembic.ini") as alembic_ini:
        alembic_cfg = Config(alembic_ini)
        alembic_cfg.set_main_option("script_location", str(alembic_ini.parent))
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_revs = context.get_current_heads()
            if not current_revs:
                Base.metadata.create_all(bind=engine)
                stamp(alembic_cfg, "head")
            else:
                upgrade(alembic_cfg, "head")

    with SessionLocal() as db:
        try:
            ServerSettings.get(db)
        except RuntimeError:
            db.add(ServerSettings())
        root = User.get(db, "")
        if root is None:
            root = User(email="", name="Root", is_admin=True)
            db.add(root)
            db.commit()
        print(f"Root user login link:\n{EnvConfig.get().base_url}?login_token={root.login_token(db)}")
    yield


def generate_route_name(route: APIRoute) -> str:
    return route.name

app = FastAPI(lifespan=lifespan, generate_unique_id_function=generate_route_name)


@app.exception_handler(RequestValidationError)
def err_handler(request: Request, e: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            {
                "detail": e.errors(),
                "body": e.body,
            }
        ),
    )


@app.exception_handler(PermissionExcpetion)
def perm_err(request: Request, e: PermissionError):
    raise HTTPException(status.HTTP_403_FORBIDDEN)


@app.exception_handler(ValueTaken)
def val_taken_err(request: Request, e: ValueTaken):
    return JSONResponse(
        status_code=409,
        content=jsonable_encoder(
            {
                "type": "value_taken",
                "field": e.field,
                "value": e.value,
                "object": e.object,
            }
        ),
    )


app.include_router(api)
for route in app.routes:
    if isinstance(route, SchemaRoute):
        route.operation_id = route.name


app.add_middleware(
    CORSMiddleware,
    allow_origins=[EnvConfig.get().base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_openapi():
    """Prints the openapi.json schema."""
    print(json.dumps(app.openapi()))
