"""Custom request types for static type checking only.

Both _AHCUser and AuthenticatedRequest live exclusively under TYPE_CHECKING
so Django's model metaclass never sees _AHCUser(User) at runtime.

Usage in views:

    from __future__ import annotations
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from ahc.types import AuthenticatedRequest

    class MyView(LoginRequiredMixin, ...):
        request: AuthenticatedRequest

The 'from __future__ import annotations' import makes all class-body
annotations lazy (PEP 563), so Python evaluates them only when explicitly
requested — never at class definition time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.http import HttpRequest

    from ahc.apps.users.models import Profile

    class _AHCUser(User):
        profile: Profile

    class AuthenticatedRequest(HttpRequest):
        user: _AHCUser  # type: ignore[assignment]
