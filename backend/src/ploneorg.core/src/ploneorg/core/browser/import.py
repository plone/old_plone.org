from App.config import getConfiguration
from bs4 import BeautifulSoup
from collective.exportimport.fix_html import fix_html_in_content_fields
from collective.exportimport.fix_html import fix_html_in_portlets
from collective.exportimport.import_content import ImportContent
from logging import getLogger
from pathlib import Path
from plone import api
from plone.protect.interfaces import IDisableCSRFProtection
from Products.Five import BrowserView
from Products.ZCatalog.ProgressHandler import ZLogHandler
from zope.annotation.interfaces import IAnnotations
from zope.interface import alsoProvides
from ZPublisher.HTTPRequest import FileUpload

import json
import os
import pycountry
import transaction


logger = getLogger(__name__)

PORTAL_TYPE_MAPPING = {
    # "FormFolder": "EasyForm",
}

ALLOWED_TYPES = [
    "Collection",
    "Document",
    "Event",
    "File",
    "Folder",
    "Image",
    "Link",
    "News Item",
    "FoundationMember",
    "FoundationSponsor",
    "hotfix",
    "plonerelease",
    "vulnerability",
]


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
        catalog = api.portal.get_tool("portal_catalog")
        pghandler = ZLogHandler(1000)
        catalog.reindexIndex("allowedRolesAndUsers", None, pghandler=pghandler)
        logger.info("Finished Reindexing Security")
        transaction.commit()

        name = "ordering"
        view = api.content.get_view(f"import_{name}", portal, request)
        path = Path(directory) / f"export_{name}.json"
        results = view(jsonfile=path.read_text(), return_json=True)
        logger.info(results)
        transaction.commit()

        # name = "defaultpages"
        # view = api.content.get_view(f"import_{name}", portal, request)
        # path = Path(directory) / f"export_{name}.json"
        # results = view(jsonfile=path.read_text(), return_json=True)
        # logger.info(results)
        # transaction.commit()

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

    def global_dict_hook(self, item):
        # TODO: implement the missing types
        if item["@type"] not in ALLOWED_TYPES:
            return

        # fix error_expiration_must_be_after_effective_date
        if item["UID"] == "0cf016d763af4615b3f06587ef5cd9f4":
            item["effective"] = "2019-01-01T00:00:00"

        # Some items may have no title or only spaces but it is a required field
        if not item.get("title") or not item.get("title", "").strip():
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

        if item["@type"] == "vulnerability":
            item["reported_by"] = [i for i in item.get("reported_by", []) or [] if i]

        # update constraints
        if item.get("exportimport.constrains"):
            types_fixed = []
            for portal_type in item["exportimport.constrains"]["locally_allowed_types"]:
                if portal_type in PORTAL_TYPE_MAPPING:
                    types_fixed.append(PORTAL_TYPE_MAPPING[portal_type])
                elif portal_type in ALLOWED_TYPES:
                    types_fixed.append(portal_type)
            item["exportimport.constrains"]["locally_allowed_types"] = list(
                set(types_fixed)
            )

            types_fixed = []
            for portal_type in item["exportimport.constrains"][
                "immediately_addable_types"
            ]:
                if portal_type in PORTAL_TYPE_MAPPING:
                    types_fixed.append(PORTAL_TYPE_MAPPING[portal_type])
                elif portal_type in ALLOWED_TYPES:
                    types_fixed.append(portal_type)
            item["exportimport.constrains"]["immediately_addable_types"] = list(
                set(types_fixed)
            )

        return item

    def dict_hook_plonerelease(self, item):
        # TODO: transfer data to a better format?
        fileinfos = item.get("files", [])
        item["files"] = []
        for fileinfo in fileinfos:
            value = (
                f"{fileinfo['description']} "
                f"({fileinfo['file_size']}, "
                f"{fileinfo['platform']}): {fileinfo['url']}"
            )
            item["files"].append(value)
        return item

    def dict_hook_collection(self, item):
        # Replace Collections with Documents with a listing block
        item["@type"] = "Document"
        # transform query to listing block with the same query
        item["exportimport.collection.query"] = item.pop("query")
        item["exportimport.collection.layout"] = item.pop("layout")
        return item

    def dict_hook_foundationmember(self, item):
        firstname = item.pop("fname", "")
        lastname = item.pop("lname", "")
        item["title"] = f"{firstname} {lastname}".strip()

        # append ploneuse to main text
        ploneuse = item["ploneuse"] and item["ploneuse"]["data"] or ""
        soup = BeautifulSoup(ploneuse, "html.parser")
        text = soup.text.strip()
        if text and "no data (carried over from old site)" not in text:
            merit = item["merit"]["data"]
            ploneuse = item["ploneuse"]["data"]
            item["merit"]["data"] = f"{merit} \r\n {ploneuse}"

        # TODO: Fix workflow
        item["review_state"] = "published"
        return item

    def dict_hook_foundationsponsor(self, item):
        # fix amount to be float
        if item.get("payment_amount"):
            item["payment_amount"] = float(item["payment_amount"])
        else:
            item["payment_amount"] = 0.0

        # fix country to work with vocabulary
        if item.get("country"):
            country = pycountry.countries.get(alpha_3=item["country"]["token"])
            item["country"] = country.alpha_2

        # TODO: Fix workflow
        item["review_state"] = "published"
        return item

    def obj_hook_document(self, obj, item):
        if item.get("exportimport.collection.query"):
            # Store collection query for later transform to listing block
            annotations = IAnnotations(obj)
            annotations["exportimport.collection.query"] = item[
                "exportimport.collection.query"
            ]
            annotations["exportimport.collection.layout"] = item.get(
                "exportimport.collection.layout"
            )


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
            except Exception as e:  # noQA
                status = "error"
                logger.error(e)
                api.portal.show_message(
                    "Failure while uploading: {}".format(e),
                    request=self.request,
                )
            else:
                members = self.import_members(data)
                msg = "Imported {} members".format(members)
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
