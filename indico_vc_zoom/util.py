from __future__ import unicode_literals


from indico.core.db import db
from indico.modules.users.models.emails import UserEmail
from indico.modules.users.models.users import User


def find_enterprise_email(user):
    """Find a user's first e-mail address which can be used by the Zoom API.

    :param user: the `User` in question
    :return: the e-mail address if it exists, otherwise `None`
    """
    from indico_vc_zoom.plugin import ZoomPlugin
    providers = [auth.strip() for auth in ZoomPlugin.settings.get('email_domains').split(',')]
    result = UserEmail.query.filter(
        UserEmail.user == user,
        ~User.is_blocked,
        ~User.is_deleted,
        db.or_(UserEmail.email.ilike("%%@{}".format(provider)) for provider in providers)
    ).join(User).first()
    return result.email if result else None
