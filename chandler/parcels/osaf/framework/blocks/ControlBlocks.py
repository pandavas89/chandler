__version__ = "$Revision$"
__date__ = "$Date$"
__copyright__ = "Copyright (c) 2003 Open Source Applications Foundation"
__license__ = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

import time
import os
import application.Globals as Globals
from application.Application import mixinAClass
from Block import *
from ContainerBlocks import *
from Styles import Font
from repository.util.UUID import UUID
import wx
import wx.html
import wx.gizmos
import wx.grid
import webbrowser # for opening external links

class wxButton(wx.Button):
    def __del__(self):
        del Globals.association [self.blockUUID]

        
class wxBitmapButton(wx.BitmapButton):
    def __del__(self):
        del Globals.association [self.blockUUID]

        
class wxToggleButton(wx.ToggleButton):
    def __del__(self):
        del Globals.association [self.blockUUID]

        
class Button(RectangularChild):
    def instantiateWidget(self):
        try:
            id = Block.getWidgetID(self)
        except AttributeError:
            id = 0

        parentWidget = Globals.association [self.parentBlock.itsUUID]
        if self.buttonKind == "Text":
            button = wxButton(parentWidget, id, self.title,
                              wx.DefaultPosition,
                              (self.minimumSize.width, self.minimumSize.height))
        elif self.buttonKind == "Image":
            image = wx.Image(self.icon, 
                             wx.BITMAP_TYPE_PNG)
            bitmap = image.ConvertToBitmap()
            button = wxBitmapButton(parentWidget, id, bitmap,
                                    wx.DefaultPosition,
                                    (self.minimumSize.width, self.minimumSize.height))
        elif self.buttonKind == "Toggle":
            if wx.Platform == '__WXMAC__': # @@@ Toggle buttons are not supported under OSX
                button = wxButton(parentWidget, id, self.title,
                                  wx.DefaultPosition,
                                  (self.minimumSize.width, self.minimumSize.height))
            else:
                button = wxToggleButton(parentWidget, id, self.title,
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
            self.Post(event, {'item':self})

                              
class wxChoice(wx.Choice):
    def __del__(self):
        del Globals.association [self.blockUUID]

class Choice(RectangularChild):
    def instantiateWidget(self):
        choice = wxChoice(parentWindow, -1, 
                          wx.DefaultPosition,
                          (self.minimumSize.width, self.minimumSize.height),
                          self.choices)
        return choice


class wxComboBox(wx.ComboBox):
    def __del__(self):
        del Globals.association [self.blockUUID]

class ComboBox(RectangularChild):
    def instantiateWidget(self):
        parentWidget = Globals.association [self.parentBlock.itsUUID]
        comboBox = wxComboBox(parentWidget, -1, self.selection, 
                              wx.DefaultPosition,
                              (self.minimumSize.width, self.minimumSize.height),
                              self.choices)
        return comboBox


class wxEditText(wx.TextCtrl):
    def __init__(self, *arguments, **keywords):
        super (wxEditText, self).__init__ (*arguments, **keywords)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnEnterPressed, id=self.GetId())

    def OnEnterPressed(self, event):
        block = Globals.repository.find (self.blockUUID)
        block.Post (Globals.repository.findPath('//parcels/osaf/framework/blocks/Events/EnterPressed'),
                   {'text':self.GetValue()})

    def __del__(self):
        del Globals.association [self.blockUUID]


class EditText(RectangularChild):
    def instantiateWidget(self):
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

        parentWidget = Globals.association [self.parentBlock.itsUUID]
        editText = wxEditText (parentWidget,
                               -1,
                               "",
                               wx.DefaultPosition,
                               (self.minimumSize.width, self.minimumSize.height),
                               style=style, name=self._name)

        editText.SetFont(Font (self.characterStyle))
        return editText



class wxHTML(wx.html.HtmlWindow):
    def OnLinkClicked(self, link):
        webbrowser.open(link.GetHref())

    def __del__(self):
        del Globals.association [self.blockUUID]


class HTML(RectangularChild):
    def instantiateWidget (self):
        parentWidget = Globals.association [self.parentBlock.itsUUID]
        htmlWindow = wxHTML(parentWidget,
                            Block.getWidgetID(self),
                            wx.DefaultPosition,
                            (self.minimumSize.width, self.minimumSize.height))
        if self.url:
            htmlWindow.LoadPage(self.url)
        return htmlWindow

 
class ListDelegate:
    """
      Default delegate for Lists that use the block's contents. Override
    to customize your behavior.
    """
    def GetElementText (self, row, column):
        block = Globals.repository.find (self.blockUUID)
        result = block.contents[item]
        name = block.columnHeadings[column]
        try:
            return str (result.getAttributeValue(name))
        except AttributeError:
            return ""

    def SetElementText (self, row, column, value):
        block = Globals.repository.find (self.blockUUID)
        result = block.contents[item]
        column = block.columnHeadings[column]
        result.setAttributeValue(column, value)

    def ElementCount (self):
        block = Globals.repository.find (self.blockUUID)
        return block.contents.len()


class wxList (wx.ListCtrl):
    def __init__(self, *arguments, **keywords):
        super (wxList, self).__init__ (*arguments, **keywords)
        self.scheduleUpdate = False
        self.lastUpdateTime = 0
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.On_wxSelectionChanged, id=self.GetId())
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_SIZE, self.OnSize)

    def OnIdle(self, event):
        """
          Wait a second after a update is first scheduled before updating
        and don't update more than once a second.
        """
        if self.scheduleUpdate:
            if (time.time() - self.lastUpdateTime) > 1.0:
                block = Globals.repository.find (self.blockUUID)
                block.synchronizeWidget()
        else:
            lastupdateTime = time.time()
        event.Skip()

    def OnSize(self, event):
        if not Globals.wxApplication.ignoreSynchronizeWidget:
            size = self.GetClientSize()
            widthMinusLastColumn = 0
            assert self.GetColumnCount() > 0, "We're assuming that there is at least one column"
            for column in xrange (self.GetColumnCount() - 1):
                widthMinusLastColumn += self.GetColumnWidth (column)
            lastColumnWidth = size.width - widthMinusLastColumn
            if lastColumnWidth > 0:
                self.SetColumnWidth (self.GetColumnCount() - 1, lastColumnWidth)
        event.Skip()

    def On_wxSelectionChanged(self, event):
        if not Globals.wxApplication.ignoreSynchronizeWidget:
            block = Globals.repository.find (self.blockUUID)
            item = block.contents [event.GetIndex()]
            if block.selection != item:
                block.selection = item
            block.Post (Globals.repository.findPath('//parcels/osaf/framework/blocks/Events/SelectionChanged'),
                       {'item':item})


    def wxSynchronizeWidget(self):
        block = Globals.repository.find (self.blockUUID)
        elementDelegate = block.elementDelegate
        if not elementDelegate:
            elementDelegate = '//parcels/osaf/framework/blocks/ControlBlocks/ListDelegate'
        mixinAClass (self, elementDelegate)

        itemCollection = block.contents
        itemCollection.resultsStale = True
        self.Freeze()
        self.ClearAll()
        for index in xrange (len(block.columnHeadings)):
            self.InsertColumn(index,
                              str(block.columnHeadings[index]),
                              width = block.columnWidths[index])

        self.SetItemCount (self.ElementCount())
        self.Thaw()
        try:
            subscription = self.subscriptionUUID
        except AttributeError:
            block = Globals.repository.find (self.blockUUID)
            events = [Globals.repository.findPath('//parcels/osaf/framework/item_changed'),
                      Globals.repository.findPath('//parcels/osaf/framework/item_added'),
                      Globals.repository.findPath('//parcels/osaf/framework/item_deleted')]
            self.subscriptionUUID = UUID()
            Globals.notificationManager.Subscribe (events,
                                                   self.subscriptionUUID,
                                                   itemCollection.onItemChanges)
                
        if block.selection:
            self.GoToItem (block.selection)

        self.scheduleUpdate = False
        self.lastUpdateTime = time.time()
        
    def __del__(self):
        Globals.notificationManager.Unsubscribe(self.subscriptionUUID)
        del Globals.association [self.blockUUID]

    def OnGetItemText (self, row, column):
        """
          OnGetItemText won't be called if it's in the delegate -- WxPython won't
        call it if it's in a base class
        """
        return self.GetElementText (row, column)

    def GoToItem(self, item):
        block = Globals.repository.find (self.blockUUID)
        index = block.contents.index (item)
        self.Select (index)


class List(RectangularChild):
    def __init__(self, *arguments, **keywords):
        super (List, self).__init__ (*arguments, **keywords)
        self.selection = None

    def instantiateWidget (self):
        parentWidget = Globals.association [self.parentBlock.itsUUID]
        list = wxList (parentWidget,
                       Block.getWidgetID(self),
                       style=wx.LC_REPORT|wx.LC_VIRTUAL|wx.SUNKEN_BORDER|wx.LC_EDIT_LABELS)
        return list


    def NeedsUpdate(self):
        wxWindow = Globals.association[self.itsUUID]
        wxWindow.scheduleUpdate = True    

    def OnSelectionChangedEvent (self, notification):
        """
          Display the item in the wxWidget.
        """
        self.selection = notification.data['item']
        self.GoToItem (self.selection)


class wxSummaryTable(wx.grid.PyGridTableBase):
    def __init__(self, elementDelegate):
        super (wxSummaryTable, self).__init__ ()
        self.elementDelegate = elementDelegate
        self.cellAttribute = wx.grid.GridCellAttr() 

    def GetAttr(self, row, col, kind):
        self.cellAttribute.IncRef() 
        return self.cellAttribute 

    def GetNumberRows(self):
        return self.elementDelegate.ElementCount() 

    def GetNumberCols(self): 
        block = Globals.repository.find (self.elementDelegate.blockUUID)
        return len(block.columnHeadings)

    def GetColLabelValue(self, column):
        block = Globals.repository.find (self.elementDelegate.blockUUID)
        return block.columnHeadings[column]

    def IsEmptyCell(self, row, column): 
        return False 

    def GetValue(self, row, column): 
        return self.elementDelegate.GetElementText(row, column)

    def SetValue(self, row, column, value):
        self.elementDelegate.GetElementText(row, column, value) 

class wxSummary(wx.grid.Grid):
    def __init__(self, *arguments, **keywords):
        super (wxSummary, self).__init__ (*arguments, **keywords)
        self.SetRowLabelSize(0)
        self.scheduleUpdate = False
        self.lastUpdateTime = 0
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.grid.EVT_GRID_COL_SIZE, self.OnColumnDrag)

    def OnIdle(self, event):
        """
          Wait a second after a update is first scheduled before updating
        and don't update more than once a second.
        """
        if self.scheduleUpdate:
            if (time.time() - self.lastUpdateTime) > 1.0:
                block = Globals.repository.find (self.blockUUID)
                block.synchronizeWidget()
        else:
            lastupdateTime = time.time()
        event.Skip()

    def OnColumnDrag(self, event):
        if not Globals.wxApplication.ignoreSynchronizeWidget:
            block = Globals.repository.find (self.blockUUID)
            columnIndex = event.GetRowOrCol()
            block.columnWidths [columnIndex] = self.GetColSize (columnIndex)

    def OnSize(self, event):
        if not Globals.wxApplication.ignoreSynchronizeWidget:
            size = event.GetSize()
            widthMinusLastColumn = 0
            assert self.GetNumberCols() > 0, "We're assuming that there is at least one column"
            lastColumnIndex = self.GetNumberCols() - 1
            for column in xrange (lastColumnIndex):
                widthMinusLastColumn += self.GetColSize (column)
            lastColumnWidth = size.width - widthMinusLastColumn
            if lastColumnWidth > 0:
                self.SetColSize (lastColumnIndex, lastColumnWidth)
                self.ForceRefresh()
        event.Skip()

    def Reset(self): 
        """
          A Grid can't easily redisplay its contents, so we write the following
        helper function to readjust everything after the contents change
        """
        block = Globals.repository.find (self.blockUUID)
        #Trim/extend the control's rows and update all values
        self.BeginBatch()
        gridTable = self.GetTable()
        newRows = gridTable.GetNumberRows()
        newColumns = gridTable.GetNumberCols()
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
        for columnIndex in xrange (newColumns):
            self.SetColSize (columnIndex, block.columnWidths [columnIndex])

        #Update all displayed values
        message = wx.grid.GridTableMessage (gridTable, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES) 
        self.ProcessTableMessage (message) 
        self.EndBatch() 

        # The scroll bars aren't resized (at least on windows) 
        # Jiggling the size of the window rescales the scrollbars 
        h,w = self.GetSize() 
        self.SetSize ((h+1, w)) 
        self.SetSize ((h, w)) 
        self.ForceRefresh () 

    def wxSynchronizeWidget(self):
        block = Globals.repository.find (self.blockUUID)
        itemCollection = block.contents
        itemCollection.resultsStale = True
        elementDelegate = block.elementDelegate
        if not elementDelegate:
            elementDelegate = '//parcels/osaf/framework/blocks/ControlBlocks/ListDelegate'
        mixinAClass (self, elementDelegate)

        table = self.GetTable()
        if not table:
            """GetNumberCols
              wxSummaryTable handles the callbacks to display the elements of the
            table. Setting the second argument to True cause the table to be deleted
            when the grid is deleted.
            """
            gridTable = wxSummaryTable(self)
            self.SetTable (gridTable, True)
            self.currentRows = gridTable.GetNumberRows()
            self.currentColumns = gridTable.GetNumberCols()

        try:
            subscription = self.subscriptionUUID
        except AttributeError:
            block = Globals.repository.find (self.blockUUID)
            events = [Globals.repository.findPath('//parcels/osaf/framework/item_changed'),
                      Globals.repository.findPath('//parcels/osaf/framework/item_added'),
                      Globals.repository.findPath('//parcels/osaf/framework/item_deleted')]
            self.subscriptionUUID = UUID()
            Globals.notificationManager.Subscribe (events,
                                                   self.subscriptionUUID,
                                                   itemCollection.onItemChanges)
        self.Reset()
        if block.selection:
            self.GoToItem (block.selection)

        self.scheduleUpdate = False
        self.lastUpdateTime = time.time()
        
    def __del__(self):
        Globals.notificationManager.Unsubscribe(self.subscriptionUUID)
        del Globals.association [self.blockUUID]

    def OnGetItemText (self, row, column):
        """
          OnGetItemText won't be called if it's in the delegate -- WxPython won't
        call it if it's in a base class
        """
        return self.GetElementText (row, column)

    def GoToItem(self, item):
        block = Globals.repository.find (self.blockUUID)
        row = block.contents.index (item)
        self.SelectRow (row)


class Summary(RectangularChild):
    def __init__(self, *arguments, **keywords):
        super (Summary, self).__init__ (*arguments, **keywords)
        self.selection = None

    def instantiateWidget (self):
        parentWidget = Globals.association [self.parentBlock.itsUUID]
        list = wxSummary (parentWidget, Block.getWidgetID(self))
        return list

    def NeedsUpdate(self):
        wxWindow = Globals.association[self.itsUUID]
        wxWindow.scheduleUpdate = True    

    def OnSelectionChangedEvent (self, notification):
        """
          Display the item in the wxWidget.
        """
        self.selection = notification.data['item']
        self.GoToItem (self.selection)


class wxRadioBox(wx.RadioBox):
    def __del__(self):
        del Globals.association [self.blockUUID]


class RadioBox(RectangularChild):
    def instantiateWidget(self):
        if self.radioAlignEnum == "Across":
            dimension = wx.RA_SPECIFY_COLS
        elif self.radioAlignEnum == "Down":
            dimension = wx.RA_SPECIFY_ROWS
        elif __debug__:
            assert False, "unknown radioAlignEnum"
                                    
        parentWidget = Globals.association [self.parentBlock.itsUUID]
        radioBox = wxRadioBox(parentWidget, -1, self.title,
                              wx.DefaultPosition, 
                              (self.minimumSize.width, self.minimumSize.height),
                              self.choices, self.itemsPerLine, dimension)
        return radioBox


class wxStaticText(wx.StaticText):
    def __del__(self):
        del Globals.association [self.blockUUID]

class StaticText(RectangularChild):
    def instantiateWidget (self):
        if self.textAlignmentEnum == "Left":
            style = wx.ALIGN_LEFT
        elif self.textAlignmentEnum == "Center":
            style = wx.ALIGN_CENTRE
        elif self.textAlignmentEnum == "Right":
            style = wx.ALIGN_RIGHT

        parentWidget = Globals.association [self.parentBlock.itsUUID]
        staticText = wxStaticText (parentWidget,
                                   -1,
                                   self.title,
                                   wx.DefaultPosition,
                                   (self.minimumSize.width, self.minimumSize.height),
                                   style)

        staticText.SetFont(Font (self.characterStyle))
        return staticText

    
class wxStatusBar (wx.StatusBar):
    
    def wxSynchronizeWidget(self):
        block = Globals.repository.find (self.blockUUID)
        if block.open != self.IsShown():
            self.Show (block.open)

    def __del__(self):
        del Globals.association [self.blockUUID]


class StatusBar(Block):
    def instantiateWidget (self):
        frame = Globals.wxApplication.mainFrame
        assert frame.GetStatusBar() == None
        widget = wxStatusBar (frame, Block.getWidgetID(self))
        frame.SetStatusBar (widget)
        return widget


class ToolbarItem(Block):
    """
      Under construction
    """
    def instantiateWidget (self):
        # @@@ Must use self.toolbarLocation rather than wxMainFrame.GetToolBar()
        tool = None
        wxToolbar = Globals.wxApplication.mainFrame.GetToolBar()
        toolbar = Globals.repository.find(wxToolbar.blockUUID)
        parentWidget = Globals.association [self.parentBlock.itsUUID]
        id = Block.getWidgetID(self)
        if self.toolbarItemKind == 'Button':
            bitmap = wx.Image (self.bitmap, 
                               wx.BITMAP_TYPE_PNG).ConvertToBitmap()
            tool = wxToolbar.AddSimpleTool (id, bitmap, 
                                            self.title, self.statusMessage)
            parentWidget.Bind(wx.EVT_TOOL, toolbar.toolPressed, id=id)
        elif self.toolbarItemKind == 'Separator':
            wxToolbar.AddSeparator()
        elif self.toolbarItemKind == 'Check':
            pass
        elif self.toolbarItemKind == 'Radio':
            pass
        elif self.toolbarItemKind == 'Text':
            tool = wx.TextCtrl (wxToolbar, id, "", 
                               wx.DefaultPosition, 
                               wx.Size(300,-1), 
                               wx.TE_PROCESS_ENTER)
            tool.SetName(self.title)
            wxToolbar.AddControl (tool)
            tool.Bind(wx.EVT_TEXT_ENTER, toolbar.toolEnterPressed, id=id)
        elif __debug__:
            assert False, "unknown toolbarItemKind"

        wxToolbar.Realize()

        return tool


class wxTreeAndList:
    def __init__(self, *arguments, **keywords):
        self.scheduleUpdate = False
        self.lastUpdateTime = 0
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnExpanding, id=self.GetId())
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSING, self.OnCollapsing, id=self.GetId())
        self.Bind(wx.EVT_LIST_COL_END_DRAG, self.OnColumnDrag, id=self.GetId())
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.On_wxSelectionChanged, id=self.GetId())
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_SIZE, self.OnSize)

    def OnIdle(self, event):
        """
          Wait a second after a update is first scheduled before updating
        and don't update more than once a second.
        """
        if self.scheduleUpdate:
           if (time.time() - self.lastUpdateTime) > 0.5:
               block = Globals.repository.find (self.blockUUID)
               block.synchronizeWidget()
        else:
            lastupdateTime = time.time()
        event.Skip()

    def OnSize(self, event):
        if not Globals.wxApplication.ignoreSynchronizeWidget:
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
        if not Globals.wxApplication.ignoreSynchronizeWidget:
            self.LoadChildren(event.GetItem())

    def LoadChildren(self, parentId):
        """
          Load the items in the tree only when they are visible.
        """
        child, cookie = self.GetFirstChild (parentId)
        if not child.IsOk():
            
            block = Globals.repository.find (self.blockUUID)
    
            parentUUID = self.GetItemData(parentId).GetData()
            for child in self.ElementChildren (Globals.repository [parentUUID]):
                cellValues = self.ElementCellValues (child)
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
 
            block.openedContainers [parentUUID] = True

    def OnCollapsing(self, event):
        block = Globals.repository.find (self.blockUUID)
        id = event.GetItem()
        """
          if the data passed in has a UUID we'll keep track of the
        state of the opened tree
        """
        del block.openedContainers [self.GetItemData(id).GetData()]
        self.DeleteChildren (id)

    def OnColumnDrag(self, event):
        if not Globals.wxApplication.ignoreSynchronizeWidget:
            block = Globals.repository.find (self.blockUUID)
            columnIndex = event.GetColumn()
            try:
                block.columnWidths [columnIndex] = self.GetColumnWidth (columnIndex)
            except AttributeError:
                pass

    def On_wxSelectionChanged(self, event):
        if not Globals.wxApplication.ignoreSynchronizeWidget:
            block = Globals.repository.find (self.blockUUID)
    
            itemUUID = self.GetItemData(self.GetSelection()).GetData()
            selection = Globals.repository.find (itemUUID)
            if block.selection != selection:
                block.selection = selection
        
                block.Post (Globals.repository.findPath('//parcels/osaf/framework/blocks/Events/SelectionChanged'),
                           {'item':selection})

    def wxSynchronizeWidget(self):
        def ExpandContainer (self, openedContainers, id):
            try:
                expand = openedContainers [self.GetItemData(id).GetData()]
            except KeyError:
                pass
            else:
                self.LoadChildren(id)

                if self.IsVisible (id):
                    self.Expand(id)

                child, cookie = self.GetFirstChild (id)
                while child.IsOk():
                    ExpandContainer (self, openedContainers, child)
                    child = self.GetNextSibling (child)

        block = Globals.repository.find (self.blockUUID)
        mixinAClass (self, block.elementDelegate)
        
        try:
            block.columnHeadings
        except AttributeError:
            pass # A wx.TreeCtrl won't use columnHeadings
        else:
            for index in xrange(self.GetColumnCount()):
                self.RemoveColumn (0)
    
            info = wx.gizmos.TreeListColumnInfo()
            for index in xrange (len(block.columnHeadings)):
                info.SetText (block.columnHeadings[index])
                info.SetWidth (block.columnWidths[index])
                self.AddColumnInfo (info)

        self.DeleteAllItems()

        root = block.rootPath
        if not root:
            root = self.ElementChildren (None)
        cellValues = self.ElementCellValues (root)
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
        ExpandContainer (self, block.openedContainers, rootNodeId)

        selection = block.selection
        if not selection:
            selection = root
        self.GoToItem (selection)

        try:
            subscription = self.subscriptionUUID
        except AttributeError:
            events = [Globals.repository.findPath('//parcels/osaf/framework/item_changed'),
                      Globals.repository.findPath('//parcels/osaf/framework/item_added'),
                      Globals.repository.findPath('//parcels/osaf/framework/item_deleted')]
            block = Globals.repository.find (self.blockUUID)
            self.subscriptionUUID = UUID()
            Globals.notificationManager.Subscribe (events,
                                                   self.subscriptionUUID,
                                                   self.NeedsUpdate)
        self.scheduleUpdate = False
        self.lastUpdateTime = time.time()
        
    def __del__(self):
        Globals.notificationManager.Unsubscribe(self.subscriptionUUID)
        del Globals.association [self.blockUUID]

    def GoToItem(self, item):
        def ExpandTreeToItem (self, item):
            parent = self.ElementParent (item)
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

 
class wxTree(wx.TreeCtrl, wxTreeAndList):
    def __init__(self, *arguments, **keywords):
        super (wxTree, self).__init__ (*arguments, **keywords)
        wxTreeAndList.__init__ (self, *arguments, **keywords)
    

class wxTreeList(wx.gizmos.TreeListCtrl, wxTreeAndList):
    def __init__(self, *arguments, **keywords):
        super (wxTreeList, self).__init__ (*arguments, **keywords)
        wxTreeAndList.__init__ (self, *arguments, **keywords)
    

class Tree(RectangularChild):
    def __init__(self, *arguments, **keywords):
        super (Tree, self).__init__ (*arguments, **keywords)
        self.openedContainers = {}
        self.rootPath = None
        self.selection = None

    def instantiateWidget(self):
        parentWidget = Globals.association [self.parentBlock.itsUUID]
        try:
            self.columnHeadings
        except AttributeError:
            tree = wxTree (parentWidget, Block.getWidgetID(self), style = self.Calculate_wxStyle())
        else:
            tree = wxTreeList (parentWidget, Block.getWidgetID(self), style = self.Calculate_wxStyle())
        return tree

    def OnSelectionChangedEvent (self, notification):
        widget = Globals.association[self.itsUUID]
        widget.GoToItem (notification.GetData()['item'])

    def Calculate_wxStyle (self):
        style = wx.TR_DEFAULT_STYLE|wx.NO_BORDER
        if self.hideRoot:
            style |= wx.TR_HIDE_ROOT
        if self.noLines:
            style |= wx.TR_NO_LINES
        if self.useButtons:
            style |= wx.TR_HAS_BUTTONS
        else:
            style |= wx.TR_NO_BUTTONS
        return style


class wxItemDetail(wx.html.HtmlWindow):
    def OnLinkClicked(self, wx_linkinfo):
        """
          Clicking on an item changes the selection (post notification).
          Clicking on a URL loads the page in a separate browser.
        """
        itemURL = wx_linkinfo.GetHref()
        item = Globals.repository.findPath(itemURL)
        if not item:
            webbrowser.open(itemURL)
        else:
            event = Globals.repository.findPath('//parcels/osaf/framework/blocks/Events/SelectionChanged')
            event.Post({'item':item, 'type':'Normal'})

    def wxSynchronizeWidget(self):
        block = Globals.repository.find (self.blockUUID)
        if block.selection:
            self.SetPage(block.getHTMLText(block.selection))
        else:
            self.SetPage('<html><body></body></html>')

    def __del__(self):
        del Globals.association [self.blockUUID]


class ItemDetail(RectangularChild):
    def __init__(self, *arguments, **keywords):
        super (ItemDetail, self).__init__ (*arguments, **keywords)
        self.selection = None

    def instantiateWidget (self):
        parentWidget = Globals.association [self.parentBlock.itsUUID]
        htmlWindow = wxItemDetail(parentWidget,
                                  Block.getWidgetID(self),
                                  wx.DefaultPosition,
                                  (self.minimumSize.width,
                                   self.minimumSize.height))

        return htmlWindow

    def getHTMLText(self, item):
        return '<body><html><h1>%s</h1></body></html>' % item.getDisplayName()

    def OnSelectionChangedEvent (self, notification):
        """
          Display the item in the wxWidget.
        """
        self.selection = notification.data['item']
        self.synchronizeWidget ()
