# backend/tests/test_auth.py
"""
Authentication endpoint tests.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, test_user_data: dict):
    """Test user registration."""
    response = await client.post("/api/v1/auth/register", json=test_user_data)

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == test_user_data["email"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user_data: dict):
    """Test registration with duplicate email."""
    await client.post("/api/v1/auth/register", json=test_user_data)
    response = await client.post("/api/v1/auth/register", json=test_user_data)

    assert response.status_code == 422
    assert "already registered" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user_data: dict):
    """Test successful login."""
    await client.post("/api/v1/auth/register", json=test_user_data)

    response = await client.post("/api/v1/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, test_user_data: dict):
    """Test login with invalid credentials."""
    await client.post("/api/v1/auth/register", json=test_user_data)

    response = await client.post("/api/v1/auth/login", json={
        "email": test_user_data["email"],
        "password": "wrongpassword"
    })

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(authenticated_client: AsyncClient):
    """Test getting current user profile."""
    response = await authenticated_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "email" in data["data"]
