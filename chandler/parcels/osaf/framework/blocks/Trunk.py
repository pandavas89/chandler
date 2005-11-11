__version__ = "$Revision$"
__date__ = "$Date$"
__copyright__ = "Copyright (c) 2005 Open Source Applications Foundation"
__license__ = "http://osafoundation.org/Chandler_0.1_license_terms.htm"
__parcel__ = "osaf.framework.blocks"

import sys
from osaf.framework.blocks import Block
from osaf.framework.blocks import ContainerBlocks
from repository.item.Item import Item
from application import schema
import wx

"""
Trunk.py - Classes for dynamically substituting child trees-of-blocks.

The idea is that you've got a block that wants different sets of child blocks substituted within itself,
based on some key (like a content item to be displayed). The block inherits from this TrunkParentBlock
class; whenever synchronizeWidget happens, the appropriate set of child blocks will be swapped in. This
mechanism is managed by a TrunkDelegate object, which can be subclassed and/or configured from parcel XML
to customize its behavior.
"""

class wxTrunkParentBlock(ContainerBlocks.wxBoxContainer):
    """ 
    A widget block that gives its TrunkParentBlock a chance to change 
    the tree of blocks within it. 
    """
    def wxSynchronizeWidget(self, **hints):
        if self.blockItem.isShown:
            self.blockItem.installTreeOfBlocks()
        super(wxTrunkParentBlock, self).wxSynchronizeWidget()
    
class TrunkParentBlock(ContainerBlocks.BoxContainer):
    """
    A block that can swap in different sets of child blocks ("trunks") based
    on its detailContents. It uses a TrunkDelegate to do the heavy lifting.
    """    
    colorStyle = schema.One('osaf.framework.blocks.Styles.ColorStyle')

    trunkDelegate = schema.One(
        'TrunkDelegate', inverse = 'trunkParentBlocks', required = True
    )
    TPBDetailItem = schema.One(
        schema.Item, initialValue = None, otherName = 'TPBDetailItemOwner'
    )
    TPBSelectedItem = schema.One(
        schema.Item, initialValue = None, otherName = 'TPBSelectedItemOwner'
    )

    schema.addClouds(
        copying = schema.Cloud(
            byRef = [trunkDelegate,colorStyle,TPBDetailItem,TPBSelectedItem]
        )
    )

    def instantiateWidget(self):
       return wxTrunkParentBlock(self.parentBlock.widget)
    
    def onSelectItemsEvent (self, event):
        # for the moment, multiple selection means, "select nothing"
        # i.e. multiple selection in the summary view means selecting
        # nothing in the detail view

        # eventually we might want TPBSelectedItem to be an iterable
        # of some kind
        items = event.arguments['items']
        if len(items)==1:
            self.TPBSelectedItem = items[0]
        else:
            self.TPBSelectedItem = None
        widget = getattr (self, 'widget', None)
        if widget is not None:
            widget.wxSynchronizeWidget ()

    def installTreeOfBlocks(self):
        """
          If necessary, replace our children with a trunk of blocks appropriate for our content
        """
        TPBSelectedItem = getattr(self, 'TPBSelectedItem', None)
        hints = {}
        keyItem = self.trunkDelegate._mapItemToCacheKeyItem(TPBSelectedItem, hints)
        newView = self.trunkDelegate.getTrunkForKeyItem(keyItem)
        if keyItem is None:
            TPBDetailItem = None
        else:
            """
              Seems like we should always mark new views with an event boundary
            """
            assert newView is None or newView.eventBoundary
            TPBDetailItem = self.trunkDelegate._getContentsForTrunk(
                                newView, TPBSelectedItem, keyItem)

        detailItemChanged = getattr(self, 'TPBDetailItem', None) != TPBDetailItem
            
        self.TPBDetailItem = TPBDetailItem
        # For bug 4269 in 0.6: If we've been given a contents collection,
        # it's so that we can put our TPBDetailItem in it, to get a notification
        # when that item is deleted. Update the collection if necessary.
        contents = getattr(self, 'contents', None)
        if (contents is not None and contents.first() is not TPBDetailItem):
            contents.clear()
            if TPBDetailItem is not None:
                contents.add(self.TPBDetailItem)

        oldView = self.childrenBlocks.first()
        treeChanged = newView is not oldView

        if treeChanged:
            if oldView is not None:
                oldView.unRender()

        if treeChanged:
            self.childrenBlocks = []
            if newView is not None:
                self.childrenBlocks.append(newView)

        if newView is not None:
            app = wx.GetApp()
            oldIgnoreSynchronizeWidget = app.ignoreSynchronizeWidget
            app.ignoreSynchronizeWidget = False
            try:
                if (detailItemChanged or
                    treeChanged or
                    hints.get ("sendSetContents", False)):
                    newView.postEventByName ("SetContents", {'item':TPBDetailItem})

                if not hasattr (newView, "widget"):
                    newView.render()
                else:
                    layoutMethod = getattr(newView, 'Layout', None)
                    if layoutMethod is not None: 
                        layoutMethod()
            finally:
                app.ignoreSynchronizeWidget = oldIgnoreSynchronizeWidget


class TrunkDelegate(schema.Item):
    """
    A mechanism to map an item to a view: call its getTrunkForKeyItem(item)
    to get the view for that item.

    The default implementation is suitable when the item the view to be used;
    it'll be returned as-is (except that a copy will be made if the original's
    in the read-only part of the repository).

    Issues:
     - We'd like to use itemrefs as keys, so reference tracking & cleanup
       would work.
    """

    trunkParentBlocks = schema.Sequence(
        TrunkParentBlock,
        inverse = TrunkParentBlock.trunkDelegate,
        required = True,
    )

    keyUUIDToTrunk = schema.Mapping(Block.Block, initialValue = {})

    def deleteCache(self):
        for item in self.keyUUIDToTrunk.itervalues():
            if item is not None:
                item.delete (cloudAlias="copying")
        self.keyUUIDToTrunk = {}

    def getTrunkForKeyItem(self, keyItem):
        """ 
        Given an item, return the view to be used to display it.

        Can be overridden if you don't want the default behavior, which is to 
        cache the views, keyed by a value returned by _mapItemToCacheKeyItem. Misses 
        are handled by _makeTrunkForItem.
        """
        trunk = None
        if not keyItem is None:
            keyUUID = keyItem.itsUUID
            try:
                trunk = self.keyUUIDToTrunk[keyUUID]
            except KeyError:
                trunk = self._makeTrunkForCacheKey(keyItem)
                self.keyUUIDToTrunk[keyUUID] = trunk
        return trunk

    def _mapItemToCacheKeyItem(self, item, hints):
        """ 
        Given an item, determine the item to be used as the cache key.
        Can be overridden; defaults to using the item itself. hints is
        a dictionary that includes domain specific information. See
        the other implementations of _mapItemToCacheKeyItem for more
        information.
        """
        return item

    def _makeTrunkForCacheKey(self, keyItem):
        """ 
        Handle a cache miss; build and return a tree-of-blocks for this keyItem. 
        Defaults to using the keyItem itself, copying it if it's in the read-only
        part of the repository. (This behavior fits with the simple case where
        the items are views.)
        """
        return self._copyItem(keyItem, onlyIfReadOnly=True)

    def _copyItem(self, item, onlyIfReadOnly=False):
        """
        Handy utility: Return a copy of this item using its default cloud.
        If onlyIfReadOnly, we'll return the item as-is if it's already in the
        writeable part of the repository.
        """
        # Look up the soup in the repository once per run.
        try:
            userData = self.userData
        except AttributeError:
            userData = self.findPath('//userdata')
            self.userData = userData

        if onlyIfReadOnly and item.itsParent == userData:
            result = item
        else:
            result = item.copy(parent = userData, cloudAlias="copying")
            
        return result

    def _getContentsForTrunk(self, trunk, item, keyItem):
        """ 
        Given a trunk, item and keyItem, return the contents for the trunk.
        """
        return item

