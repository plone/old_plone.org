from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.testing.zope import WSGI_SERVER_FIXTURE

import ploneorg.core


class PLONEORGCORELayer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        self.loadZCML(package=ploneorg.core)

    def setUpPloneSite(self, portal):
        applyProfile(portal, "ploneorg.core:default")
        applyProfile(portal, "ploneorg.core:initial")


PLONEORG_CORE_FIXTURE = PLONEORGCORELayer()


PLONEORG_CORE_INTEGRATION_TESTING = IntegrationTesting(
    bases=(PLONEORG_CORE_FIXTURE,),
    name="PLONEORGCORELayer:IntegrationTesting",
)


PLONEORG_CORE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(PLONEORG_CORE_FIXTURE, WSGI_SERVER_FIXTURE),
    name="PLONEORGCORELayer:FunctionalTesting",
)


PLONEORG_COREACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        PLONEORG_CORE_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        WSGI_SERVER_FIXTURE,
    ),
    name="PLONEORGCORELayer:AcceptanceTesting",
)
