from AccessControl.SecurityManagement import newSecurityManager
from ploneorg.core.interfaces import IPloneOrgCoreLayer
from Products.CMFPlone.factory import _DEFAULT_PROFILE
from Products.CMFPlone.factory import addPloneSite
from Testing.makerequest import makerequest
from zope.interface import directlyProvidedBy
from zope.interface import directlyProvides

import transaction


app = makerequest(app)

request = app.REQUEST

ifaces = [
    IPloneOrgCoreLayer,
] + list(directlyProvidedBy(request))

directlyProvides(request, *ifaces)

admin = app.acl_users.getUserById("admin")
admin = admin.__of__(app.acl_users)
newSecurityManager(None, admin)

site_id = "Plone"
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

if site_id in app.objectIds():
    app.manage_delObjects([site_id])

transaction.commit()

site = addPloneSite(app, site_id, **payload)
transaction.commit()
