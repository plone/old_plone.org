from App.config import getConfiguration
from collective.exportimport.fix_html import fix_html_in_content_fields
from collective.exportimport.fix_html import fix_html_in_portlets
from collective.exportimport.import_content import ImportContent
from logging import getLogger
from pathlib import Path
from plone import api
from plone.protect.interfaces import IDisableCSRFProtection
from Products.Five import BrowserView
from zope.interface import alsoProvides
from ZPublisher.HTTPRequest import FileUpload

import os
import json
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
        from Products.ZCatalog.ProgressHandler import ZLogHandler
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

        name = "portlets"
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

    def global_dict_hook(self, item):
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
            acl.users.addUser(username, title, password)
            for role in roles:
                acl.roles.assignRoleToPrincipal(role, username)
            usersNumber += 1
        return usersNumber
