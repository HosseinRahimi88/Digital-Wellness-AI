"""
Account/Auth Settings
-----------------------
Small policy constants for account registration, pulled out of
services/account_service.py so the threshold isn't a magic number
buried in business logic (and so app/pages/Login.py doesn't need its
own copy of the rule to pre-check user input).
"""

# Minimum password length enforced at registration. Matches the
# "At least 8 characters." hint already shown on the register form
# (app/pages/Login.py) - moving the *enforcement* into
# AccountService.register() (previously only checked in the page)
# means every current and future caller gets the same policy for free.
MIN_PASSWORD_LENGTH = 8
