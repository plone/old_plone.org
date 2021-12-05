from AccessControl.SecurityManagement import newSecurityManager
from ploneorg.core.interfaces import IPloneOrgCoreLayer
from Products.CMFPlone.factory import _DEFAULT_PROFILE
from Products.CMFPlone.factory import addPloneSite
from Testing.makerequest import makerequest
from zope.interface import directlyProvidedBy
from zope.interface import directlyProvides

import os
import transaction


truthy = frozenset(('t', 'true', 'y', 'yes', 'on', '1'))


def asbool(s):
    """Return the boolean value ``True`` if the case-lowered value of string
    input ``s`` is a :term:`truthy string`. If ``s`` is already one of the
    boolean values ``True`` or ``False``, return it."""
    if s is None:
        return False
    if isinstance(s, bool):
        return s
    s = str(s).strip()
    return s.lower() in truthy


DELETE_EXISTING = asbool(os.getenv("DELETE_EXISTING"))

app = makerequest(app)

request = app.REQUEST

ifaces = [
    IPloneOrgCoreLayer,
] + list(directlyProvidedBy(request))

directlyProvides(request, *ifaces)

admin = app.acl_users.getUserById("admin")
admin = admin.__of__(app.acl_users)
newSecurityManager(None, admin)

SITE_ID = "Plone"

payload = {
    "title": "Plone CMS: Open Source Content Management",
    "profile_id": _DEFAULT_PROFILE,
    "extension_ids": [
        "ploneorg.core:default",
        "ploneorg.core:initial",
    ],
    "setup_content": False,
    "default_language": "en",
    "portal_timezone": "Europe/Berlin",
}

if SITE_ID in app.objectIds() and DELETE_EXISTING:
    app.manage_delObjects([SITE_ID])
    transaction.commit()
    app._p_jar.sync()

if SITE_ID not in app.objectIds():
    site = addPloneSite(app, SITE_ID, **payload)
    transaction.commit()
    app._p_jar.sync()
else:
    print(f"Site {SITE_ID} already created")
    print("Set DELETE_EXISTING=true to delete it and create a new one")
