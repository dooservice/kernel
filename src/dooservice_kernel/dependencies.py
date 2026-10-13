from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from .config import Config
from .security import CookieSigner, PasswordHasher


def provide_config(request: Request) -> Config:
    return request.app.state.config


def provide_cookie_signer(request: Request) -> CookieSigner:
    return request.app.state.cookie_signer


def provide_password_hasher(request: Request) -> PasswordHasher:
    return request.app.state.password_hasher


AppConfig = Annotated[Config, Depends(provide_config)]
AppCookieSigner = Annotated[CookieSigner, Depends(provide_cookie_signer)]
AppPasswordHasher = Annotated[PasswordHasher, Depends(provide_password_hasher)]
