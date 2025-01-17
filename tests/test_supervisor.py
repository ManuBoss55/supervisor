"""Test supervisor object."""

from datetime import timedelta
from unittest.mock import AsyncMock, PropertyMock, patch

from aiohttp.client_exceptions import ClientError
import pytest

from supervisor.coresys import CoreSys
from supervisor.supervisor import Supervisor


@pytest.fixture(name="websession")
async def fixture_webession(coresys: CoreSys) -> AsyncMock:
    """Mock of websession."""
    mock_websession = AsyncMock()
    with patch.object(
        type(coresys), "websession", new=PropertyMock(return_value=mock_websession)
    ):
        yield mock_websession


@pytest.fixture(name="supervisor_unthrottled")
async def fixture_supervisor_unthrottled(coresys: CoreSys) -> Supervisor:
    """Get supervisor object with connectivity check throttle removed."""
    with patch(
        "supervisor.supervisor._check_connectivity_throttle_period",
        return_value=timedelta(),
    ):
        yield coresys.supervisor


@pytest.mark.parametrize(
    "side_effect,connectivity", [(ClientError(), False), (None, True)]
)
async def test_connectivity_check(
    supervisor_unthrottled: Supervisor,
    websession: AsyncMock,
    side_effect: Exception | None,
    connectivity: bool,
):
    """Test connectivity check."""
    assert supervisor_unthrottled.connectivity is True

    websession.head.side_effect = side_effect
    await supervisor_unthrottled.check_connectivity()

    assert supervisor_unthrottled.connectivity is connectivity


@pytest.mark.parametrize("side_effect,call_count", [(ClientError(), 3), (None, 1)])
async def test_connectivity_check_throttling(
    coresys: CoreSys,
    websession: AsyncMock,
    side_effect: Exception | None,
    call_count: int,
):
    """Test connectivity check throttled when checks succeed."""
    coresys.supervisor.connectivity = None
    websession.head.side_effect = side_effect

    for _ in range(3):
        await coresys.supervisor.check_connectivity()

    assert websession.head.call_count == call_count
