from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.restapi.testing import RelativeSession
from ploneorg.core.testing import PLONEORG_CORE_FUNCTIONAL_TESTING
from ploneorg.core.testing import PLONEORG_CORE_INTEGRATION_TESTING
from ploneorg.core.tests import create_test_users
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

import transaction
import unittest


class TestCountriesVocabulary(unittest.TestCase):

    layer = PLONEORG_CORE_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]

    def test_vocab(self):
        vocab_util = getUtility(
            IVocabularyFactory, "ploneorg.core.vocabulary.countries"
        )
        topics = vocab_util(self.portal)
        self.assertTrue("BR" in [x for x in topics.by_token])


class TestCountriesVocabularyEndpoint(unittest.TestCase):

    layer = PLONEORG_CORE_FUNCTIONAL_TESTING

    endpoint = "/@vocabularies/ploneorg.core.vocabulary.countries"

    def setUp(self):
        self.app = self.layer["app"]
        self.portal = self.layer["portal"]
        self.portal_url = self.portal.absolute_url()
        self.api_session = RelativeSession(self.portal_url)
        self.api_session.headers.update({"Accept": "application/json"})
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.users = create_test_users()
        transaction.commit()

    def test_get_vocabulary_as_manager(self):
        self.api_session.auth = (SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
        response = self.api_session.get(self.endpoint)
        self.assertEqual(200, response.status_code)
        data = response.json()
        first = data["items"][0]
        self.assertEqual(first["token"], "AW")
        self.assertEqual(first["title"], "Aruba")

    def test_get_vocabulary_as_editor(self):
        self.api_session.auth = self.users["editor"]
        response = self.api_session.get(self.endpoint)
        self.assertEqual(200, response.status_code)
        data = response.json()
        first = data["items"][0]
        self.assertEqual(first["token"], "AW")
        self.assertEqual(first["title"], "Aruba")

    def test_get_vocabulary_as_member(self):
        self.api_session.auth = self.users["member"]
        response = self.api_session.get(self.endpoint)
        self.assertEqual(200, response.status_code)
        data = response.json()
        first = data["items"][0]
        self.assertEqual(first["token"], "AW")
        self.assertEqual(first["title"], "Aruba")
