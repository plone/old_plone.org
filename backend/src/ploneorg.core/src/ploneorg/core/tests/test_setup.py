"""Setup tests for this package."""
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from ploneorg.core.testing import PLONEORG_CORE_INTEGRATION_TESTING  # noqa: E501
from Products.CMFPlone.utils import get_installer

import unittest


class TestSetup(unittest.TestCase):
    """Test that ploneorg.core is properly installed."""

    layer = PLONEORG_CORE_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer["portal"]
        self.setup = self.portal.portal_setup
        if get_installer:
            self.installer = get_installer(self.portal, self.layer["request"])
        else:
            self.installer = api.portal.get_tool("portal_quickinstaller")

    def test_product_installed(self):
        """Test if ploneorg.core is installed."""
        self.assertTrue(self.installer.isProductInstalled("ploneorg.core"))

    def test_browserlayer(self):
        """Test that IPloneOrgCoreLayer is registered."""
        from plone.browserlayer import utils
        from ploneorg.core.interfaces import IPloneOrgCoreLayer

        self.assertIn(IPloneOrgCoreLayer, utils.registered_layers())

    def test_latest_version(self):
        """Test latest version of default profile."""
        self.assertEqual(
            self.setup.getLastVersionForProfile("ploneorg.core:default")[0],
            "20211204001",
        )


class TestUninstall(unittest.TestCase):

    layer = PLONEORG_CORE_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        if get_installer:
            self.installer = get_installer(self.portal, self.layer["request"])
        else:
            self.installer = api.portal.get_tool("portal_quickinstaller")
        roles_before = api.user.get_roles(TEST_USER_ID)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.installer.uninstallProducts(["ploneorg.core"])
        setRoles(self.portal, TEST_USER_ID, roles_before)

    def test_product_uninstalled(self):
        """Test if ploneorg.core is cleanly uninstalled."""
        self.assertFalse(self.installer.isProductInstalled("ploneorg.core"))

    def test_browserlayer_removed(self):
        """Test that IPloneOrgCoreLayer is removed."""
        from plone.browserlayer import utils
        from ploneorg.core.interfaces import IPloneOrgCoreLayer

        self.assertNotIn(IPloneOrgCoreLayer, utils.registered_layers())
