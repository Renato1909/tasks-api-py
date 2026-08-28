import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_session

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
TestSessionMaker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


async def override_get_session():
    async with TestSessionMaker() as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def user_token(client):
    email = "test@example.com"
    password = "senha1234"
    r = await client.post("/api/register", json={"email": email, "password": password})
    assert r.status_code == 201
    r = await client.post("/api/login", json={"email": email, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_register_duplicate_email(client):
    email = "dup@example.com"
    pw = "senha1234"
    r1 = await client.post("/api/register", json={"email": email, "password": pw})
    assert r1.status_code == 201
    r2 = await client.post("/api/register", json={"email": email, "password": pw})
    assert r2.status_code == 400


async def test_login_invalid_creds(client):
    r = await client.post("/api/login", json={"email": "no@ex.com", "password": "senha1234"})
    assert r.status_code == 401


async def test_create_task(client):
    email = "t1@example.com"
    pw = "senha1234"
    await client.post("/api/register", json={"email": email, "password": pw})
    r = await client.post("/api/login", json={"email": email, "password": pw})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/tasks", json={"title": "Estudar FastAPI", "description": "async + await"}, headers=h)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Estudar FastAPI"
    assert data["status"] == "pending"
    assert "id" in data


async def test_list_tasks(client):
    email = "t2@example.com"
    pw = "senha1234"
    await client.post("/api/register", json={"email": email, "password": pw})
    r = await client.post("/api/login", json={"email": email, "password": pw})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    await client.post("/api/tasks", json={"title": "Tarefa 1"}, headers=h)
    await client.post("/api/tasks", json={"title": "Tarefa 2", "status": "done"}, headers=h)
    r = await client.get("/api/tasks", headers=h)
    assert r.status_code == 200
    tasks = r.json()
    assert len(tasks) == 2
    titles = {t["title"] for t in tasks}
    assert titles == {"Tarefa 1", "Tarefa 2"}


async def test_filter_tasks_by_status(client):
    email = "t3@example.com"
    pw = "senha1234"
    await client.post("/api/register", json={"email": email, "password": pw})
    r = await client.post("/api/login", json={"email": email, "password": pw})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    await client.post("/api/tasks", json={"title": "Pendente"}, headers=h)
    await client.post("/api/tasks", json={"title": "Feita", "status": "done"}, headers=h)
    r = await client.get("/api/tasks?status=done", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["title"] == "Feita"


async def test_get_task(client):
    email = "t4@example.com"
    pw = "senha1234"
    await client.post("/api/register", json={"email": email, "password": pw})
    r = await client.post("/api/login", json={"email": email, "password": pw})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/tasks", json={"title": "Get me"}, headers=h)
    task_id = r.json()["id"]
    r2 = await client.get(f"/api/tasks/{task_id}", headers=h)
    assert r2.status_code == 200
    assert r2.json()["id"] == task_id


async def test_get_task_not_found(client):
    email = "t5@example.com"
    pw = "senha1234"
    await client.post("/api/register", json={"email": email, "password": pw})
    r = await client.post("/api/login", json={"email": email, "password": pw})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    r = await client.get("/api/tasks/999999", headers=h)
    assert r.status_code == 404


async def test_update_task(client):
    email = "t6@example.com"
    pw = "senha1234"
    await client.post("/api/register", json={"email": email, "password": pw})
    r = await client.post("/api/login", json={"email": email, "password": pw})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/tasks", json={"title": "Original"}, headers=h)
    task_id = r.json()["id"]
    r2 = await client.patch(f"/api/tasks/{task_id}", json={"title": "Atualizado", "status": "done"}, headers=h)
    assert r2.status_code == 200
    data = r2.json()
    assert data["title"] == "Atualizado"
    assert data["status"] == "done"


async def test_delete_task(client):
    email = "t7@example.com"
    pw = "senha1234"
    await client.post("/api/register", json={"email": email, "password": pw})
    r = await client.post("/api/login", json={"email": email, "password": pw})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/tasks", json={"title": "Para apagar"}, headers=h)
    task_id = r.json()["id"]
    r2 = await client.delete(f"/api/tasks/{task_id}", headers=h)
    assert r2.status_code == 204
    r3 = await client.get(f"/api/tasks/{task_id}", headers=h)
    assert r3.status_code == 404


async def test_unauthorized_access(client):
    r = await client.get("/api/tasks")
    assert r.status_code == 401
    r2 = await client.post("/api/tasks", json={"title": "X"})
    assert r2.status_code == 401