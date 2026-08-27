from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas, auth
from app.database import get_session

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    token: str = Depends(auth.oauth2_scheme),
) -> models.User:
    payload = auth.decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="token invalido ou expirado")
    user = await session.get(models.User, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="usuario nao encontrado")
    return user


@router.post("", response_model=schemas.TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: schemas.TaskCreate,
    session: AsyncSession = Depends(get_session),
    user: models.User = Depends(get_current_user),
):
    task = models.Task(**data.model_dump(), owner_id=user.id)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.get("", response_model=list[schemas.TaskRead])
async def list_tasks(
    status: Optional[str] = Query(None, pattern="^(pending|done)$"),
    session: AsyncSession = Depends(get_session),
    user: models.User = Depends(get_current_user),
):
    stmt = select(models.Task).where(models.Task.owner_id == user.id)
    if status:
        stmt = stmt.where(models.Task.status == status)
    stmt = stmt.order_by(models.Task.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{task_id}", response_model=schemas.TaskRead)
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    user: models.User = Depends(get_current_user),
):
    task = await session.get(models.Task, task_id)
    if not task or task.owner_id != user.id:
        raise HTTPException(status_code=404, detail="tarefa nao encontrada")
    return task


@router.patch("/{task_id}", response_model=schemas.TaskRead)
async def update_task(
    task_id: int,
    data: schemas.TaskUpdate,
    session: AsyncSession = Depends(get_session),
    user: models.User = Depends(get_current_user),
):
    task = await session.get(models.Task, task_id)
    if not task or task.owner_id != user.id:
        raise HTTPException(status_code=404, detail="tarefa nao encontrada")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await session.commit()
    await session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    user: models.User = Depends(get_current_user),
):
    task = await session.get(models.Task, task_id)
    if not task or task.owner_id != user.id:
        raise HTTPException(status_code=404, detail="tarefa nao encontrada")
    await session.delete(task)
    await session.commit()