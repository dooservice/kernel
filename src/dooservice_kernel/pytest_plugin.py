"""The kernel's pytest fixtures, loaded by pytest itself once the package is installed.

`kernel_harness` is `KernelHarness`, to open as many apps as a test needs:

    async def test_orders(kernel_harness) -> None:
        async with kernel_harness([ShopModule()]) as shop:
            assert (await shop.client.get("/api/orders")).status_code == 200
"""

from __future__ import annotations

import pytest

from .testing import KernelHarness


@pytest.fixture
def kernel_harness() -> type[KernelHarness]:
    return KernelHarness
