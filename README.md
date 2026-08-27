# tasks-api-py

![CI](https://github.com/Renato1909/tasks-api-py/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688)
![SQLite](https://img.shields.io/badge/SQLite-async-lightgrey)

API REST de **gerenciamento de tarefas** com **FastAPI**, autenticação **JWT**, banco **SQLite assíncrono** (aiosqlite + SQLAlchemy 2.0) e testes **pytest + httpx**.

## Destaques técnicos

- **FastAPI** com patterns de roteamento modernos (`GET /{task_id}`)
- **SQLAlchemy 2.0 async** + `aiosqlite` — sem threading, tudo assíncrono
- **Autenticação JWT** (HS256) + hash de senha `pbkdf2_sha256` (sem dependência C)
- **Pydantic v2** para validação e serialização
- **Testes de integração** com `httpx.ASGITransport` + banco em memória por teste
- CI no GitHub Actions: `ruff` + `pytest --cov`

## Endpoints

| Método | Rota              | Descrição                          | Auth |
|--------|-------------------|------------------------------------|------|
| GET    | `/health`         | Health check                       | não  |
| POST   | `/api/register`   | Registra usuário                   | não  |
| POST   | `/api/login`      | Login → retorna JWT                | não  |
| POST   | `/api/tasks`      | Cria tarefa                        | sim  |
| GET    | `/api/tasks`      | Lista tarefas (filtro `?status=`)  | sim  |
| GET    | `/api/tasks/{id}` | Obtém tarefa                       | sim  |
| PATCH  | `/api/tasks/{id}` | Atualiza tarefa                    | sim  |
| DELETE | `/api/tasks/{id}` | Deleta tarefa                      | sim  |

### Exemplos

```bash
# Registrar
curl -s -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@ex.com","password":"senha1234"}'
# {"id":1,"email":"user@ex.com","created_at":"2026-08-24T12:00:00"}

# Login
curl -s -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@ex.com","password":"senha1234"}'
# {"access_token":"eyJ...","token_type":"bearer"}

# Criar tarefa
curl -s -X POST http://localhost:8000/api/tasks \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Estudar FastAPI","description":"async + await","status":"pending"}'
# {"id":1,"title":"Estudar FastAPI","description":"async + await","status":"pending","owner_id":1,"created_at":"...","updated_at":"..."}

# Listar com filtro
curl -s -H "Authorization: Bearer <token>" "http://localhost:8000/api/tasks?status=done"
```

## Como rodar

Requisitos: Python 3.12+

```powershell
# Instalar deps
python -m pip install -e .

# Rodar (cria data/tasks.db automaticamente)
uvicorn app.main:app --reload --port 8000
```

Variáveis de ambiente opcionais:

| Variável     | Padrão                        | Descrição                     |
|--------------|-------------------------------|-------------------------------|
| `SECRET_KEY` | `dev-secret-change-in-production` | Chave JWT (trocar em prod!) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/tasks.db` | Caminho do SQLite |

## Como testar

```powershell
pytest -v                 # testes unitários + integração
pytest --cov=app          # com coverage
ruff check .              # lint
```

## Arquitetura

```
app/
├── main.py           # FastAPI app + lifespan (init DB)
├── database.py       # Engine async + session factory
├── models.py         # User, Task (SQLAlchemy)
├── schemas.py        # Pydantic models (request/response)
├── auth.py           # JWT + pbkdf2_sha256
├── routes_auth.py    # /register, /login
└── routes_tasks.py   # CRUD /api/tasks protegido por JWT
tests/
└── test_api.py       # 11 testes de integração (httpx + SQLite :memory:)
```

Fluxo de autenticação:

```
POST /api/register  → 201 + UserRead
POST /api/login     → 200 + Token (JWT HS256, 7 dias)
GET  /api/tasks     → Authorization: Bearer <token> → 200 + list[TaskRead]
```

## Decisões técnicas

- **SQLite + aiosqlite**: zero config, suficiente para portfólio e testes; migra para Postgres trocando só a `DATABASE_URL`
- **`pbkdf2_sha256`**: hash puro Python, sem dependência C (evita problemas de build no Windows/CI)
- **Banco em memória nos testes**: cada teste roda isolado, rápido e determinístico
- **`httpx.ASGITransport`**: testa a app FastAPI real sem subir servidor HTTP real

## Limitações conhecidas (por design)

- Sem refresh token / rotação de JWT
- Sem rate limiting
- Sem paginação em `/api/tasks`
- SQLite não escala para escrita concorrente pesada

## Roadmap

- [ ] Refresh token + rota `/api/refresh`
- [ ] Paginação (`limit`/`offset`) + ordenação
- [ ] Métricas Prometheus (`/metrics`)
- [ ] Dockerfile multi-stage + deploy example

## Licença

[MIT](LICENSE)