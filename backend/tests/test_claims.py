# backend/tests/test_claims.py
"""
Claims endpoint tests.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_claim(authenticated_client: AsyncClient):
    """Test claim creation."""
    response = await authenticated_client.post("/api/v1/claims", json={
        "patient_name": "John Doe"
    })

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["patient_name"] == "John Doe"
    assert "claim_number" in data["data"]


@pytest.mark.asyncio
async def test_list_claims(authenticated_client: AsyncClient):
    """Test listing claims."""
    # Create a claim first
    await authenticated_client.post("/api/v1/claims", json={
        "patient_name": "Test Patient"
    })

    response = await authenticated_client.get("/api/v1/claims")

    assert response.status_code == 200
    data = response.json()
    assert "claims" in data
    assert len(data["claims"]) > 0


@pytest.mark.asyncio
async def test_get_claim(authenticated_client: AsyncClient):
    """Test getting a specific claim."""
    # Create a claim
    create_response = await authenticated_client.post("/api/v1/claims", json={
        "patient_name": "Test Patient"
    })
    claim_id = create_response.json()["data"]["id"]

    # Get the claim
    response = await authenticated_client.get(f"/api/v1/claims/{claim_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["id"] == claim_id


@pytest.mark.asyncio
async def test_delete_claim(authenticated_client: AsyncClient):
    """Test deleting a claim."""
    # Create a claim
    create_response = await authenticated_client.post("/api/v1/claims", json={
        "patient_name": "Test Patient"
    })
    claim_id = create_response.json()["data"]["id"]

    # Delete the claim
    response = await authenticated_client.delete(f"/api/v1/claims/{claim_id}")

    assert response.status_code == 204

    # Verify deletion
    get_response = await authenticated_client.get(f"/api/v1/claims/{claim_id}")
    assert get_response.status_code == 404
