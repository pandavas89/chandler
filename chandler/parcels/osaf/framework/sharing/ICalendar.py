import Sharing
import application.Parcel
import osaf.contentmodel.ItemCollection as ItemCollection
import osaf.contentmodel.calendar.Calendar as Calendar
from chandlerdb.util.UUID import UUID
import StringIO
import vobject
import logging
import mx
import dateutil.tz
import datetime
import itertools

logger = logging.getLogger('ICalendar')
logger.setLevel(logging.INFO)

localtime = dateutil.tz.tzlocal()
utc = dateutil.tz.tzutc()

MAXRECUR = 10

def convertToMX(dt, tz=None):
    """Convert the given datetime into an mxDateTime.
    
    Convert dt to tz if it has a timezone.  tz defaults to localtime.
    
    >>> import datetime, mx.DateTime
    >>> dt = datetime.datetime(2004, 12, 20, 18, tzinfo=utc)
    >>> mxdt = convertToMX(dt, pacific)
    >>> print mxdt
    2004-12-20 10:00:00.00
    >>> type(mxdt)
    <type 'DateTime'>
    
    """
    if not tz: tz = localtime
    if getattr(dt, 'tzinfo', None): dt = dt.astimezone(tz)
    return mx.DateTime.mktime(dt.timetuple())

def convertToUTC(dt, tz = None):
    """Convert the given mxDateTime (without tz) into datetime with tzinfo=UTC.
    
    >>> import datetime, mx.DateTime
    >>> mxdt = mx.DateTime.DateTime(2004, 12, 20, 12)
    >>> dt = convertToUTC(mxdt, pacific)
    >>> print dt
    2004-12-20 20:00:00+00:00
    
    """
    if not tz: tz = localtime
    args = (dt.year, dt.month, dt.day, dt.hour, dt.minute, int(dt.second))
    return datetime.datetime(*args).replace(tzinfo=tz).astimezone(utc)

def itemsToVObject(view, items, cal=None):
    """Iterate through items, add to cal, create a new vcalendar if needed.

    Chandler doesn't do recurrence yet, so for now we don't worry
    about timezones.

    """
    taskKind  = view.findPath("//parcels/osaf/contentmodel/EventTask")
    if cal is None:
        cal = vobject.iCalendar()
    for item in items:
        if item.isItemOf(taskKind):
            taskorevent='TASK'
            comp = cal.add('vtodo')
        else:
            taskorevent='EVENT'
            comp = cal.add('vevent')            
        comp.add('uid').value = unicode(item.itsUUID)
        try:
            comp.add('summary').value = item.displayName
        except AttributeError:
            pass
        try:
            comp.add('dtstart').value = convertToUTC(item.startTime)
        except AttributeError:
            pass
        try:
            if taskorevent == 'TASK':
                comp.add('due').value = convertToUTC(item.dueDate)
            else:
                comp.add('dtend').value = convertToUTC(item.endTime)
        except AttributeError:
            pass
        try:
            comp.add('description').value = item.body.getReader().read()
        except AttributeError:
            pass
        try:
            comp.add('valarm').add('trigger').value = \
              convertToUTC(item.reminderTime) - convertToUTC(item.startTime)
        except AttributeError:
            pass
    return cal

class ICalendarFormat(Sharing.ImportExportFormat):
    myKindID = None
    myKindPath = "//parcels/osaf/framework/sharing/ICalendarFormat"

    __calendarEventPath = "//parcels/osaf/contentmodel/calendar/CalendarEvent"
    __taskPath = "//parcels/osaf/contentmodel/EventTask"
    __lobPath = "//Schema/Core/Lob"
    
    def fileStyle(self):
        return self.STYLE_SINGLE

    def extension(self, item):
        return "ics"

    def importProcess(self, text, extension=None, item=None):
        # the item parameter is so that a share item can be passed in for us
        # to populate.

        # An ICalendar file doesn't have any 'share' info, just the collection
        # of events, etc.  Therefore, we want to actually populate the share's
        # 'contents':

        view = self.itsView
        if item is None:
            item = ItemCollection.ItemCollection(view=view)
        elif isinstance(item, Sharing.Share):
            if item.contents is None:
                item.contents = ItemCollection.ItemCollection(view=view)
            item = item.contents

        if not isinstance(item, ItemCollection.ItemCollection):
            print "Only a share or an item collection can be passed in"
            #@@@MOR Raise something

        # @@@MOR Total hack
        # this shouldn't be necessary anymore
        #newtext = []
        #for c in text:
        #    if ord(c) > 127:
        #        c = " "
        #    newtext.append(c)
        #text = "".join(newtext)

        input = StringIO.StringIO(text)
        calendar = vobject.readComponents(input, validate=True).next()

        try:
            calName = calendar.contents[u'x-wr-calname'][0].value
        except:
            calName = "Imported Calendar"
        item.displayName = calName

        countNew = 0
        countUpdated = 0
        eventKind = self.itsView.findPath(self.__calendarEventPath)
        taskKind  = self.itsView.findPath(self.__taskPath)
        textKind  = self.itsView.findPath(self.__lobPath)
        
        eventlist = getattr(calendar, 'vevent', [])
        todolist  = getattr(calendar, 'vtodo', [])
        
        # this is just a quick hack to get VTODO working, FIXME write
        # more readable table driven code to process VEVENTs and VTODOs
        for event in itertools.chain(eventlist, todolist):
            vtype = event.name
            if vtype == u'VEVENT':
                logger.debug("got VEVENT")
                pickKind = eventKind
            elif vtype == u'VTODO':
                logger.debug("got VTODO")
                pickKind = taskKind
            # See if we have a corresponding item already, or create one
            uuid = UUID(event.uid[0].value[:36]) # @@@MOR, stripping "-RID"
            # FIXME Why are we stripping to 36 characters?

            # hack until recurrence set can be stored in Chandler with one UUID
            # as it's modeled by iCalendar
            uuidMatchItem = self.itsView.findUUID(uuid)

            # For now we'll expand recurrence sets, first find attributes that
            # will be constant across the recurrence set.

            try:
                displayName = event.summary[0].value
            except AttributeError:
                displayName = ""

            try:
                description = event.description[0].value
            except AttributeError:
                description = None

            try:
                # FIXME assumes DURATION, not DATE-TIME
                reminderDelta = event.valarm[0].trigger[0].value
            except AttributeError:
                reminderDelta = None

            # RFC2445 allows VEVENTs without DTSTART, but it's hard to guess
            # what that would mean, so we won't catch an exception if there's no
            # dtstart.
            dtstart  = event.dtstart[0].value 
            
            try:
                duration = event.duration[0].value
            except AttributeError:
                # note that duration = dtend - dtstart isn't strictly correct
                # throughout a recurrence set, 1 hour differences might happen
                # around DST, but we'll ignore that corner case for now
                try:
                    duration = event.dtend[0].value - dtstart
                # FIXME no end time or duration, Calendar UI doesn't seem to
                # like events with no duration, so for now we'll set a dummy
                # duration of 1 hour
                except AttributeError:
                    # FIXME Nesting try/excepts is ugly.  Also, we're assuming
                    # DATE-TIMEs, not DATEs.
                    try:
                        duration = event.due[0].value - dtstart
                    except AttributeError:
                        if vtype == u'VEVENT':
                            duration = datetime.timedelta(hours=1)
                        elif vtype == u'VTODO':
                            duration = None
            # Iterate through recurrence set.  Infinite recurrence sets are
            # common, something has to be done to avoid infinite loops.
            # We'll arbitrarily limit ourselves to MAXRECUR recurrences.

            first = True
            for dt in itertools.islice(event.rruleset, MAXRECUR):
                # Hack to deal with recurrence set having a single UID but
                # needing to become multiple items with distinct UUIDs.  For the
                # first item, use the right UUID (and the matching Item if it
                # exists), for later items, create a new uuid.
                if first and uuidMatchItem is not None:
                    logger.debug("matched UUID")
                    eventItem = uuidMatchItem
                    countUpdated += 1
                else:
                    if not first:
                        uuid = UUID()
                    # @@@MOR This needs to use the new defaultParent framework
                    # to determine the parent
                    parent = self.findPath("//userdata")
                    eventItem = pickKind.instantiateItem(None, parent, uuid)
                    countNew += 1
                    
                logger.debug("eventItem is %s" % str(eventItem))
                              
                eventItem.displayName = displayName
                eventItem.startTime   = convertToMX(dt)
                if vtype == u'VEVENT':
                    eventItem.endTime = convertToMX(dt + duration)
                elif vtype == u'VTODO':
                    if duration is not None:
                        eventItem.dueDate = convertToMX(dt + duration)
                
                
                # I think Item.description describes a Kind, not userdata, so
                # I'm using DESCRIPTION <-> body  
                if description is not None:
                    eventItem.body = textKind.makeValue(description)
                    
                if reminderDelta is not None:
                    eventItem.reminderTime = convertToMX(dt + reminderDelta)

                item.add(eventItem)
                first = False
                logger.debug("Imported %s %s" % (eventItem.displayName,
                 eventItem.startTime))
                 
        logger.info("...iCalendar import of %d new items, %d updated" % \
         (countNew, countUpdated))

        return item

    def exportProcess(self, item, depth=0):
        # item is the whole collection or it may be a single event or task
        if isinstance(item, ItemCollection.ItemCollection):
            items = [item]
        else:
            items = item.contents
        
        cal = itemsToVObject(self.itsView, items)
        return cal.serialize()


class CalDAVFormat(ICalendarFormat):
    """Treat multiple events as different resources."""
    
    def fileStyle(self):
        return self.STYLE_DIRECTORY
