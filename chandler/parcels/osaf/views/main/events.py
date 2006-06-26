#   Copyright (c) 2003-2006 Open Source Applications Foundation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


from osaf.usercollections import UserCollection
from osaf.framework.blocks import *

def makeMainEvents(parcel):

    from application import schema
    import osaf.pim.notes
    import osaf.pim.calendar
    import osaf.pim.mail
    import osaf.pim.tasks
    from osaf import pim, messages

    repositoryView = parcel.itsView

    BlockEvent.template(
        'ReminderTime',
        dispatchEnum = 'SendToBlockByReference'
        # destinatinBlockReference is assigned in makeMakeView
        # because of a circular dependence
        ).install(parcel)
    
    NewItemEvent.update(
        parcel, 'NewItem',
        blockName = 'NewItem')

    NewItemEvent.update(
        parcel, 'NewNote',
        blockName = 'NewNote',
        kindParameter = osaf.pim.notes.Note.getKind(repositoryView))

    BlockEvent.template(
        'RunSelectedScript',
        dispatchEnum = 'FocusBubbleUp').install(parcel)

    # Event to put "Scripts" in the Sidebar
    BlockEvent.template('AddScriptsToSidebar').install(parcel)

    BlockEvent.template('AddSharingLogToSidebar').install(parcel)

    BlockEvent.template('BackupRepository').install(parcel)

    BlockEvent.template('CompactRepository').install(parcel)

    BlockEvent.template('IndexRepository').install(parcel)

    BlockEvent.template('UnsubscribeSidebarCollection').install(parcel)

    BlockEvent.template('SharingPublishFreeBusy').install(parcel)

    BlockEvent.template('SharingUnpublishFreeBusy').install(parcel)

    BlockEvent.template('CopyFreeBusyURL').install(parcel)

    BlockEvent.template('ShowPyCrust').install(parcel)

    KindParameterizedEvent.template(
        'ApplicationBarMail',
        methodName = 'onKindParameterizedEvent',
        kindParameter = osaf.pim.mail.MailMessageMixin.getKind(repositoryView),
        dispatchToBlockName = 'Sidebar').install(parcel)

    BlockEvent.template(
        'ShowHideStatusBar',
        methodName = 'onShowHideEvent',
        dispatchToBlockName = 'StatusBar').install(parcel)

    BlockEvent.template('EnableSections').install(parcel)

    BlockEvent.template('EnableTimezones').install(parcel)

    # "Item" menu events
    BlockEvent.template(
        'FocusTogglePrivate',
        dispatchEnum = 'FocusBubbleUp').install(parcel)

    KindParameterizedEvent.template(
        'FocusStampMessage',
        methodName = 'onFocusStampEvent',
        kindParameter = osaf.pim.mail.MailMessageMixin.getKind(repositoryView),
        dispatchEnum = 'FocusBubbleUp').install(parcel)

    KindParameterizedEvent.template(
        'FocusStampTask',
        methodName = 'onFocusStampEvent',
        kindParameter = osaf.pim.tasks.TaskMixin.getKind(repositoryView),
        dispatchEnum = 'FocusBubbleUp').install(parcel)

    KindParameterizedEvent.template(
        'FocusStampCalendar',
        methodName = 'onFocusStampEvent',
        kindParameter = osaf.pim.calendar.Calendar.CalendarEventMixin.getKind(repositoryView),
        dispatchEnum = 'FocusBubbleUp').install(parcel)

    BlockEvent.template('SharingSubscribeToCollection').install(parcel)

    BlockEvent.template('CheckRepository').install(parcel)

    BlockEvent.template('i18nMailTest').install(parcel)

    BlockEvent.template('ShowLogWindow').install(parcel)

    BlockEvent.template('ActivateWebserver').install(parcel)

    BlockEvent.template('BackgroundSyncAll').install(parcel)

    BlockEvent.template('EditMyName').install(parcel)

    BlockEvent.template('CommitRepository').install(parcel)

    BlockEvent.template('GetNewMail',
                       commitAfterDispatch = True).install(parcel)

    BlockEvent.template('ManageSidebarCollection').install(parcel)

    BlockEvent.template('StopProfiler').install(parcel)

    BlockEvent.template('ShowPyShell').install(parcel)

    BlockEvent.template('EditAccountPreferences').install(parcel)

    BlockEvent.template(
        'ShowHideSidebar',
        methodName = 'onShowHideEvent',
        dispatchToBlockName = 'SidebarContainer').install(parcel)

    BlockEvent.template('ReloadParcels').install(parcel)

    BlockEvent.template(
        'ReloadStyles',
        dispatchEnum = 'SendToBlockByName',
        dispatchToBlockName = 'MainView').install(parcel)

    KindParameterizedEvent.template(
        'ApplicationBarAll',
        methodName = 'onKindParameterizedEvent',
        kindParameter = None,
        dispatchToBlockName = 'Sidebar').install(parcel)

    NewItemEvent.update(
        parcel, 'NewMailMessage',
        blockName = 'NewMailMessage',
        kindParameter = osaf.pim.mail.MailMessage.getKind(repositoryView))

    KindParameterizedEvent.template(
        'ApplicationBarEvent',
        methodName = 'onKindParameterizedEvent',
        kindParameter = osaf.pim.calendar.Calendar.CalendarEventMixin.getKind(repositoryView),
        dispatchToBlockName = 'Sidebar').install(parcel)

    NewItemEvent.update(
        parcel, 'NewCalendar',
        blockName = 'NewCalendar',
        kindParameter = osaf.pim.calendar.Calendar.CalendarEvent.getKind(repositoryView))

    BlockEvent.template(
        'Delete',
        commitAfterDispatch = True,
        dispatchEnum = 'FocusBubbleUp').install(parcel)

    BlockEvent.template('ShareSidebarCollection').install(parcel)

    BlockEvent.template('StartProfiler').install(parcel)

    BlockEvent.template('LoadLoggingConfig').install(parcel)

    BlockEvent.template('SearchWindow').install(parcel)

    BlockEvent.template('RestoreShares').install(parcel)

    BlockEvent.template('SyncPrefs').install(parcel)

    BlockEvent.template('RestoreShares').install(parcel)

    BlockEvent.template('SyncCollection').install(parcel)

    BlockEvent.template(
        'ToggleMine',
        dispatchToBlockName = 'Sidebar').install(parcel)

    BlockEvent.template('SharingImportDemoCalendar').install(parcel)

    BlockEvent.template(
        'ShowHideApplicationBar',
        methodName = 'onShowHideEvent',
        dispatchToBlockName = 'ApplicationBar').install(parcel)

    NewItemEvent.update(
        parcel, 'NewTask',
        blockName = 'NewTask',
        kindParameter = osaf.pim.tasks.Task.getKind(repositoryView))

    BlockEvent.template('GenerateContentItems',
                        commitAfterDispatch = True).install(parcel)

    ChoiceEvent.template(
        'ChooseChandlerMainView',
        methodName = 'onChoiceEvent',
        choice = 'MainView',
        dispatchToBlockName = 'MainViewRoot').install(parcel)

    BlockEvent.template('ExportIcalendar').install(parcel)

    BlockEvent.template('SyncAll').install(parcel)

    untitledCollection = pim.SmartCollection.update(parcel,
        'untitledCollection',
        displayName=messages.UNTITLED)

    AddToSidebarEvent.update(
        parcel, 'NewCollection',
        blockName = 'NewCollection',
        editAttributeNamed = 'displayName',
        sphereCollection = schema.ns('osaf.pim', repositoryView).mine,
        item = untitledCollection)
        
    BlockEvent.template('GenerateContentItemsFromFile',
                       commitAfterDispatch = True).install(parcel)

    KindParameterizedEvent.template(
        'ApplicationBarTask',
        methodName = 'onKindParameterizedEvent',
        kindParameter = osaf.pim.tasks.TaskMixin.getKind(repositoryView),
        dispatchToBlockName = 'Sidebar').install(parcel)

    BlockEvent.template('EmptyTrash').install(parcel)

    BlockEvent.template('UnpublishSidebarCollection').install(parcel)

    BlockEvent.template('MimeTest').install(parcel)

    BlockEvent.template('SyncWebDAV').install(parcel)

    BlockEvent.template('WxTestHarness').install(parcel)

    BlockEvent.template('ImportIcalendar',
                       commitAfterDispatch = True).install(parcel)

    BlockEvent.template('CopyCollectionURL').install(parcel)

    BlockEvent.template('TakeOnlineOffline').install(parcel)

    ChoiceEvent.template(
        'ChooseCPIATestMainView',
        methodName = 'onChoiceEvent',
        choice = 'CPIATestMainView',
        dispatchToBlockName = 'MainViewRoot').install(parcel)

    BlockEvent.template(
        'RequestSelectSidebarItem',
        dispatchToBlockName = 'Sidebar').install(parcel)
    
    BlockEvent.template('SendMail').install(parcel)
                  
    BlockEvent.template(
        'Search',
        dispatchEnum = 'FocusBubbleUp').install(parcel)

    BlockEvent.template(
        'SendShareItem',
        dispatchEnum = 'FocusBubbleUp').install(parcel)

    BlockEvent.template('ShareItem').install(parcel)
                  
    BlockEvent.template(
        'SelectedDateChanged',
        dispatchEnum = 'BroadcastEverywhere').install(parcel)
    
    BlockEvent.template(
        'DayMode',
        dispatchEnum = 'BroadcastEverywhere').install(parcel)
        
    blockViewer = schema.ns("osaf.views.blockviewer", repositoryView)
    
    NewBlockWindowEvent.update(
        parcel, 'ShowBlockViewer',
        blockName = 'ShowBlockViewer',
        treeOfBlocks = blockViewer.BlockViewerFrameWindow)

    repositoryViewer = schema.ns("osaf.views.repositoryviewer", repositoryView)

    NewBlockWindowEvent.update(
        parcel, 'ShowRepositoryViewer',
        blockName = 'ShowBlockViewer',
        treeOfBlocks = repositoryViewer.RepositoryViewerFrameWindow)

