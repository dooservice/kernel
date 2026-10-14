from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from .config import Config
from .security import CookieSigner, PasswordHasher


class KernelDependencies:
    """What a route needs of the kernel."""

    @staticmethod
    def provide_config(request: Request) -> Config:
        return request.app.state.config

    @staticmethod
    def provide_cookie_signer(request: Request) -> CookieSigner:
        return request.app.state.cookie_signer

    @staticmethod
    def provide_password_hasher(request: Request) -> PasswordHasher:
        return request.app.state.password_hasher


AppConfig = Annotated[Config, Depends(KernelDependencies.provide_config)]
AppCookieSigner = Annotated[CookieSigner, Depends(KernelDependencies.provide_cookie_signer)]
AppPasswordHasher = Annotated[PasswordHasher, Depends(KernelDependencies.provide_password_hasher)]
