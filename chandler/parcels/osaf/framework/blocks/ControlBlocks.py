__version__ = "$Revision$"
__date__ = "$Date$"
__copyright__ = "Copyright (c) 2003-2005 Open Source Applications Foundation"
__license__ = "http://osafoundation.org/Chandler_0.1_license_terms.htm"
__parcel__ = "osaf.framework.blocks"

import os, sys
from application.Application import mixinAClass
from application import schema
from Block import ( 
    Block, RectangularChild, BlockEvent, 
    ShownSynchronizer, lineStyleEnumType, logger, debugName
)
from ContainerBlocks import BoxContainer
from osaf.pim import AbstractCollection
import DragAndDrop
import PimBlocks
from chandlerdb.item.ItemError import NoSuchAttributeError
import wx
import wx.html
import wx.gizmos
import wx.grid
import webbrowser # for opening external links
import PyICU

from osaf.framework.blocks import DrawingUtilities
import application.dialogs.RecurrenceDialog as RecurrenceDialog
import application.dialogs.ReminderDialog as ReminderDialog
import Styles
from datetime import datetime, time, timedelta
from osaf.pim.calendar import Calendar
from osaf.pim import Reminder
from repository.item.Monitors import Monitors
from i18n import OSAFMessageFactory as _


class textAlignmentEnumType(schema.Enumeration):
    values = "Left", "Center", "Right"

class buttonKindEnumType(schema.Enumeration):
     values = "Text", "Image", "Toggle"

class Button(RectangularChild):

    characterStyle = schema.One(Styles.CharacterStyle)
    title = schema.One(schema.Text)
    buttonKind = schema.One(buttonKindEnumType)
    icon = schema.One(schema.Text)
    rightClicked = schema.One(BlockEvent)
    event = schema.One(BlockEvent)

    def instantiateWidget(self):
        id = self.getWidgetID(self)
        parentWidget = self.parentBlock.widget
        if self.buttonKind == "Text":
            button = wx.Button (parentWidget,
                                id,
                                self.title,
                                wx.DefaultPosition,
                                (self.minimumSize.width, self.minimumSize.height))
        elif self.buttonKind == "Image":
            bitmap = wx.GetApp().GetImage (self.icon)
            button = wx.BitmapButton (parentWidget,
                                      id,
                                      bitmap,
                                      wx.DefaultPosition,
                                      (self.minimumSize.width, self.minimumSize.height))
        elif self.buttonKind == "Toggle":
                button = wx.ToggleButton (parentWidget, 
                                          id, 
                                          self.title,
                                          wx.DefaultPosition,
                                          (self.minimumSize.width, self.minimumSize.height))
        elif __debug__:
            assert False, "unknown buttonKind"

        parentWidget.Bind(wx.EVT_BUTTON, self.buttonPressed, id=id)
        return button

    def buttonPressed(self, event):
        try:
            event = self.event
        except AttributeError:
            pass
        else:
            self.post(event, {'item':self})


class wxCheckBox(ShownSynchronizer, wx.CheckBox):
    pass

class CheckBox(RectangularChild):

    event = schema.One(BlockEvent)
    title = schema.One(schema.Text)
    schema.addClouds(
        copying = schema.Cloud(byCloud=[event])
    )

    def instantiateWidget(self):
        try:
            id = Block.getWidgetID(self)
        except AttributeError:
            id = 0

        parentWidget = self.parentBlock.widget
        checkbox = wxCheckBox (parentWidget,
                          id,
                          self.title,
                          wx.DefaultPosition,
                          (self.minimumSize.width, self.minimumSize.height))
        checkbox.Bind(wx.EVT_CHECKBOX, wx.GetApp().OnCommand, id=id)
        return checkbox
    
class wxChoice(ShownSynchronizer, wx.Choice):
    pass

class Choice(RectangularChild):

    characterStyle = schema.One(Styles.CharacterStyle)
    event = schema.One(BlockEvent)
    choices = schema.Sequence(schema.Text)
    schema.addClouds(
        copying = schema.Cloud(byCloud=[characterStyle])
    )

    def instantiateWidget(self):
        try:
            id = Block.getWidgetID(self)
        except AttributeError:
            id = 0

        parentWidget = self.parentBlock.widget
        choice = wxChoice (parentWidget,
                         id, 
                         wx.DefaultPosition,
                         (self.minimumSize.width, self.minimumSize.height),
                         self.choices)
        choice.Bind(wx.EVT_CHOICE, wx.GetApp().OnCommand, id=id)
        
        try:
            charStyle = self.characterStyle
        except AttributeError:
            charStyle = None
        choice.SetFont(Styles.getFont(charStyle))
        
        return choice

class ComboBox(RectangularChild):

    selection = schema.One(schema.Text)
    choices = schema.Sequence(schema.Text)
    itemSelected = schema.One(BlockEvent)

    def instantiateWidget(self):
        return wx.ComboBox (self.parentBlock.widget,
                            -1,
                            self.selection, 
                            wx.DefaultPosition,
                            (self.minimumSize.width, self.minimumSize.height),
                            self.choices)

    
class ContextMenu(RectangularChild):
    def displayContextMenu(self, parentWindow, position, data):
        menu = wx.Menu()
        for child in self.childrenBlocks:
            child.addItem(menu, data)
        parentWindow.PopupMenu(menu, position)
        menu.Destroy()
        

class ContextMenuItem(RectangularChild):

    event = schema.One(BlockEvent)
    title = schema.One(schema.Text)
    schema.addClouds(
        copying = schema.Cloud(byCloud=[event])
    )

    def addItem(self, wxContextMenu, data):
        id = Block.getWidgetID(self)
        self.data = data
        wxContextMenu.Append(id, self.title)
        wxContextMenu.Bind(wx.EVT_MENU, wx.GetApp().OnCommand, id=id)


class textStyleEnumType(schema.Enumeration):
      values = "PlainText", "RichText"


class EditText(RectangularChild):

    characterStyle = schema.One(Styles.CharacterStyle)
    lineStyleEnum = schema.One(lineStyleEnumType)
    textStyleEnum = schema.One(textStyleEnumType, initialValue = 'PlainText')
    readOnly = schema.One(schema.Boolean, initialValue = False)
    textAlignmentEnum = schema.One(
        textAlignmentEnumType, initialValue = 'Left',
    )
    schema.addClouds(
        copying = schema.Cloud(byRef=[characterStyle])
    )

    def instantiateWidget(self):
        # Remove STATIC_BORDER: it wrecks padding on WinXP; was: style = wx.STATIC_BORDER
        style = 0
        if self.textAlignmentEnum == "Left":
            style |= wx.TE_LEFT
        elif self.textAlignmentEnum == "Center":
            style |= wx.TE_CENTRE
        elif self.textAlignmentEnum == "Right":
            style |= wx.TE_RIGHT

        if self.lineStyleEnum == "MultiLine":
            style |= wx.TE_MULTILINE
        else:
            style |= wx.TE_PROCESS_ENTER

        if self.textStyleEnum == "RichText":
            style |= wx.TE_RICH2

        if self.readOnly:
            style |= wx.TE_READONLY

        editText = AttributeEditors.wxEditText (self.parentBlock.widget,
                               -1,
                               "",
                               wx.DefaultPosition,
                               (self.minimumSize.width, self.minimumSize.height),
                               style=style, name=self.itsUUID.str64())

        editText.SetFont(Styles.getFont(getattr(self, "characterStyle", None)))
        return editText
    
class wxHTML(wx.html.HtmlWindow):
    def OnLinkClicked(self, link):
        webbrowser.open(link.GetHref())


class HTML(RectangularChild):
    url = schema.One(schema.Bytes)

    def instantiateWidget (self):
        htmlWindow = wxHTML (self.parentBlock.widget,
                             Block.getWidgetID(self),
                             wx.DefaultPosition,
                             (self.minimumSize.width, self.minimumSize.height))
        if self.url:
            htmlWindow.LoadPage(self.url)
        return htmlWindow

 
class ListDelegate (object):
    """
      Default delegate for Lists that use the block's contents. Override
    to customize your behavior. You must implement GetElementValue.
    """
    def GetColumnCount (self):
        return len (self.blockItem.columnHeadings)

    def GetElementCount (self):
        return len (self.blockItem.contents)

    def GetElementType (self, row, column):
        return "Text"

    def GetColumnHeading (self, column, item):
        return self.blockItem.columnHeadings [column]

    def ReadOnly (self, row, column):
        """
          Second argument should be True if all cells have the first value
        """
        return False, True


class AttributeDelegate (ListDelegate):
    def GetElementType (self, row, column):
        """
          An apparent bug in wxWidgets occurs when there are no items in a table,
        the Table asks for the type of cell 0,0
        """
        typeName = "_default"
        try:
            item = self.blockItem.contents [row]
        except IndexError:
            pass
        else:
            attributeName = self.blockItem.columnData [column]
            if item.itsKind.hasAttribute (attributeName):
                try:
                    typeName = item.getAttributeAspect (attributeName, 'type').itsName
                except NoSuchAttributeError:
                    # We special-case the non-Chandler attributes we want to use (_after_ trying the
                    # Chandler attribute, to avoid a hit on Chandler-attribute performance). If we
                    # want to add other itsKind-like non-Chandler attributes, we'd add more tests here.
                    raise
            elif attributeName == 'itsKind':
                typeName = 'Kind'
            else:
                try:
                    # to support properties, we get the value, and use its type's name.
                    value = getattr (item, attributeName)
                except AttributeError:
                    pass
                else:
                    typeName = type (value).__name__
        return typeName

    def GetElementValue (self, row, column):
        return self.blockItem.contents [row], self.blockItem.columnData [column]
    
    def SetElementValue (self, row, column, value):
        item = self.blockItem.contents [row]
        attributeName = self.blockItem.columnData [column]
        assert item.itsKind.hasAttribute (attributeName), "You cannot set a non-Chandler attribute value of an item (like itsKind)"
        item.setAttributeValue (attributeName, value)

    def GetColumnHeading (self, column, item):
        attributeName = self.blockItem.columnData [column]
        if item is not None:
            try:
                attribute = item.itsKind.getAttribute (attributeName)
            except NoSuchAttributeError:
                # We don't need to redirect non-Chandler attributes (eg, itsKind).
                heading = self.blockItem.columnHeadings[column]
            else:
                heading = attribute.getItemDisplayName()
                redirect = item.getAttributeAspect(attributeName, 'redirectTo')
                if redirect is not None:
                    names = redirect.split('.')
                    for name in names [:-1]:
                        item = item.getAttributeValue (name)
                    actual = item.itsKind.getAttribute (names[-1]).getItemDisplayName()
                    heading = u"%s (%s)" % (heading, actual)
                self.blockItem.columnHeadings [column] = heading
        else:
            heading = self.blockItem.columnHeadings [column]
        return heading
    

class wxList (DragAndDrop.DraggableWidget, 
              DragAndDrop.ItemClipboardHandler,
              wx.ListCtrl):
    def __init__(self, *arguments, **keywords):
        super (wxList, self).__init__ (*arguments, **keywords)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnWXSelectItem, id=self.GetId())
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.OnItemDrag)

    def OnInit (self):
        elementDelegate = self.blockItem.elementDelegate
        if not elementDelegate:
            elementDelegate = 'osaf.framework.blocks.ControlBlocks.ListDelegate'
        mixinAClass (self, elementDelegate)
        
    def OnSize(self, event):
        if not wx.GetApp().ignoreSynchronizeWidget:
            size = self.GetClientSize()
            widthMinusLastColumn = 0
            assert self.GetColumnCount() > 0, "We're assuming that there is at least one column"
            for column in xrange (self.GetColumnCount() - 1):
                widthMinusLastColumn += self.GetColumnWidth (column)
            lastColumnWidth = size.width - widthMinusLastColumn
            if lastColumnWidth > 0:
                self.SetColumnWidth (self.GetColumnCount() - 1, lastColumnWidth)
        event.Skip()

    def OnWXSelectItem(self, event):
        if not wx.GetApp().ignoreSynchronizeWidget:
            item = self.blockItem.contents [event.GetIndex()]
            if self.blockItem.selection != item:
                self.blockItem.selection = item
            self.blockItem.postEventByName("SelectItemsBroadcast", {'items':[item]})
        event.Skip()

    def OnItemDrag(self, event):
        self.DoDragAndDrop()

    def SelectedItems(self):
        """
        Return the list of items currently selected.
        """
        curIndex = -1
        itemList = []
        while True:
            curIndex = self.GetNextItem(curIndex, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            itemList.append(self.blockItem.contents [curIndex])
            if curIndex is -1:
                break
        return itemList

    def wxSynchronizeWidget(self, **hints):
        self.Freeze()
        self.ClearAll()
        self.SetItemCount (self.GetElementCount())
        for columnIndex in xrange (self.GetColumnCount()):
            self.InsertColumn (columnIndex,
                               self.GetColumnHeading (columnIndex, self.blockItem.selection),
                               width = self.blockItem.columnWidths [columnIndex])

        self.Thaw()

        if self.blockItem.selection:
            self.GoToItem (self.blockItem.selection)

    def OnGetItemText (self, row, column):
        """
          OnGetItemText won't be called if it's in the delegate -- WxPython won't
        call it if it's in a base class
        """
        return self.GetElementValue (row, column)

    def OnGetItemImage (self, item):
        return -1
    
    def GoToItem(self, item):
        self.Select (self.blockItem.contents.index (item))


class List(RectangularChild):

    columnHeadings = schema.Sequence(schema.Text, required = True)
    columnData = schema.Sequence(schema.Text)
    columnWidths = schema.Sequence(schema.Integer, required = True)
    elementDelegate = schema.One(schema.Bytes, initialValue = '')
    selection = schema.One(schema.Item, initialValue = None)
    schema.addClouds(
        copying = schema.Cloud(byRef=[selection])
    )

    def __init__(self, *arguments, **keywords):
        super (List, self).__init__ (*arguments, **keywords)
        self.selection = None

    def instantiateWidget (self):
        return wxList (self.parentBlock.widget,
                       Block.getWidgetID(self),
                       style=wx.LC_REPORT|wx.LC_VIRTUAL|wx.SUNKEN_BORDER|wx.LC_EDIT_LABELS)

    def onSelectItemsEvent (self, event):
        """
          Display the item in the widget.
        """
        items = event.arguments['items']
        if len(items) == 1:
            self.selection = items[0]
        else:
            self.selection = None
        
        self.widget.GoToItem (self.selection)


class wxTableData(wx.grid.PyGridTableBase):
    def __init__(self, *arguments, **keywords):
        super (wxTableData, self).__init__ (*arguments, **keywords)
        self.defaultRWAttribute = wx.grid.GridCellAttr()
        self.defaultROAttribute = wx.grid.GridCellAttr()
        self.defaultROAttribute.SetReadOnly (True)

    def __del__ (self):
        self.defaultRWAttribute.DecRef()
        self.defaultROAttribute.DecRef()
        
    def GetNumberRows (self):
        """
          We've got the usual chicken & egg problems: wxWidgets calls GetNumberRows &
        GetNumberCols before wiring up the view instance variable
        """
        view = self.GetView()
        if view is not None:
            return view.GetElementCount()
        return 1

    def GetNumberCols (self):
        view = self.GetView()
        if view is not None:
            return view.GetColumnCount()
        return 1

    def GetColLabelValue (self, column):
        grid = self.GetView()
        elements = grid.GetElementCount()
        cursorRow = grid.GetGridCursorRow()
        if elements and elements > cursorRow:
            item = grid.blockItem.contents [cursorRow]
        else:
            item = None
        return grid.GetColumnHeading (column, item)

    def IsEmptyCell (self, row, column): 
        return False 

    def GetValue (self, row, column): 
        return self.GetView().GetElementValue (row, column)

    def SetValue (self, row, column, value):
        self.GetView().SetElementValue (row, column, value) 

    def GetTypeName (self, row, column):
        return self.GetView().GetElementType (row, column)

    def GetAttr (self, row, column, kind):
        attribute = self.base_GetAttr (row, column, kind)
        if attribute is None:
            type = self.GetTypeName (row, column)
            delegate = AttributeEditors.getSingleton (type)
            attribute = self.defaultROAttribute
            """
              An apparent bug in table asks for an attribute even when
            there are no entries in the table
            """
            grid = self.GetView()
            if ((row < grid.GetElementCount()) and
                not grid.blockItem.columnReadOnly[column] and
                not grid.ReadOnly (row, column)[0] and
                not delegate.ReadOnly (grid.GetElementValue (row, column))):
                attribute = self.defaultRWAttribute
            attribute.IncRef()
        return attribute
        

class wxTable(DragAndDrop.DraggableWidget, 
              DragAndDrop.DropReceiveWidget, 
              DragAndDrop.ItemClipboardHandler,
              wx.grid.Grid):
    def __init__(self, parent, widgetID, characterStyle, headerCharacterStyle, *arguments, **keywords):
        if '__WXMAC__' in wx.PlatformInfo:
            theStyle=wx.BORDER_SIMPLE
        else:
            theStyle=wx.BORDER_STATIC
        """
          Giant hack. Calling event.GetEventObject in OnShow of application, while the
        object is being created cause the object to get the wrong type because of a
        "feature" of SWIG. So we need to avoid OnShows in this case.
        """
        app = wx.GetApp()
        oldIgnoreSynchronizeWidget = app.ignoreSynchronizeWidget
        app.ignoreSynchronizeWidget = True
        try:
            super (wxTable, self).__init__ (parent, widgetID, style=theStyle, *arguments, **keywords)
        finally:
            app.ignoreSynchronizeWidget = oldIgnoreSynchronizeWidget

        self.SetDefaultCellFont(Styles.getFont(characterStyle))
        self.SetLabelFont(Styles.getFont(headerCharacterStyle))
        self.SetColLabelAlignment(wx.ALIGN_LEFT, wx.ALIGN_CENTRE)
        self.SetRowLabelSize(0)
        self.AutoSizeRows()
        self.EnableDragCell(True)
        self.DisableDragRowSize()
        self.SetDefaultCellBackgroundColour(wx.WHITE)
        """
          Big fat hack. Since the grid is a scrolled window we set a border equal to the size
        of the scrollbar so the scroll bars won't show. Instead we should consider modifying
        grid adding a new style for not showing scrollbars.  Bug #2375
        """
        self.SetMargins(-wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X),
                        -wx.SystemSettings_GetMetric(wx.SYS_HSCROLL_Y))
        self.EnableCursor (False)
        background = wx.SystemSettings.GetColour (wx.SYS_COLOUR_HIGHLIGHT)
        self.SetLightSelectionBackground()

        self.Bind(wx.EVT_KILL_FOCUS, self.OnLoseFocus)
        self.Bind(wx.EVT_SET_FOCUS, self.OnGainFocus)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.grid.EVT_GRID_CELL_BEGIN_DRAG, self.OnItemDrag)
        self.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnRightClick)
        self.Bind(wx.grid.EVT_GRID_COL_SIZE, self.OnColumnDrag)
        self.Bind(wx.grid.EVT_GRID_RANGE_SELECT, self.OnRangeSelect)

    def OnGainFocus (self, event):
        self.SetSelectionBackground (wx.SystemSettings.GetColour (wx.SYS_COLOUR_HIGHLIGHT))
        self.InvalidateSelection ()

    def OnLoseFocus (self, event):
        self.SetLightSelectionBackground()
        self.InvalidateSelection ()

    def SetLightSelectionBackground (self):
        background = wx.SystemSettings.GetColour (wx.SYS_COLOUR_HIGHLIGHT)
        background.Set ((background.Red() + 255) / 2,
                        (background.Green() + 255) / 2,
                         (background.Blue() + 255) / 2)
        self.SetSelectionBackground (background)

    def InvalidateSelection (self):
        for range in self.blockItem.selection:
            dirtyRect = wx.Rect()
            dirtyRect.SetTopLeft (self.CellToRect (range[0], 0).GetTopLeft())
            dirtyRect.SetBottomRight (self.CellToRect (range[1], self.GetNumberCols() - 1).GetBottomRight())
            dirtyRect.OffsetXY (self.GetRowLabelSize(), self.GetColLabelSize())
            self.RefreshRect (dirtyRect)

    def OnInit (self):
        elementDelegate = self.blockItem.elementDelegate
        if not elementDelegate:
            elementDelegate = 'osaf.framework.blocks.ControlBlocks.AttributeDelegate'
        mixinAClass (self, elementDelegate)
        """
          wxTableData handles the callbacks to display the elements of the
        table. Setting the second argument to True cause the table to be deleted
        when the grid is deleted.

          We've also got the usual chicken and egg problem: SetTable uses the
        table before initializing it's view so GetView() returns none.
        """
        gridTable = wxTableData()

        self.currentRows = gridTable.GetNumberRows()
        self.currentColumns = gridTable.GetNumberCols()
        self.EnableGridLines (self.blockItem.hasGridLines)
        self.SetTable (gridTable, True, selmode=wx.grid.Grid.SelectRows)

    def OnRangeSelect(self, event):
        if not wx.GetApp().ignoreSynchronizeWidget:
            blockItem = self.blockItem
            # Itnore notifications that arrise as a side effect of changes to the selection
            blockItem.stopNotificationDirt()
            try:
                topLeftList = self.GetSelectionBlockTopLeft()
                blockItem.selection = []
                for topLeft, bottomRight in zip (topLeftList,
                                                 self.GetSelectionBlockBottomRight()):
                    blockItem.selection.append ([topLeft[0], bottomRight[0]])
               
                topLeftList.sort()
                try:
                    (row, column) = topLeftList [0]
                except IndexError:
                    item = None
                else:
                    item = blockItem.contents [row]
    
                if item is not blockItem.selectedItemToView:
                    blockItem.selectedItemToView = item
                    if item is not None:
                        gridTable = self.GetTable()
                        for columnIndex in xrange (gridTable.GetNumberCols()):
                            self.SetColLabelValue (columnIndex, gridTable.GetColLabelValue (columnIndex))
                    """
                      So happens that under some circumstances widgets
                      needs to clear the selection before setting a new
                      selection, e.g. when you have some rows in a table
                      selected and you click on another cell. However, we
                      need to catch changes to the selection in
                      OnRangeSelect to keep track of the selection and
                      broadcast selection changes to other blocks. So
                      under some circumstances you get two OnRangeSelect
                      calls, one to clear the selection and another to set
                      the new selection. When the first OnRangeSelect is
                      called to clear the selection we used to broadcast a
                      select item event with None as the selection. This
                      has two unfortunate side effects: it causes other
                      views (e.g. the detail view) to draw blank and it
                      causes the subsequent call to OnRangeSelect to not
                      occur, causing the selection to vanish.  It turns
                      out that ignoring all the clear selections except
                      when control is down skips the extra clear
                      selections.
                    """
                    if (item is not None or event.Selecting() or event.ControlDown()):
                        blockItem.postEventByName("SelectItemsBroadcast",
                                                  {'items':[item]})
            finally:
                blockItem.startNotificationDirt()

        event.Skip()

    def OnSize(self, event):
        if not wx.GetApp().ignoreSynchronizeWidget:
            size = event.GetSize()
            widthMinusLastColumn = 0

            assert self.GetNumberCols() > 0, "We're assuming that there is at least one column"
            lastColumnIndex = self.GetNumberCols() - 1
            for column in xrange (lastColumnIndex):
                widthMinusLastColumn += self.GetColSize (column)
            lastColumnWidth = size.width - widthMinusLastColumn
            """
              This is a temporary fix to get around an apparent bug in grids.  We only want to adjust
            for scrollbars if they are present.  The -2 is a hack, without which the sidebar will grow
            indefinitely when resizing the window.
            """
            if (self.GetSize() == self.GetVirtualSize()):
                lastColumnWidth = lastColumnWidth - 2
            else:
                lastColumnWidth = lastColumnWidth - wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
            if lastColumnWidth > 0:
                self.SetColSize (lastColumnIndex, lastColumnWidth)
                self.ForceRefresh()
        event.Skip()

    def OnColumnDrag(self, event):
        if not wx.GetApp().ignoreSynchronizeWidget:
            columnIndex = event.GetRowOrCol()
            self.blockItem.columnWidths [columnIndex] = self.GetColSize (columnIndex)

    def OnItemDrag(self, event):

        # To fix bug 2159, tell the grid to release the mouse now because the
        # grid object may get destroyed before it has a chance to later on:
        gridWindow = self.GetGridWindow()
        if gridWindow.HasCapture():
            gridWindow.ReleaseMouse()

        # make sure SelectedItemToView is up-to-date (shouldn't need to do this!)
        if not self.blockItem.selection:
            firstRow = event.GetRow()
            self.blockItem.selection = [[firstRow, firstRow]]
        self.DoDragAndDrop(copyOnly=True)

    def AddItems(self, itemList):
        
        collection = self.blockItem.GetCurrentContents(writable=True)
        assert collection, "Can't add items to readonly collection - should block before the drop"
        
        for item in itemList:
            item.addToCollection(collection)

    def OnRightClick(self, event):
        self.blockItem.DisplayContextMenu(event.GetPosition(),
                                          self.blockItem.contents [event.GetRow()])

    def wxSynchronizeWidget(self, **hints):
        """
          A Grid can't easily redisplay its contents, so we write the following
        helper function to readjust everything after the contents change
        """
        #Trim/extend the control's rows and update all values

        if self.blockItem.hideColumnHeadings:
            self.SetColLabelSize (0)
        else:
            self.SetColLabelSize (wx.grid.GRID_DEFAULT_COL_LABEL_HEIGHT)

        gridTable = self.GetTable()
        newRows = gridTable.GetNumberRows()
        newColumns = gridTable.GetNumberCols()

        # update the widget to reflect the new or removed rows or
        # columns. Note that we're only telling the grid HOW MANY rows
        # or columns to add/remove - the per-cell callbacks will
        # determine what actual text to display in each cell
        self.BeginBatch()
        for current, new, deleteMessage, addMessage in [
            (self.currentRows, newRows, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED), 
            (self.currentColumns, newColumns, wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED, wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED)]: 
                if new < current: 
                    message = wx.grid.GridTableMessage (gridTable, deleteMessage, new, current-new) 
                    self.ProcessTableMessage (message) 
                elif new > current: 
                    message = wx.grid.GridTableMessage (gridTable, addMessage, new-current) 
                    self.ProcessTableMessage (message) 
        self.currentRows = newRows
        self.currentColumns = newColumns
        # update all column widths but the last one
        widthMinusLastColumn = 0
        for columnIndex in xrange (newColumns - 1):
            widthMinusLastColumn += self.blockItem.columnWidths[columnIndex]
            self.SetColSize (columnIndex, self.blockItem.columnWidths [columnIndex])

        # update the last column to fill the rest of the widget
        remaining = self.GetSize().width - widthMinusLastColumn
        # Adjust for scrollbar if it is present
        if (self.GetSize() != self.GetVirtualSize()):
            remaining = remaining - wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
        if remaining > 0:
            self.SetColSize(newColumns - 1, remaining)
        
        self.ClearSelection()
        firstSelectedRow = None

        # now update the ranges to reflect the new selection (this
        # should probably be done before the GridTableMessage that
        # removes rows, above (but for 0.6, this is the less risky place)
        if len (self.blockItem.contents) > 0:
            invalidRanges = []
            for range in self.blockItem.selection:
                if range[0] < self.currentRows:
                    if firstSelectedRow is None:
                        firstSelectedRow = range[0]
                        self.SetGridCursor (firstSelectedRow, 0)
                    self.SelectBlock (range[0], 0, range[1], newColumns, True)
                else:
                    invalidRanges.append(range)
                    
            for badRange in invalidRanges:
                self.blockItem.selection.remove(badRange)
        else:
            self.blockItem.selection = []
        self.EndBatch() 

        #Update all displayed values
        message = wx.grid.GridTableMessage (gridTable, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES) 
        self.ProcessTableMessage (message) 
        self.ForceRefresh () 

        if (self.blockItem.selectedItemToView not in self.blockItem.contents and
            firstSelectedRow is not None):
            selectedItemToView = self.blockItem.contents [firstSelectedRow]
            self.blockItem.selectedItemToView = selectedItemToView
            self.blockItem.postEventByName("SelectItemsBroadcast",
                                           {'items':[selectedItemToView]})

        try:
            row = self.blockItem.contents.index (self.blockItem.selectedItemToView)
        except ValueError:
            pass
        else:
            self.MakeCellVisible (row, 0)

    def GoToItem(self, item):
        if item != None:
            try:
                row = self.blockItem.contents.index (item)
            except ValueError:
                item = None
        if item is not None:
            self.blockItem.selection.append ([row, row])
            self.blockItem.selectedItemToView = item
            self.SelectBlock (row, 0, row, self.GetColumnCount() - 1)
            self.MakeCellVisible (row, 0)
        else:
            self.blockItem.selection = []
            self.blockItem.selectedItemToView = None
            self.ClearSelection()
        self.blockItem.postEventByName("SelectItemsBroadcast",
                                       {'items':[item]})

    def DeleteSelection (self, DeleteItemCallback=None):
        def DefaultCallback(item, collection=self.blockItem.contents):
            collection.remove(item)
            
        blockItem = self.blockItem
        if DeleteItemCallback is None:
            DeleteItemCallback = DefaultCallback
        topLeftList = self.GetSelectionBlockTopLeft()
        bottomRightList = self.GetSelectionBlockBottomRight()
        """
          Clear the selection before removing the elements from the collection
        otherwise our delegate will get called asking for deleted items
        """
        self.ClearSelection()
        
        # build up a list of selection ranges [[tl1, br1], [tl2, br2]]
        selectionRanges = []
        for topLeft in topLeftList:
            bottomRight = bottomRightList.pop (0)
            selectionRanges.append ([topLeft[0], bottomRight[0]])
        selectionRanges.sort()
        selectionRanges.reverse()

        # now delete rows - since we reverse sorted, the 
        # "newRowSelection" will be the highest row that we're not deleting
        
        # this is broken - we shouldn't be going through the widget
        # to delete the items! Instead, when items are removed from the
        # current collection, the widget should be notified to remove
        # the corresponding rows.
        # (that probably can't be fixed until ItemCollection
        # becomes Collection and notifications work again)
        newRowSelection = 0
        contents = blockItem.contents
        for range in selectionRanges:
            for row in xrange (range[1], range [0] - 1, -1):
                DeleteItemCallback(contents[row])
                newRowSelection = row

        blockItem.selection = []
        blockItem.selectedItemToView = None
        blockItem.itsView.commit()
        
        # now select the "next" item
        totalItems = len(contents)
        """
          We call wxSynchronizeWidget here because the postEvent
          causes the DetailView to call it's wxSynchrnoizeWidget,
          which calls layout, which causes us to redraw the table,
          which hasn't had time to get it's notificaitons so its data
          is out of synch and chandler Crashes. So I think the long
          term fix is to not call wxSynchronizeWidget here or in the
          DetailView and instead let the notifications cause
          wxSynchronizeWidget to be called. -- DJA
        """
        blockItem.synchronizeWidget()
        if totalItems > 0:
            newRowSelection = min(newRowSelection, totalItems - 1)
            blockItem.postEventByName("SelectItemsBroadcast",
                                      {'items':[contents[newRowSelection]]})
        else:
            blockItem.postEventByName("SelectItemsBroadcast",
                                      {'items': []})

    def SelectedItems(self):
        """
        Return the list of selected items.
        """
        selectionRanges = self.blockItem.selection
        if not selectionRanges:
            detailItem = self.blockItem.selectedItemToView
            if detailItem is None:
                return []
            else:
                return [detailItem]
        itemList = []
        for selectionRange in selectionRanges:
            for index in xrange(selectionRange[0], selectionRange[1]+1):
                itemList.append(self.blockItem.contents [index])
        return itemList

class GridCellAttributeRenderer (wx.grid.PyGridCellRenderer):
    def __init__(self, type):
        super (GridCellAttributeRenderer, self).__init__ ()
        self.delegate = AttributeEditors.getSingleton (type)

    def Draw (self, grid, attr, dc, rect, row, column, isInSelection):
        """
          Currently only handles left justified multiline text
        """
        DrawingUtilities.SetTextColorsAndFont (grid, attr, dc, isInSelection)
        item, attributeName = grid.GetElementValue (row, column)
        assert not item.isDeleted()
        item = RecurrenceDialog.getProxy(u'ui', item, createNew=False)
        self.delegate.Draw (dc, rect, item, attributeName, isInSelection)

class GridCellAttributeEditor (wx.grid.PyGridCellEditor):
    def __init__(self, type):
        super (GridCellAttributeEditor, self).__init__ ()
        self.delegate = AttributeEditors.getSingleton (type)

    def Create (self, parent, id, evtHandler):
        """
          Create an edit control to edit the text
        """
        self.control = self.delegate.CreateControl(True, False, parent, id, None, None)
        self.SetControl (self.control)
        if evtHandler:
            self.control.PushEventHandler (evtHandler)

    def PaintBackground (self, *arguments, **keywords):
        """
          background drawing is done by the edit control
        """
        pass

    def BeginEdit (self, row,  column, grid):
        assert getattr(self, 'editingCell', None) is None
        self.editingCell = (row, column)
        
        item, attributeName = grid.GetElementValue (row, column)
        assert not item.isDeleted()
        item = RecurrenceDialog.getProxy(u'ui', item)
        
        self.initialValue = self.delegate.GetAttributeValue (item, attributeName)
        self.delegate.BeginControlEdit (item, attributeName, self.control)
        self.control.SetFocus()
        self.control.SelectAll()

    def EndEdit (self, row, column, grid):
        assert self.editingCell == (row, column)
        self.editingCell = None

        value = self.delegate.GetControlValue (self.control)
        item, attributeName = grid.GetElementValue (row, column)
        assert not item.isDeleted()
        item = RecurrenceDialog.getProxy(u'ui', item)

        if value == self.initialValue:
            changed = False
        # @@@ For now we do not want to allow users to blank out fields.  This should eventually be
        #  replaced by proper editor validation.
        elif value.strip() == '':
            changed = False
        else:
            changed = True
            # set the value using the delegate's setter, if it has one.
            try:
                attributeSetter = self.delegate.SetAttributeValue
            except AttributeError:
                grid.SetElementValue (row, column, value)
            else:
                attributeSetter (item, attributeName, value)
        self.delegate.EndControlEdit (item, attributeName, self.control)
        return changed

    def Reset (self):
        self.delegate.SetControlValue (self.control, self.initialValue)

    def GetValue (self):
        assert False # who needs this?
        return self.delegate.GetControlValue (self.control)

class Table (PimBlocks.FocusEventHandlers, RectangularChild):

    columnHeadings = schema.Sequence(schema.Text, required = True)
    columnHeadingTypes = schema.Sequence(schema.Text)
    columnData = schema.Sequence(schema.Text)
    columnWidths = schema.Sequence(schema.Integer, required = True)
    columnReadOnly = schema.Sequence(schema.Boolean)
    elementDelegate = schema.One(schema.Bytes, initialValue = '')
    selection = schema.Sequence(schema.List, initialValue = [])
    selectedItemToView = schema.One(schema.Item, initialValue = None)
    hideColumnHeadings = schema.One(schema.Boolean, initialValue = False)
    characterStyle = schema.One(Styles.CharacterStyle)
    headerCharacterStyle = schema.One(Styles.CharacterStyle)
    hasGridLines = schema.One(schema.Boolean, initialValue = False)

    schema.addClouds(
        copying = schema.Cloud(
            byRef=[characterStyle,headerCharacterStyle,selectedItemToView]
        )
    )

    def __init__(self, *arguments, **keywords):
        super (Table, self).__init__ (*arguments, **keywords)

    def instantiateWidget (self):
        widget = wxTable (self.parentBlock.widget, 
                          Block.getWidgetID(self),
                          characterStyle=getattr(self, "characterStyle", None),
                          headerCharacterStyle=getattr(self, "headerCharacterStyle", None))        
        defaultName = "_default"
        widget.SetDefaultRenderer (GridCellAttributeRenderer (defaultName))
        aeKind = AttributeEditors.AttributeEditorMapping.getKind(\
            wx.GetApp().UIRepositoryView)
        for ae in aeKind.iterItems():
            key = ae.itsName
            if key != defaultName and not '+' in key:
                widget.RegisterDataType (key,
                                         GridCellAttributeRenderer (key),
                                         GridCellAttributeEditor (key))
        return widget

    def GetCurrentContents(self, writable=False):
        """
        The table's self.contents may contain a collectionList, in
        case this collection is composed of other collections. In this
        case, collectionList[0] is the 'primary' collection that
        should handle adds/deletes and other status updates
        """
        if hasattr(self.contents, 'collectionList'):
            collection = self.contents.collectionList[0]
        else:
            collection = self.contents
            
        # Sometimes you need a non-readonly collection. Should we be
        # checking if the collection has an 'add' attribute too?
        if not (writable and not collection.isReadOnly()):
            return collection

    def onSetContentsEvent (self, event):
        item = event.arguments ['item']
        if isinstance (item, AbstractCollection):
            self.contents = item

    def onSelectItemsEvent (self, event):
        items = event.arguments ['items']
        self.select_items (items)

    def select (self, item):
        # polymorphic method used by scripts
        self.select_items ([item])

    def select_items (self, items):
        """
        Select the row corresponding to each item, and account for the
        fact that not all of the items are int the table
        Also make the first visible 
        """
        visiblerow = None
        self.widget.ClearSelection()
        lastColumn = self.widget.GetColumnCount() - 1
        for item in items:
            try:
                row = self.contents.index (item)
            except ValueError:
                continue

            if visiblerow is None:
                visiblerow = row
                
            if item != self.selectedItemToView:
                self.selectedItemToView = item
                self.widget.SelectBlock (row, 0, row, lastColumn, True)
                
        if visiblerow is not None:
            self.widget.MakeCellVisible (row, 0)

    def onDeleteEvent(self, event):

        # precache the trash so we don't have to keep looking it up
        trash = schema.ns('osaf.app', self).TrashCollection
        
        def MoveToTrash(item):
            trash.add(item)

        # this is broken, we shouldn't be going through the widget
        # see additional comments in DeleteSelection itself
        self.widget.DeleteSelection(MoveToTrash)
        
    def onRemoveEventUpdateUI (self, event):
        collection = self.GetCurrentContents()
        event.arguments['Enable'] = not self.HasReadonlySelection()
        event.arguments['Text'] = _(u'Delete from \'%s\'') % collection.displayName

    def onRemoveEvent (self, event):

        collection = self.GetCurrentContents(writable=False)
        assert collection, "Shouldn't be calling this on a readonly collection)"
        def Delete(item):
            collection.remove(item)

        self.widget.DeleteSelection(Delete)

    def HasReadonlySelection(self):
        readOnly = True
        for range in self.selection:
            for row in xrange (range[0], range[1] + 1):
                readOnly, always = self.widget.ReadOnly (row, 0)
                if not readOnly or always:
                    break
        return readOnly

    def onDeleteEventUpdateUI(self, event):
        event.arguments['Enable'] = not self.HasReadonlySelection()

class radioAlignEnumType(schema.Enumeration):
      values = "Across", "Down"


class RadioBox(RectangularChild):

    title = schema.One(schema.Text)
    choices = schema.Sequence(schema.Text)
    radioAlignEnum = schema.One(radioAlignEnumType)
    itemsPerLine = schema.One(schema.Integer)
    event = schema.One(BlockEvent)
    schema.addClouds(
        copying = schema.Cloud(byCloud=[event])
    )

    def instantiateWidget(self):
        if self.radioAlignEnum == "Across":
            dimension = wx.RA_SPECIFY_COLS
        elif self.radioAlignEnum == "Down":
            dimension = wx.RA_SPECIFY_ROWS
        elif __debug__:
            assert False, "unknown radioAlignEnum"

        return wx.RadioBox (self.parentBlock.widget,
                            -1,
                            self.title,
                            wx.DefaultPosition, 
                            (self.minimumSize.width, self.minimumSize.height),
                            self.choices, self.itemsPerLine, dimension)

class wxStaticText(ShownSynchronizer, wx.StaticText):
    pass

class StaticText(RectangularChild):

    textAlignmentEnum = schema.One(
        textAlignmentEnumType, initialValue = 'Left',
    )
    characterStyle = schema.One(Styles.CharacterStyle)
    title = schema.One(schema.Text)

    schema.addClouds(
        copying = schema.Cloud(byRef=[characterStyle])
    )

    def instantiateWidget (self):
        if self.textAlignmentEnum == "Left":
            style = wx.ALIGN_LEFT
        elif self.textAlignmentEnum == "Center":
            style = wx.ALIGN_CENTRE
        elif self.textAlignmentEnum == "Right":
            style = wx.ALIGN_RIGHT

        if Block.showBorders:
            style |= wx.SIMPLE_BORDER

        staticText = wxStaticText (self.parentBlock.widget,
                                   -1,
                                   self.title,
                                   wx.DefaultPosition,
                                   (self.minimumSize.width, self.minimumSize.height),
                                   style)
        staticText.SetFont(Styles.getFont(getattr(self, "characterStyle", None)))
        return staticText

    
class wxStatusBar (ShownSynchronizer, wx.StatusBar):
    def __init__(self, *arguments, **keyWords):
        super (wxStatusBar, self).__init__ (*arguments, **keyWords)
        self.gauge = wx.Gauge(self, -1, 100, size=(125, 30), style=wx.GA_HORIZONTAL|wx.GA_SMOOTH)
        self.gauge.Show(False)

    def Destroy(self):
        self.blockItem.getFrame().SetStatusBar(None)
        super (wxStatusBar, self).Destroy()
        
    def wxSynchronizeWidget(self, **hints):
        super (wxStatusBar, self).wxSynchronizeWidget()
        self.blockItem.getFrame().Layout()


class StatusBar(Block):
    def instantiateWidget (self):
        frame = self.getFrame()
        widget = wxStatusBar (frame, Block.getWidgetID(self))
        frame.SetStatusBar (widget)
        return widget

    def setStatusMessage(self, statusMessage, progressPercentage=-1):
        """
          Allows you to set the message contained in the status bar.  You can also specify 
        values for the progress bar contained on the right side of the status bar.  If you
        specify a progressPercentage (as a float 0 to 1) the progress bar will appear.  If 
        no percentage is specified the progress bar will disappear.
        """
        if progressPercentage == -1:
            if self.widget.GetFieldsCount() != 1:
                self.widget.SetFieldsCount(1)
            self.widget.SetStatusText(statusMessage)
            self.widget.gauge.Show(False)
        else:
            if self.widget.GetFieldsCount() != 2:
                self.widget.SetFieldsCount(2)
                self.widget.SetStatusWidths([-1, 150])
            if statusMessage is not None:
                self.widget.SetStatusText(statusMessage)
            self.widget.gauge.Show(True)
            self.widget.gauge.SetValue((int)(progressPercentage*100))
            # By default widgets are added to the left side...we must reposition them
            rect = self.widget.GetFieldRect(1)
            self.widget.gauge.SetPosition((rect.x+2, rect.y+2))
                            
"""
  To use the TreeAndList you must provide a delegate to perform access
to the data that is displayed. 
  You might be able to subclass ListDelegate and implement the following methods:

class TreeAndListDelegate (ListDelegate):

    def GetElementParent(self, element):

    def GetElementChildren(self, element):

    def GetElementValues(self, element):

    def ElementHasChildren(self, element):
        
    Optionally override GetColumnCount and GetColumnHeading
"""


class wxTreeAndList(DragAndDrop.DraggableWidget, DragAndDrop.ItemClipboardHandler):
    def __init__(self, *arguments, **keywords):
        super (wxTreeAndList, self).__init__ (*arguments, **keywords)
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnExpanding, id=self.GetId())
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSING, self.OnCollapsing, id=self.GetId())
        self.Bind(wx.EVT_LIST_COL_END_DRAG, self.OnColumnDrag, id=self.GetId())
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnWXSelectItem, id=self.GetId())
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnItemDrag)

    def OnInit (self):
        mixinAClass (self, self.blockItem.elementDelegate)
        
    def OnSize(self, event):
        if not wx.GetApp().ignoreSynchronizeWidget:
            if isinstance (self, wx.gizmos.TreeListCtrl):
                size = self.GetClientSize()
                widthMinusLastColumn = 0
                assert self.GetColumnCount() > 0, "We're assuming that there is at least one column"
                for column in xrange (self.GetColumnCount() - 1):
                    widthMinusLastColumn += self.GetColumnWidth (column)
                lastColumnWidth = size.width - widthMinusLastColumn
                if lastColumnWidth > 0:
                    self.SetColumnWidth (self.GetColumnCount() - 1, lastColumnWidth)
            else:
                assert isinstance (self, wx.TreeCtrl), "We're assuming the only other choice is a wx.Tree"
        event.Skip()

    def OnExpanding(self, event):
        if not wx.GetApp().ignoreSynchronizeWidget:
            self.LoadChildren(event.GetItem())

    def LoadChildren(self, parentId):
        """
          Load the items in the tree only when they are visible.
        """
        child, cookie = self.GetFirstChild (parentId)
        if not child.IsOk():

            parentUUID = self.GetItemData(parentId).GetData()
            app = wx.GetApp()
            for child in self.GetElementChildren (app.UIRepositoryView [parentUUID]):
                cellValues = self.GetElementValues (child)
                childNodeId = self.AppendItem (parentId,
                                               cellValues.pop(0),
                                               -1,
                                               -1,
                                               wx.TreeItemData (child.itsUUID))
                index = 1
                for value in cellValues:
                    self.SetItemText (childNodeId, value, index)
                    index += 1
                self.SetItemHasChildren (childNodeId, self.ElementHasChildren (child))
 
            self.blockItem.openedContainers [parentUUID] = True

    def OnCollapsing(self, event):
        id = event.GetItem()
        """
          if the data passed in has a UUID we'll keep track of the
        state of the opened tree
        """
        del self.blockItem.openedContainers [self.GetItemData(id).GetData()]
        self.DeleteChildren (id)

    def OnColumnDrag(self, event):
        if not wx.GetApp().ignoreSynchronizeWidget:
            columnIndex = event.GetColumn()
            try:
                self.blockItem.columnWidths [columnIndex] = self.GetColumnWidth (columnIndex)
            except AttributeError:
                pass

    def OnWXSelectItem(self, event):
        if not wx.GetApp().ignoreSynchronizeWidget:
    
            itemUUID = self.GetItemData(self.GetSelection()).GetData()
            selection = self.blockItem.find (itemUUID)
            if self.blockItem.selection != selection:
                self.blockItem.selection = selection
        
                self.blockItem.postEventByName("SelectItemsBroadcast",
                                               {'items':[selection]})
        event.Skip()
        
    def SelectedItems(self):
        """
        Return the list of selected items.
        """
        try:
            idList = self.GetSelections() # multi-select API supported?
        except:
            idList = [self.GetSelection(), ] # use single-select API
        # convert from ids, which are UUIDs, to items.
        itemList = []
        for id in idList:
            itemUUID = self.GetItemData(id).GetData()
            itemList.append(self.blockItem.findUUID(itemUUID))
        return itemList

    def OnItemDrag(self, event):
        self.DoDragAndDrop()
        
    def wxSynchronizeWidget(self, **hints):
        def ExpandContainer (self, openedContainers, id):
            try:
                expand = openedContainers [self.GetItemData(id).GetData()]
            except KeyError:
                pass
            else:
                self.LoadChildren(id)

                self.Expand(id)

                child, cookie = self.GetFirstChild (id)
                while child.IsOk():
                    ExpandContainer (self, openedContainers, child)
                    child = self.GetNextSibling (child)

        try:
            self.blockItem.columnWidths
        except AttributeError:
            pass # A wx.TreeCtrl won't use columnWidths
        else:
            for index in xrange(wx.gizmos.TreeListCtrl.GetColumnCount(self)):
                self.RemoveColumn (0)
    
            for index in xrange (self.GetColumnCount()):
                info = wx.gizmos.TreeListColumnInfo()
                info.SetText (self.GetColumnHeading (index, None))
                info.SetWidth (self.blockItem.columnWidths [index])
                self.AddColumnInfo (info)

        self.DeleteAllItems()

        root = self.blockItem.rootPath
        if not root:
            root = self.GetElementChildren (None)
        cellValues = self.GetElementValues (root)
        rootNodeId = self.AddRoot (cellValues.pop(0),
                                   -1,
                                   -1,
                                   wx.TreeItemData (root.itsUUID))        
        index = 1
        for value in cellValues:
            self.SetItemText (rootNodeId, value, index)
            index += 1
        self.SetItemHasChildren (rootNodeId, self.ElementHasChildren (root))
        self.LoadChildren (rootNodeId)
        ExpandContainer (self, self.blockItem.openedContainers, rootNodeId)

        selection = self.blockItem.selection
        if not selection:
            selection = root
        self.GoToItem (selection)
        
    def GoToItem(self, item):
        def ExpandTreeToItem (self, item):
            parent = self.GetElementParent (item)
            if parent:
                id = ExpandTreeToItem (self, parent)
                self.LoadChildren(id)
                if self.IsVisible(id):
                    self.Expand (id)
                itemUUID = item.itsUUID
                child, cookie = self.GetFirstChild (id)
                while child.IsOk():
                    if self.GetItemData(child).GetData() == itemUUID:
                        return child
                    child = self.GetNextSibling (child)
                assert False, "Didn't find the item in the tree"
                return None
            else:
                return self.GetRootItem()

        id = ExpandTreeToItem (self, item)
        self.SelectItem (id)
        self.ScrollTo (id)

    @classmethod
    def CalculateWXStyle(theClass, block):
        style = wx.TR_DEFAULT_STYLE|wx.NO_BORDER
        if block.hideRoot:
            style |= wx.TR_HIDE_ROOT
        if block.noLines:
            style |= wx.TR_NO_LINES
        if block.useButtons:
            style |= wx.TR_HAS_BUTTONS
        else:
            style |= wx.TR_NO_BUTTONS
        return style
        
 
class wxTree(wxTreeAndList, wx.TreeCtrl):
    pass
    

class wxTreeList(wxTreeAndList, wx.gizmos.TreeListCtrl):
    pass


class Tree(RectangularChild):

    columnHeadings = schema.Sequence(schema.Text, required = True)
    columnData = schema.Sequence(schema.Text)
    columnWidths = schema.Sequence(schema.Integer, required = True)
    elementDelegate = schema.One(schema.Bytes, initialValue = '')
    selection = schema.One(schema.Item, initialValue = None)
    hideRoot = schema.One(schema.Boolean, initialValue = True)
    noLines = schema.One(schema.Boolean, initialValue = True)
    useButtons = schema.One(schema.Boolean, initialValue = True)
    openedContainers = schema.Mapping(schema.Boolean, initialValue = {})
    rootPath = schema.One(schema.Item, initialValue = None)

    schema.addClouds(
        copying = schema.Cloud(byRef=[selection])
    )

    def instantiateWidget(self):
        try:
            self.columnWidths
        except AttributeError:
            tree = wxTree (self.parentBlock.widget, Block.getWidgetID(self), 
                           style=wxTreeAndList.CalculateWXStyle(self))
        else:
            tree = wxTreeList (self.parentBlock.widget, Block.getWidgetID(self), 
                               style=wxTreeAndList.CalculateWXStyle(self))
        return tree

    def onSelectItemsEvent (self, event):
        items = event.arguments['items']
        if len(items)>0:
            self.widget.GoToItem (event.arguments['items'][0])


class wxItemDetail(wx.html.HtmlWindow):
    def OnLinkClicked(self, wx_linkinfo):
        """
          Clicking on an item changes the selection (post event).
          Clicking on a URL loads the page in a separate browser.
        """
        itemURL = wx_linkinfo.GetHref()
        item = self.blockItem.findPath(itemURL)
        if not item:
            webbrowser.open(itemURL)
        else:
            self.blockItem.postEventByName("SelectItemsBroadcast",
                                           {'items':[item]})

    def wxSynchronizeWidget(self, **hints):
        if self.blockItem.selection is not None:
            self.SetPage (self.blockItem.getHTMLText (self.blockItem.selection))
        else:
            self.SetPage('<html><body></body></html>')


class ItemDetail(RectangularChild):

    selection = schema.One(schema.Item, initialValue = None)
    schema.addClouds(
        copying = schema.Cloud(byRef=[selection])
    )

    def __init__(self, *arguments, **keywords):
        super (ItemDetail, self).__init__ (*arguments, **keywords)
        self.selection = None

    def instantiateWidget (self):
        return wxItemDetail (self.parentBlock.widget,
                             Block.getWidgetID(self),
                             wx.DefaultPosition,
                             (self.minimumSize.width,
                              self.minimumSize.height))

    def getHTMLText(self, item):
        return u'<body><html><h1>%s</h1></body></html>' % item.getDisplayName()

    def onSelectItemsEvent (self, event):
        """
          Display the item in the wxWidget.
        """
        items = event.arguments['items']
        if len(items)>0:
            self.selection = items[0]
        else:
            self.selection = None
        self.synchronizeWidget ()

    
class ContentItemDetail(BoxContainer):
    """
    ContentItemDetail
    Any container block in the Content Item's Detail View hierarchy.
    Not to be confused with ItemDetail (above) which uses an HTML-based widget.
    Keeps track of the current selected item
    Supports Color Style
    """
    colorStyle = schema.One(Styles.ColorStyle)
    
class wxPyTimer(wx.PyTimer):
    """ 
    A wx.PyTimer that has an IsShown() method, like all the other widgets
    that blocks deal with; it also generates its own event from Notify
    """              
    def IsShown(self):
        return True
    
    def Notify(self):
        event = wx.PyEvent()
        event.SetEventType(wx.wxEVT_TIMER)
        event.SetId(Block.getWidgetID(self.blockItem))
        wx.GetApp().OnCommand(event)

    def Destroy(self):
       Block.wxOnDestroyWidget (self)

class Timer(Block):
    """
    A Timer block. Fires (sending a BlockEvent) at a particular time.
    A passed time will fire "shortly".
    """

    event = schema.One(
        BlockEvent,
        doc = "The event we'll send when we go off",
    )

    schema.addClouds(
        copying = schema.Cloud(byCloud=[event])
    )

    def instantiateWidget (self):
        timer = wxPyTimer(self.parentBlock.widget)
        return timer

    def setFiringTime(self, when):
        # First turn off the old timer
        timer = self.widget
        timer.Stop()

        # Set the new time, if we have one. If it's in the past, fire "really soon". If it's way in the future,
        # don't bother firing.
        if when is not None:
            td = Calendar.datetimeOp(when, '-', datetime.now())
            millisecondsUntilFiring = ((td.days * 86400) + td.seconds) * 1000L
            if millisecondsUntilFiring < 100:
                millisecondsUntilFiring = 100
            elif millisecondsUntilFiring > sys.maxint:
                millisecondsUntilFiring = sys.maxint

            # print "*** setFiringTime: will fire at %s in %s minutes" % (when, millisecondsUntilFiring / 60000)
            timer.Start(millisecondsUntilFiring, True)
        else:
            # print "*** setFiringTime: No new time."
            pass

class ReminderTimer(Timer):
    """ Watches for reminders & drives the reminder dialog. """
    
    def synchronizeWidget (self, **hints):
        # logger.debug("*** Synchronizing ReminderTimer widget!")
        super(ReminderTimer, self).synchronizeWidget(**hints)
        if not wx.GetApp().ignoreSynchronizeWidget:
            pending = self.getPendingReminders()
            closeIt = False
            reminderDialog = self.getReminderDialog(False)
            if reminderDialog is not None:
                (nextReminderTime, closeIt) = reminderDialog.UpdateList(pending)
            if closeIt:
                self.closeReminderDialog();
            self.setFiringTimeIfRemindersExist()

    def render(self, *args, **kwds):
        super(ReminderTimer, self).render(*args, **kwds)
        # Create a monitor to watch for changes that affect reminders
        for attr in ('reminders', 'startTime'):
            Monitors.attach(self, 'onRemindersChanged', 'set', attr)
            
    def onDestroyWidget(self, *args, **kwds):
        # Get rid of the monitors
        for attr in ('reminders', 'startTime'):
            Monitors.detach(self, 'onRemindersChanged', 'set', attr)
        super(ReminderTimer, self).onDestroyWidget(*args, **kwds)

    def onRemindersChanged(self, op, item, attribute):
        self.synchronizeSoon()

    def getPendingReminders (self):
        """ Return a list of reminder tuples sorted by reminderTime 

        Each tuple contains (reminderTime, remindable, reminder) 
        """

        view = self.itsView
        # reminderFireTime always adds a timezone, so add one to now 
        now = datetime.now(PyICU.ICUtzinfo.getDefault())

        def matches(key):
            if view[key].reminderFireTime <= now:
                return 0
            return -1

        events = schema.ns('osaf.app', view).eventsWithReminders.rep
        lastPastKey = events.findInIndex('reminderTime', 'last', matches)

        if lastPastKey is not None:
            return [(ev.reminderFireTime, ev ,ev.reminders.first()) 
                    for ev in (view[key] for key in 
                     events.iterindexkeys('reminderTime', None, lastPastKey))]

        return []
    
    def onReminderTimeEvent(self, event):
        # Run the reminders dialog and re-queue our timer if necessary
        # logger.debug("*** Got reminders time event!")
        pending = self.getPendingReminders()
        reminderDialog = self.getReminderDialog(True)
        assert reminderDialog is not None
        (nextReminderTime, closeIt) = reminderDialog.UpdateList(pending)
        if closeIt:
            # logger.debug("*** closing the dialog!")
            self.closeReminderDialog()
        self.setFiringTimeIfRemindersExist()

    def setFiringTimeIfRemindersExist(self):
        events = schema.ns('osaf.app', self.itsView).eventsWithReminders.rep
        
        firstReminder = events.firstInIndex('reminderTime')

        if firstReminder is not None:
            self.setFiringTime(firstReminder.reminderFireTime)

    def getReminderDialog(self, createIt):
        try:
            reminderDialog = self.widget.reminderDialog
        except AttributeError:
            if createIt:
                reminderDialog = ReminderDialog.ReminderDialog(wx.GetApp().mainFrame, -1)
                self.widget.reminderDialog = reminderDialog
                reminderDialog.dismissCallback = self.synchronizeSoon
            else:
                reminderDialog = None
        return reminderDialog

    def closeReminderDialog(self):
        try:
            reminderDialog = self.widget.reminderDialog
        except AttributeError:
            pass
        else:
            del self.widget.reminderDialog
            reminderDialog.Destroy()

    def setFiringTime(self, when):
        # logger.debug("*** next reminder due %s" % when)
        super(ReminderTimer, self).setFiringTime(when)

class PresentationStyle(schema.Item):
    schema.kindInfo(
        displayName = _(u"Presentation Style")
    )
    sampleText = schema.One(
        schema.Text,
        doc = 'Localized in-place sample text (optional); if "", will use the attr\'s displayName.',
    )
    format = schema.One(
        schema.Bytes,
        doc = 'customization of presentation format',
    )
    choices = schema.Sequence(
        schema.Text,
        doc = 'options for multiple-choice values',
    )
    editInPlace = schema.One(
        schema.Boolean,
        doc = 'For text controls, True if we should wait for a click to become editable',
    )
    lineStyleEnum = schema.One(
        lineStyleEnumType,
        doc = 'SingleLine vs MultiLine for textbox-based editors',
    )
    schema.addClouds(
        copying = schema.Cloud(
            byValue=[sampleText,format,choices,editInPlace,lineStyleEnum]
        )
    )

def getProxiedContentsItem(block):
    item = getattr(block, 'contents', None)
    if item is not None:
        if item.isDeleted():
            logger.debug("getProxiedContentsItem(%s): item is deleted!",
                         getattr(block, 'blockName', '?'))
            item = None
        else:
            # We have an item - return a proxy for it if necessary
            item = RecurrenceDialog.getProxy(u'ui', item)
    return item

class AEBlock(BoxContainer):
    """
    Attribute Editor Block: instantiates an Attribute Editor appropriate for
    the value of the specified attribute; the Attribute Editor then creates
    the widget. Issues:
     - Finalization.  We're relying on EVT_KILL_FOCUS to know when to end 
       editing.  We know the Detail View doesn't always operate in ways that 
       cause this to be reliable, but I think these problems can be fixed there.
    """
    schema.kindInfo(
        displayName=u"Attribute Editor Block Kind",
        description="Block that instantiates an appropriate Attribute Editor."
    )

    characterStyle = schema.One(Styles.CharacterStyle)
    readOnly = schema.One(schema.Boolean, initialValue = False)
    presentationStyle = schema.One(PresentationStyle)
    changeEvent = schema.One(BlockEvent)

    schema.addClouds(
        copying = schema.Cloud(byRef=[characterStyle, presentationStyle, 
                                      changeEvent])
    )
    
    def setItem(self, value): 
        assert not value.isDeleted()
        self.contents = value
    item = property(getProxiedContentsItem, setItem, 
                    doc="Safely access the selected item (or None)")
    
    def getAttributeName(self): return getattr(self, 'viewAttribute', None)
    def setAttributeName(self, value): self.viewAttribute = value
    attributeName = property(getAttributeName, setAttributeName, doc=\
                             "Safely access the configured attribute name (or None)")
    
    def instantiateWidget(self):
        """
        Ask our attribute editor to create a widget for us.
        """
        existingWidget = getattr(self, 'widget', None) 
        if existingWidget is not None:
            return existingWidget
        
        forEditing = getattr(self, 'forEditing', False)

        # Tell the control what font we expect it to use
        try:
            charStyle = self.characterStyle
        except AttributeError:
            charStyle = None
        font = Styles.getFont(charStyle)

        editor = self.lookupEditor()
        if editor is None:
            assert False
            widget = wx.Panel(self.parentBlock.widget, Block.getWidgetID(self))
            return widget
        
        widget = editor.CreateControl(forEditing, editor.readOnly, 
                                      self.parentBlock.widget, 
                                      Block.getWidgetID(self), self, font)
        widget.SetFont(font)
        # logger.debug("Instantiated a %s, forEditing = %s" % (widget, forEditing))
        
        # Cache a little information in the widget.
        widget.editor = editor
        
        widget.Bind(wx.EVT_KILL_FOCUS, self.onLoseFocusFromWidget)
        widget.Bind(wx.EVT_KEY_UP, self.onKeyUpFromWidget)
        widget.Bind(wx.EVT_LEFT_DOWN, self.onClickFromWidget)
                    
        return widget
        
    def synchronizeWidget (self, **hints):
        """
        Override to call the editor to do the synchronization
        """
        app = wx.GetApp()
        if not app.ignoreSynchronizeWidget and hasattr(self, 'widget'):
            oldIgnoreSynchronizeWidget = app.ignoreSynchronizeWidget
            app.ignoreSynchronizeWidget = True
            try:
                editor = self.lookupEditor()
                if editor is not None:
                    editor.BeginControlEdit(editor.item, editor.attributeName, self.widget)
            finally:
                app.ignoreSynchronizeWidget = oldIgnoreSynchronizeWidget

    def onWidgetChangedSize(self):
        """ 
        Called by our widget when it changes size.
        Presumes that there's an event boundary at the point where
        we need to resynchronize, so it will work with the Detail View.
        """
        evtBoundaryWidget = self.widget
        while evtBoundaryWidget is not None:
            if evtBoundaryWidget.blockItem.eventBoundary:
                break
            evtBoundaryWidget = evtBoundaryWidget.GetParent()
        if evtBoundaryWidget:
            evtBoundaryWidget.blockItem.synchronizeWidget()

    def lookupEditor(self):
        """
        Make sure we've got the right attribute editor for this type
        """
        item = self.item
        if item is None:
            return None
        
        # Get the parameters we'll use to pick an editor
        typeName = self.getItemAttributeTypeName()
        attributeName = self.attributeName
        readOnly = self.isReadOnly(item, attributeName)
        try:
            presentationStyle = self.presentationStyle
        except AttributeError:
            presentationStyle = None
        
        # If we have an editor already, and it's the right one, return it.
        try:
            oldEditor = self.widget.editor
        except AttributeError:
            pass
        else:
            if (oldEditor is not None):
                if (oldEditor.typeName == typeName
                   and oldEditor.attributeName == attributeName
                   # see bug 4553 note below: was "and oldEditor.readOnly == readOnly"
                   and oldEditor.presentationStyle is presentationStyle):
                    # Yep, it's good enough - use it.
                    oldEditor.item = item # note that the item may have changed.
                    return oldEditor

                # It's not good enough, so we'll be changing editors.
                # unRender(), then re-render(); lookupEditor will get called
                # from within render() and will install the right editor; once
                # it returns, we can just return that.
                # @@@ Note:
                # - I don't know of a case where this can happen now (it would
                #   require a contentitem kind containing an attribute whose
                #   value could have different types, and whose different types
                #   have different attribute editors registered for them), 
                #   so this hasn't been tested.
                # - If this does happen in a situation where this code is called
                #   from within a wx event handler on this item's widget, a
                #   crash would result (because wx won't be happy if we return
                #   through it after that widget has been destroyed).
                # Additional note from work on bug 4553:
                # - Prior to bug 4553, we included read-onlyness in the test 
                #   above for whether the existing editor was still suitable 
                #   for editing this attribute. Unfortunately, that bug
                #   presented a case where this (a need to change widgets, which 
                #   the code below wants to do, but which doesn't work right)
                #   happened. Since this case only happens in 0.6 when readonly-
                #   ness is the issue on text ctrls, I'm fixing the problem by 
                #   making BeginControlEdit on those ctrls call wx.SetEditable
                #   (or not) when appropriate.
                assert False, "Please let Bryan know you've found a case where this happens!"
                logger.debug("AEBlock.lookupEditor %s: Rerendering", 
                             getattr(self, 'blockName', '?'))
                self.unRender()
                self.render()
                self.onWidgetChangedSize(item)
                return getattr(self.widget, 'editor', None)
                    
        # We need a new editor - create one.
        #logger.debug("Creating new AE for %s (%s.%s), ro=%s", 
                     #typeName, item, attributeName, readOnly)
        selectedEditor = AttributeEditors.getInstance\
                       (typeName, item, attributeName, readOnly, presentationStyle)
        
        # Note the characteristics that made us pick this editor
        selectedEditor.typeName = typeName
        selectedEditor.item = item
        selectedEditor.attributeName = attributeName
        selectedEditor.readOnly = readOnly
        selectedEditor.presentationStyle = presentationStyle
        selectedEditor.parentBlock = self

        # Register for value changes
        selectedEditor.SetChangeCallback(self.onAttributeEditorValueChange)
        return selectedEditor

    def isReadOnly(self, item, attributeName):
        # Return true if this presentation is always supposed to be readonly
        if self.readOnly: 
            return True
        
        # Return true if the content model says this attribute should be R/O
        # (we might not be editing an item, so we check the method presence)
        try:
            isAttrModifiable = item.isAttributeModifiable
        except AttributeError:
            result = False
        else:
            result = not isAttrModifiable(attributeName)

        #logger.debug("AEBlock: %s %s readonly", attributeName,
                     #result and "is" or "is not")
        return result
        
    def onSetContentsEvent (self, event):
        self.setContentsOnBlock(event.arguments['item'])
        assert not hasattr(self, 'widget')
            
    def getItemAttributeTypeName(self):
        """ Get the type of the current attribute """
        item = self.item
        if item is None:
            return None

        # Ask the schema for the attribute's type first
        try:
            theType = item.getAttributeAspect(self.attributeName, "type")
        except:
            # If the repository doesn't know about it (it might be a property),
            # see if it's one of our type-friendly Calculated properties
            try:
                theType = schema.itemFor(getattr(item.__class__, 
                                                 self.attributeName).type, 
                                         item.itsView)
            except:
                # get its value and use its type
                try:
                    attrValue = getattr(item, self.attributeName)
                except:
                    typeName = "_default"
                else:
                    typeName = type(attrValue).__name__
            else:
                # Got the computed property's type - get its name
                typeName = theType.itsName
        else:
            # Got the repository type (maybe) - get its name
            if theType is None:
                typeName = "NoneType"
            else:
                typeName = theType.itsName
        
        return typeName

    def onClickFromWidget(self, event):
        """
          The widget got clicked on - make sure we're in edit mode.
        """
        #logger.debug("AEBlock: %s widget got clicked on", self.attributeName)

        # If the widget didn't get focus as a result of the click,
        # grab focus now.
        # @@@ This was an attempt to fix bug 2878 on Mac, which doesn't focus
        # on popups when you click on them (or tab to them!)
        oldFocus = self.getFocusBlock()
        if oldFocus is not self:
            Block.finishEdits(oldFocus) # finish any edits in progress
        
            #logger.debug("Grabbing focus.")
            wx.Window.SetFocus(self.widget)

        event.Skip()

    def onLoseFocusFromWidget(self, event):
        """
          The widget lost focus - we're finishing editing.
        """
        #logger.debug("AEBlock: %s, widget losing focus" % self.blockName)
        
        if event is not None:
            event.Skip()
        
        # Workaround for wx Mac crash bug, 2857: ignore the event if we're being deleted
        widget = getattr(self, 'widget', None)
        if widget is None or widget.IsBeingDeleted() or widget.GetParent().IsBeingDeleted():
            #logger.debug("AEBlock: skipping onLoseFocus because the widget is being deleted.")
            return

        # Make sure the value is written back to the item. 
        self.saveValue()

    def saveValue(self, validate=False):
        # Make sure the value is written back to the item. 
        widget = getattr(self, 'widget', None)
        if widget is not None:
            editor = self.widget.editor
            if editor is not None:
                editor.EndControlEdit(self.item, self.attributeName, widget)

    def unRender(self):
        # Last-chance write-back.
        if getattr(self, 'forEditing', False):
            self.saveValue()
        super(AEBlock, self).unRender()
            
    def onKeyUpFromWidget(self, event):
        if event.m_keyCode == wx.WXK_RETURN:
            self.saveValue()
            
            # Do the tab thing if we're not a multiline thing.
            # stearns says: I think this is wrong (it doesn't mix well when one 
            # of the fields you'd "enter" through is multiline - it clears the 
            # content!) but Mimi wants it to work like iCal.
            try:
                isMultiLine = self.presentationStyle.lineStyleEnum == "MultiLine"
            except AttributeError:
                isMultiLine = False
            if not isMultiLine:
                self.widget.Navigate()
        event.Skip()

    def onAttributeEditorValueChange(self):
        """ Called when the attribute editor changes the value """
        item = self.item
        logger.debug("onAttributeEditorValueChange: %s %s", 
                     item, self.attributeName)
        try:
            event = self.changeEvent
        except AttributeError:
            pass
        else:
            self.post(event, {'item': item, 
                              'attribute': self.attributeName })


# Ewww, yuk.  Blocks and attribute editors are mutually interdependent
import osaf.framework.attributeEditors
AttributeEditors = sys.modules['osaf.framework.attributeEditors']

