from App.config import getConfiguration
from collective.exportimport.fix_html import fix_html_in_content_fields
from collective.exportimport.fix_html import fix_html_in_portlets
from collective.exportimport.import_content import ImportContent
from logging import getLogger
from pathlib import Path
from plone import api
from plone.protect.interfaces import IDisableCSRFProtection
from Products.Five import BrowserView
from Products.ZCatalog.ProgressHandler import ZLogHandler
from uuid import uuid4
from zope.interface import alsoProvides
from ZPublisher.HTTPRequest import FileUpload

import json
import os
import requests
import transaction

logger = getLogger(__name__)


class ImportAll(BrowserView):

    def __call__(self, prepare=True):
        request = self.request
        portal = api.portal.get()
        alsoProvides(request, IDisableCSRFProtection)

        cfg = getConfiguration()
        directory = os.path.join(cfg.clienthome, "import")

        view = api.content.get_view("import_content", portal, request)
        request.form["form.submitted"] = True
        request.form["commit"] = 1000
        view(server_file="ploneorg.json", return_json=True)
        transaction.commit()

        # all other imports
        name = "relations"
        view = api.content.get_view(f"import_{name}", portal, request)
        path = Path(directory) / f"export_{name}.json"
        results = view(jsonfile=path.read_text(), return_json=True)
        logger.info(results)
        transaction.commit()

        name = "members"
        view = api.content.get_view(f"import_{name}", portal, request)
        path = Path(directory) / f"export_{name}.json"
        results = view(jsonfile=path.read_text(), return_json=True)
        logger.info(results)
        transaction.commit()

        name = "localroles"
        view = api.content.get_view(f"import_{name}", portal, request)
        path = Path(directory) / f"export_{name}.json"
        results = view(jsonfile=path.read_text(), return_json=True)
        logger.info(results)
        transaction.commit()

        # reindex
        logger.info("Reindexing Security")
        catalog = api.portal.get_tool('portal_catalog')
        pghandler = ZLogHandler(1000)
        catalog.reindexIndex('allowedRolesAndUsers', None, pghandler=pghandler)
        logger.info("Finished Reindexing Security")
        transaction.commit()

        name = "ordering"
        view = api.content.get_view(f"import_{name}", portal, request)
        path = Path(directory) / f"export_{name}.json"
        results = view(jsonfile=path.read_text(), return_json=True)
        logger.info(results)
        transaction.commit()

        name = "defaultpages"
        view = api.content.get_view(f"import_{name}", portal, request)
        path = Path(directory) / f"export_{name}.json"
        results = view(jsonfile=path.read_text(), return_json=True)
        logger.info(results)
        transaction.commit()

        name = "zope_users"
        view = api.content.get_view(f"import_{name}", portal, request)
        path = Path(directory) / f"export_{name}.json"
        results = view(jsonfile=path.read_text(), return_json=True)
        logger.info(results)
        transaction.commit()

        results = fix_html_in_content_fields()
        msg = "Fixed html for {} content items".format(results)
        logger.info(msg)
        transaction.commit()

        fix_html_in_portlets()
        msg = "Fixed html for portlets"
        logger.info(msg)
        transaction.commit()

        view = api.content.get_view("updateLinkIntegrityInformation", portal, request)
        results = view.update()
        logger.info(f"Updated linkintegrity for {results} items")
        transaction.commit()

        reset_dates = api.content.get_view("reset_dates", portal, request)
        reset_dates()
        transaction.commit()

        return request.response.redirect(portal.absolute_url())


class PloneOrgImportContent(ImportContent):

    DROP_PATHS = []

    DROP_UIDS = []

    IMPORTED_TYPES = [
        "Collection",
        "Document",
        "Event",
        "File",
        "Folder",
        "Image",
        "Link",
        "News Item",
        # "FoundationMember",
        # "FoundationSponsor",
        # "hotfix",
        # "plonerelease",
        # "vulnerability",
    ]

    def global_dict_hook(self, item):
        # TODO: implement the missing types
        if item["@type"] not in self.IMPORTED_TYPES:
            return

        # fix error_expiration_must_be_after_effective_date
        if item["UID"] == "0cf016d763af4615b3f06587ef5cd9f4":
            item["effective"] = "2019-01-01T00:00:00"

        # Some items may have no title or only spaces but it is a required field
        if not item["title"] or not item["title"].strip():
            item["title"] = item["id"]

        lang = item.pop("language", None)
        if lang is not None:
            item["language"] = "en"

        # Missing value in primary field
        if item["@type"] == "Image" and not item["image"]:
            logger.info(f'No image in {item["@id"]}! Skipping...')
            return
        if item["@type"] == "File" and not item["file"]:
            logger.info(f'No file in {item["@id"]}! Skipping...')
            return

        # Empty value in tuple
        if item["@type"] == "Event" and item["attendees"]:
            item["attendees"] = [i for i in item["attendees"] if i]

        # disable mosaic remote view
        if item.get("layout") == "layout_view":
            logger.info(f"Drop mosaic layout from {item['@id']}")
            item.pop("layout")

        # drop empty creator
        item["creators"] = [i for i in item.get("creators", []) if i]

        return item


class ImportZopeUsers(BrowserView):

    def __call__(self, jsonfile=None, return_json=False):
        if jsonfile:
            self.portal = api.portal.get()
            status = "success"
            try:
                if isinstance(jsonfile, str):
                    return_json = True
                    data = json.loads(jsonfile)
                elif isinstance(jsonfile, FileUpload):
                    data = json.loads(jsonfile.read())
                else:
                    raise ("Data is neither text nor upload.")
            except Exception as e:
                status = "error"
                logger.error(e)
                api.portal.show_message(
                    u"Failure while uploading: {}".format(e),
                    request=self.request,
                )
            else:
                members = self.import_members(data)
                msg = u"Imported {} members".format(members)
                api.portal.show_message(msg, self.request)
            if return_json:
                msg = {"state": status, "msg": msg}
                return json.dumps(msg)

        return self.index()

    def import_members(self, data):
        app = self.portal.__parent__
        acl = app.acl_users

        usersNumber = 0
        for item in data:
            username = item["username"]
            password = item.pop("password")
            roles = item.pop("roles", [])
            if not username or not password or not roles:
                continue
            title = item.pop("title", None)
            try:
                acl.users.addUser(username, title, password)
            except KeyError:
                # user exists
                pass
            for role in roles:
                acl.roles.assignRoleToPrincipal(role, username)
            usersNumber += 1
        return usersNumber


class TransformRichTextToSlate(BrowserView):

    service = "http://localhost:5000/html"

    def __call__(self):

        types_with_blocks = [
            "Document",
        ]
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        alsoProvides(self.request, IDisableCSRFProtection)
        for portal_type in types_with_blocks:
            for index, brain in enumerate(api.content.find(portal_type=portal_type), start=1):
                obj = brain.getObject()
                text = getattr(obj.aq_base, "text")
                text = text and text.raw and text.raw.strip()
                if not text:
                    continue
                r = requests.post(self.service, headers=headers, json={"html": text})
                r.raise_for_status()
                slate_data = r.json()
                logger.debug(f"Changed html to slate")
                logger.debug(f"Html: {text}")
                logger.debug(f"Slate: {slate_data}")
                blocks = {}
                uuids = []

                # add title
                uuid = str(uuid4())
                blocks[uuid] = {"@type": "title"}

                # add slate blocks
                for block in slate_data["data"]:
                    uuid = str(uuid4())
                    uuids.append(uuid)
                    blocks[uuid] = block
                obj.blocks = blocks
                obj.blocks_layout = {'items': uuids}
                logger.info(f"Migrated richtext to slate: {obj.absolute_url()}")
                obj.reindexObject(idxs=["SearchableText"])
                if index > 10:
                    return "Done"
