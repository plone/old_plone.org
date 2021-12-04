from plone.dexterity.content import Container
from plone.supermodel import model
from typing import List
from zope.interface import implementer


class IFoundationMember(model.Schema):
    """Plone Foundation Member."""


@implementer(IFoundationMember)
class FoundationMember(Container):
    """Convenience subclass for ``FoundationMember`` portal type."""
