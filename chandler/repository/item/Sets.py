
__revision__  = "$Revision: 5185 $"
__date__      = "$Date: 2005-05-01 23:42:25 -0700 (Sun, 01 May 2005) $"
__copyright__ = "Copyright (c) 2003-2004 Open Source Applications Foundation"
__license__   = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

from itertools import izip

from chandlerdb.util.c import UUID, isuuid
from chandlerdb.item.c import Nil
from chandlerdb.item.ItemValue import ItemValue
from repository.item.Monitors import Monitors
from repository.item.Indexed import Indexed
from repository.item.Collection import Collection

class AbstractSet(ItemValue, Indexed):

    def __init__(self, view):

        super(AbstractSet, self).__init__()
        self._init_indexed()

        self._view = view
        self._otherName = None

    def __contains__(self, item, excludeMutating=False):
        raise NotImplementedError, "%s.__contains__" %(type(self))

    def sourceChanged(self, op, change, sourceOwner, sourceName, inner, other):
        raise NotImplementedError, "%s.sourceChanged" %(type(self))

    def __repr__(self):
        return self._repr_()

    def __getitem__(self, uuid):

        return self._view[uuid]

    def __nonzero__(self):

        index = self._anIndex()
        if index is not None:
            return len(index) > 0

        for i in self.iterkeys():
            return True

        return False

    def isEmpty(self):

        return not self

    def __iter__(self):

        index = self._anIndex()
        if index is not None:
            view = self._view
            return (view[key] for key in index)

        return self._itervalues()

    def itervalues(self):

        return self.__iter__()

    def _itervalues(self):

        raise NotImplementedError, "%s._itervalues" %(type(self))

    def iterkeys(self):

        index = self._anIndex()
        if index is not None:
            return index.__iter__()

        return self._iterkeys()

    # the slow way, via items, to be overridden by some implementations
    def _iterkeys(self):

        return (item.itsUUID for item in self)

    def __len__(self):

        index = self._anIndex()
        if index is not None:
            return len(index)

        return self._len()

    # the slow way, via keys, to be overridden by some implementations
    def _len(self):

        count = 0
        for key in self.iterkeys():
            count += 1

        return count

    def iterSources(self):

        raise NotImplementedError, "%s.iterSources" %(type(self))

    def iterInnerSets(self):

        raise NotImplementedError, "%s.iterInnerSets" %(type(self))

    def _iterSourceItems(self):

        for item, attribute in self.iterSources():
            yield item

    def _iterSources(self, source):

        if isinstance(source, AbstractSet):
            for source in source.iterSources():
                yield source
        else:
            yield (self._view[source[0]], source[1])

    def dir(self):
        """
        Debugging: print all items referenced in this set
        """
        for item in self:
            print item._repr_()

    def _getView(self):

        return self._view

    def _setView(self, view):

        self._view = view

    def _prepareSource(self, source):
        
        if isinstance(source, AbstractSet):
            return source._view, source
        elif isinstance(source, Collection):
            return source.itsView, (source.itsUUID, source.__collection__)
        elif isuuid(source[0]):
            return None, source
        else:
            return source[0].itsView, (source[0].itsUUID, source[1])

    def _sourceContains(self, item, source, excludeMutating=False):

        if item is None:
            return False

        if isinstance(source, AbstractSet):
            return item in source

        return getattr(self._view[source[0]],
                       source[1]).__contains__(item, excludeMutating)

    def _inspectSource(self, source, indent):

        if isinstance(source, AbstractSet):
            return source._inspect_(indent)
        
        return self._view[source[0]]._inspectCollection(source[1], indent)

    def _aSourceIndex(self, source):

        if isinstance(source, AbstractSet):
            return source._anIndex()

        return getattr(self._view[source[0]], source[1])._anIndex()

    def _iterSource(self, source):

        if isinstance(source, AbstractSet):
            for item in source:
                yield item
        else:
            for item in getattr(self._view[source[0]], source[1]):
                yield item

    def _iterSourceKeys(self, source):

        if isinstance(source, AbstractSet):
            return source.iterkeys()

        return getattr(self._view[source[0]], source[1]).iterkeys()

    def _sourceLen(self, source):

        if isinstance(source, AbstractSet):
            return len(source)

        try:
            return len(getattr(self._view[source[0]], source[1]))
        except AttributeError:
            print source, type(source), self, type(self)
            raise

    def _reprSource(self, source, replace):

        if isinstance(source, AbstractSet):
            return source._repr_(replace)
        
        if replace is not None:
            replaceItem = replace[source[0]]
            if replaceItem is not Nil:
                source = (replaceItem.itsUUID, source[1])

        return "(UUID('%s'), '%s')" %(source[0].str64(), source[1])

    def _setSourceItem(self, source, item, attribute, oldItem, oldAttribute):
        
        if isinstance(source, AbstractSet):
            source._setOwner(item, attribute)

        elif item is not oldItem:
            view = self._view
            if not view.isLoading():
                if item is None:
                    sourceItem = view.findUUID(source[0])
                    if sourceItem is not None: # was deleted
                        oldItem._unwatchSet(sourceItem, source[1], oldAttribute)
                else:
                    item._watchSet(view[source[0]], source[1], attribute)

    def _setSourceView(self, source, view):

        if isinstance(source, AbstractSet):
            source._setView(view)

    def _sourceChanged(self, source, op, change,
                       sourceOwner, sourceName, other):

        if isinstance(source, AbstractSet):
            op = source.sourceChanged(op, change, sourceOwner, sourceName,
                                      True, other)

        elif (sourceName == source[1] and
              (isuuid(sourceOwner) and sourceOwner == source[0] or
               sourceOwner is self._view[source[0]])):
            pass
        else:
            op = None

        if op == 'refresh':
            index = self._anIndex()
            if index is not None:
                sourceContains = self._sourceContains(other, source)
                indexContains = other.itsUUID in index

                if sourceContains and not indexContains:
                    op = 'add'
                elif not sourceContains and indexContains:
                    op = 'remove'

        return op

    def _collectionChanged(self, op, change, other, local=False):

        item = self._item
        attribute = self._attribute

        if item is not None:
            if change == 'collection':
                if op in ('add', 'remove'):
                    if not (local or self._otherName is None):
                        refs = self._view[other]._references
                        if op == 'add':
                            refs._setRef(self._otherName, item, attribute)
                        else:
                            refs._removeRef(self._otherName, item, True)
                            
                    if self._indexes:
                        dirty = False

                        if op == 'add':
                            for index in self._indexes.itervalues():
                                if other not in index:
                                    index.insertKey(other, index.getLastKey())
                                    dirty = True
                        else:
                            for index in self._indexes.itervalues():
                                if other in index:
                                    index.removeKey(other)
                                    dirty = True

                        if dirty:
                            self._setDirty(True)

                elif op == 'refresh':
                    pass

                else:
                    raise ValueError, op

            item._collectionChanged(op, change, attribute, other)

    def removeByIndex(self, indexName, position):

        raise TypeError, "%s contents are computed" %(type(self))

    def insertByIndex(self, indexName, position, item):

        raise TypeError, "%s contents are computed" %(type(self))

    def replaceByIndex(self, indexName, position, with):

        raise TypeError, "%s contents are computed" %(type(self))

    def _copy(self, item, attribute, copyPolicy, copyFn):

        # in the bi-ref case, set owner and value on item as needed
        # in non bi-ref case, Values sets owner and value on item

        otherName = self._otherName

        if otherName is not None:
            copy = item._references.get(attribute, Nil)
            if copy is not Nil:
                return copy

        policy = (copyPolicy or
                  item.getAttributeAspect(attribute, 'copyPolicy',
                                          False, None, 'copy'))

        replace = {}
        for sourceItem in self._iterSourceItems():
            if copyFn is not None:
                replace[sourceItem.itsUUID] = copyFn(item, sourceItem, policy)
            else:
                replace[sourceItem.itsUUID] = sourceItem

        copy = eval(self._repr_(replace))
        copy._setView(item.itsView)

        if otherName is not None:
            item._references[attribute] = copy
            copy._setOwner(item, attribute)

        return copy

    def _clone(self, item, attribute):

        clone = eval(self._repr_())
        clone._setView(item.itsView)

        return clone

    def _merge(self, value):

        if (type(value) is type(self) and
            list(value.iterSources()) == list(self.iterSources())):
            if self._indexes:
                self._invalidateIndexes()
            return True
            
        return False

    def _invalidateIndexes(self):

        super(AbstractSet, self)._invalidateIndexes()
        for inner in self.iterInnerSets():
            inner._invalidateIndexes()

    def _validateIndexes(self):

        super(AbstractSet, self)._validateIndexes()
        for inner in self.iterInnerSets():
            inner._validateIndexes()

    def _check(self, logger, item, attribute):

        return (super(AbstractSet, self)._check(logger, item, attribute) and
                self._checkIndexes(logger, item, attribute))

    def _setDirty(self, noMonitors=False):

        self._dirty = True
        item = self._item
        if item is not None:
            if self._otherName is None:
                item.setDirty(item.VDIRTY, self._attribute,
                              item._values, noMonitors)
            else:
                item.setDirty(item.RDIRTY, self._attribute,
                              item._references, noMonitors)

    @classmethod
    def makeValue(cls, string):
        return eval(string)

    @classmethod
    def makeString(cls, value):
        return value._repr_()

    # refs part

    def _setOwner(self, item, attribute):

        result = super(AbstractSet, self)._setOwner(item, attribute)

        if item is None:
            self._otherName = None
        else:
            self._otherName = item.itsKind.getOtherName(attribute, item, None)

        return result

    def _isRefs(self):
        return True
    
    def _isItem(self):
        return False
    
    def _isUUID(self):
        return False

    def _setRef(self, other, alias=None):

        self._item.add(other)
        self._view._notifyChange(self._collectionChanged,
                                 'add', 'collection', other.itsUUID,
                                 True)

    def _removeRef(self, other, noError=False):

        if not noError or other in self:
            self._item.remove(other)
            self._view._notifyChange(self._collectionChanged,
                                     'remove', 'collection', other.itsUUID,
                                     True)

    def _removeRefs(self):
        
        if self._otherName is not None:
            for item in self:
                item._references._removeRef(self._otherName, self._item)

    def _fillRefs(self):

        if self._otherName is not None:
            for item in self:
                item._references._setRef(self._otherName, self._item,
                                         self._attribute)

    def _unloadRef(self, item):
        pass

    def _unloadRefs(self):
        pass

    def _clearDirties(self):
        pass

    def _clear_(self):
        pass


class Set(AbstractSet):

    def __init__(self, source):

        view, self._source = self._prepareSource(source)
        super(Set, self).__init__(view)

    def __contains__(self, item, excludeMutating=False):

        if item is None:
            return False

        index = self._anIndex()
        if index is not None:
            return item.itsUUID in index

        return self._sourceContains(item, self._source, excludeMutating)

    def _itervalues(self):

        return self._iterSource(self._source)

    def _iterkeys(self):

        return self._iterSourceKeys(self._source)

    def _len(self):

        return self._sourceLen(self._source)

    def _repr_(self, replace=None):

        return "%s(%s)" %(type(self).__name__,
                          self._reprSource(self._source, replace))
        
    def _setOwner(self, item, attribute):

        oldItem, oldAttribute = super(Set, self)._setOwner(item, attribute)
        self._setSourceItem(self._source,
                            item, attribute, oldItem, oldAttribute)

        return oldItem, oldAttribute

    def _setView(self, view):

        super(Set, self)._setView(view)
        self._setSourceView(self._source, view)

    def sourceChanged(self, op, change, sourceOwner, sourceName, inner, other):

        if change == 'collection':
            op = self._sourceChanged(self._source, op, change,
                                     sourceOwner, sourceName, other)

        elif change == 'notification':
            if other not in self:
                op = None

        if not (inner is True or op is None):
            self._collectionChanged(op, change, other)

        return op

    def iterSources(self):

        return self._iterSources(self._source)

    def iterInnerSets(self):

        if isinstance(self._source, AbstractSet):
            yield self._source


class BiSet(AbstractSet):

    def __init__(self, left, right):

        view, self._left = self._prepareSource(left)
        view, self._right = self._prepareSource(right)

        super(BiSet, self).__init__(view)

    def _repr_(self, replace=None):

        return "%s(%s, %s)" %(type(self).__name__,
                              self._reprSource(self._left, replace),
                              self._reprSource(self._right, replace))
        
    def _setOwner(self, item, attribute):

        oldItem, oldAttribute = super(BiSet, self)._setOwner(item, attribute)
        self._setSourceItem(self._left, item, attribute, oldItem, oldAttribute)
        self._setSourceItem(self._right, item, attribute, oldItem, oldAttribute)

        return oldItem, oldAttribute

    def _setView(self, view):

        super(BiSet, self)._setView(view)
        self._setSourceView(self._left, view)
        self._setSourceView(self._right, view)

    def _op(self, leftOp, rightOp, other):

        raise NotImplementedError, "%s._op" %(type(self))

    def sourceChanged(self, op, change, sourceOwner, sourceName, inner, other):

        if change == 'collection':
            leftOp = self._sourceChanged(self._left, op, change,
                                         sourceOwner, sourceName, other)
            rightOp = self._sourceChanged(self._right, op, change,
                                          sourceOwner, sourceName, other)
            if op == 'refresh':
                op = self._op(leftOp, rightOp, other) or 'refresh'
            else:
                op = self._op(leftOp, rightOp, other)                

        elif change == 'notification':
            if other not in self:
                op = None

        if not (inner is True or op is None):
            self._collectionChanged(op, change, other)

        return op

    def iterSources(self):

        for source in self._iterSources(self._left):
            yield source
        for source in self._iterSources(self._right):
            yield source

    def iterInnerSets(self):

        if isinstance(self._left, AbstractSet):
            yield self._left
        if isinstance(self._right, AbstractSet):
            yield self._right

    def _inspect_(self, indent):

        return '\n%s' %('\n'.join([self._inspectSource(self._left, indent),
                                   self._inspectSource(self._right, indent)]))


class Union(BiSet):

    def __contains__(self, item, excludeMutating=False):
        
        if item is None:
            return False

        index = self._anIndex()
        if index is not None:
            return item.itsUUID in index

        return (self._sourceContains(item, self._left, excludeMutating) or
                self._sourceContains(item, self._right, excludeMutating))

    def _itervalues(self):

        left = self._left
        for item in self._iterSource(left):
            yield item
        for item in self._iterSource(self._right):
            if not self._sourceContains(item, left):
                yield item

    def _iterkeys(self):

        leftIndex = self._aSourceIndex(self._left)
        if leftIndex is not None:
            for key in leftIndex:
                yield key
            for key in self._iterSourceKeys(self._right):
                if key not in leftIndex:
                    yield key
        else:
            for item in self:
                yield item.itsUUID

    def _op(self, leftOp, rightOp, other):

        left = self._left
        right = self._right

        if (leftOp == 'add' and not self._sourceContains(other, right) or
            rightOp == 'add' and not self._sourceContains(other, left)):
            return 'add'
        elif (leftOp == 'remove' and not self._sourceContains(other, right) or
              rightOp == 'remove' and not self._sourceContains(other, left)):
            return 'remove'

        return None


class Intersection(BiSet):

    def __contains__(self, item, excludeMutating=False):
        
        if item is None:
            return False

        index = self._anIndex()
        if index is not None:
            return item.itsUUID in index

        return (self._sourceContains(item, self._left, excludeMutating) and
                self._sourceContains(item, self._right, excludeMutating))

    def _itervalues(self):

        left = self._left
        right = self._right

        for item in self._iterSource(left):
            if self._sourceContains(item, right):
                yield item

    def _iterkeys(self):

        rightIndex = self._aSourceIndex(self._right)
        if rightIndex is not None:
            for key in self._iterSourceKeys(self._left):
                if key in rightIndex:
                    yield key
        else:
            for item in self:
                yield item.itsUUID

    def _op(self, leftOp, rightOp, other):

        left = self._left
        right = self._right

        if (leftOp == 'add' and self._sourceContains(other, right) or
            rightOp == 'add' and self._sourceContains(other, left)):
            return 'add'
        elif (leftOp == 'remove' and self._sourceContains(other, right) or
              rightOp == 'remove' and self._sourceContains(other, left)):
            return 'remove'

        return None


class Difference(BiSet):

    def __contains__(self, item, excludeMutating=False):
        
        if item is None:
            return False

        index = self._anIndex()
        if index is not None:
            return item.itsUUID in index

        return (self._sourceContains(item, self._left, excludeMutating) and
                not self._sourceContains(item, self._right, excludeMutating))

    def _itervalues(self):

        left = self._left
        right = self._right

        for item in self._iterSource(left):
            if not self._sourceContains(item, right):
                yield item

    def _iterkeys(self):

        rightIndex = self._aSourceIndex(self._right)
        if rightIndex is not None:
            for key in self._iterSourceKeys(self._left):
                if key not in rightIndex:
                    yield key
        else:
            for item in self:
                yield item.itsUUID

    def _op(self, leftOp, rightOp, other):

        left = self._left
        right = self._right

        if (leftOp == 'add' and not self._sourceContains(other, right) or
            rightOp == 'remove' and self._sourceContains(other, left, True)):
            return 'add'

        elif (leftOp == 'remove' and not self._sourceContains(other, right) or
              rightOp == 'add' and self._sourceContains(other, left, True)):
            return 'remove'

        return None


class MultiSet(AbstractSet):

    def __init__(self, *sources):

        self._sources = []
        view = None
        for source in sources:
            view, source = self._prepareSource(source)
            self._sources.append(source)

        super(MultiSet, self).__init__(view)

    def _repr_(self, replace=None):

        return "%s(%s)" %(type(self).__name__,
                          ", ".join([self._reprSource(source, replace)
                                     for source in self._sources]))
        
    def _setOwner(self, item, attribute):

        oldItem, oldAttribute = super(MultiSet, self)._setOwner(item, attribute)
        for source in self._sources:
            self._setSourceItem(source, item, attribute, oldItem, oldAttribute)

        return oldItem, oldAttribute

    def _setView(self, view):

        super(MultiSet, self)._setView(view)
        for source in self._sources:
            self._setSourceView(source, view)

    def _op(self, ops, other):

        raise NotImplementedError, "%s._op" %(type(self))

    def sourceChanged(self, op, change, sourceOwner, sourceName, inner, other):

        if change == 'collection':
            ops = [self._sourceChanged(source, op, change,
                                       sourceOwner, sourceName, other)
                   for source in self._sources]
            if op == 'refresh':
                op = self._op(ops, other) or 'refresh'
            else:
                op = self._op(ops, other)

        elif change == 'notification':
            if other not in self:
                op = None

        if not (inner is True or op is None):
            self._collectionChanged(op, change, other)

        return op

    def iterSources(self):

        for source in self._sources:
            for src in self._iterSources(source):
                yield src

    def iterInnerSets(self):

        for source in self._sources:
            if isinstance(source, AbstractSet):
                yield source

    def _inspect_(self, indent):

        return '\n%s' %('\n'.join([self._inspectSource(source, indent)
                                   for source in self._sources]))


class MultiUnion(MultiSet):

    def __contains__(self, item, excludeMutating=False):

        if item is None:
            return False

        index = self._anIndex()
        if index is not None:
            return item.itsUUID in index

        for source in self._sources:
            if self._sourceContains(item, source, excludeMutating):
                return True

        return False

    def _iterkeys(self):

        sources = self._sources
        for source in sources:
            for key in self._iterSourceKeys(source):
                unique = True
                for src in sources:
                    if src is source:
                        break
                    if self._sourceContains(key, src):
                        unique = False
                        break
                if unique:
                    yield key

    def _itervalues(self):

        sources = self._sources
        for source in sources:
            for item in self._iterSource(source):
                unique = True
                for src in sources:
                    if src is source:
                        break
                    if self._sourceContains(item, src):
                        unique = False
                        break
                if unique:
                    yield item

    def _op(self, ops, other):

        sources = self._sources
        for op, source in izip(ops, sources):
            if op is not None:
                unique = True
                for src in sources:
                    if src is source:
                        continue
                    if self._sourceContains(other, src):
                        unique = False
                        break
                if unique:
                    return op

        return None


class MultiIntersection(MultiSet):

    def __contains__(self, item, excludeMutating=False):

        if item is None:
            return False

        index = self._anIndex()
        if index is not None:
            return item.itsUUID in index

        for source in self._sources:
            if not self._sourceContains(item, source, excludeMutating):
                return False

        return True

    def _iterkeys(self):

        sources = self._sources
        if sources:
            source = sources[0]
            for key in self._iterSourceKeys(source):
                everywhere = True
                for src in sources:
                    if src is source:
                        continue
                    if not self._sourceContains(key, src):
                        everywhere = False
                        break
                if everywhere:
                    yield key

    def _itervalues(self):

        sources = self._sources
        if sources:
            source = sources[0]
            for item in self._iterSource(source):
                everywhere = True
                for src in sources:
                    if src is source:
                        continue
                    if not self._sourceContains(item, src):
                        everywhere = False
                        break
                if everywhere:
                    yield item

    def _op(self, ops, other):

        sources = self._sources
        for op, source in izip(ops, sources):
            if op is not None:
                everywhere = True
                for src in sources:
                    if src is source:
                        continue
                    if not self._sourceContains(other, src):
                        everywhere = False
                        break
                if everywhere:
                    return op

        return None


class KindSet(Set):

    def __init__(self, kind, recursive=False):

        # kind is either a Kind item or an Extent UUID

        if isinstance(kind, UUID):
            self._extent = kind
        else:
            kind = kind.extent
            self._extent = kind.itsUUID

        self._recursive = recursive
        super(KindSet, self).__init__((kind, 'extent'))

    def __contains__(self, item, excludeMutating=False):

        if item is None:
            return False

        kind = self._view[self._extent].kind

        if isuuid(item):
            instance = self._view.find(item, False)
            if instance is None:
                return kind.isKeyForInstance(item, self._recursive)
            else:
                item = instance

        if self._recursive:
            contains = item.isItemOf(kind)
        else:
            contains = item.itsKind is kind

        if contains:
            if (excludeMutating and item.isMutating() and
                (item._futureKind is None or
                 not item._futureKind.isKindOf(kind))):
                return False
            return True
        
        return False

    def _sourceContains(self, item, source, excludeMutating=False):

        return item in self

    def _itervalues(self):

        return self._view[self._extent].iterItems(self._recursive)

    def _iterkeys(self):

        return self._view[self._extent].iterKeys(self._recursive)

    def _repr_(self, replace=None):

        return "%s(UUID('%s'), %s)" %(type(self).__name__,
                                      self._extent.str64(), self._recursive)
        
    def sourceChanged(self, op, change, sourceOwner, sourceName, inner, other):

        if change == 'collection':
            op = self._sourceChanged(self._source, op, change,
                                     sourceOwner, sourceName, other)

        elif change == 'notification':
            if other not in self:
                op = None

        if not (inner is True or op is None):
            self._collectionChanged(op, change, other)

        return op

    def _len(self):

        return AbstractSet._len(self)

    def iterSources(self):

        return iter(())

    def iterInnerSets(self):

        return iter(())

    def _inspect_(self, indent):

        return "\n%skind: %s" %('  ' * indent,
                                self._view[self._extent].kind.itsPath)


class FilteredSet(Set):

    def __init__(self, source, expr, attrs=None):

        super(FilteredSet, self).__init__(source)

        self.filterExpression = expr
        self.attributes = attrs
        self.filter = eval("lambda view, uuid: " + self.filterExpression)
    
    def _repr_(self, replace=None):

        return "%s(%s, \"\"\"%s\"\"\", %s)" %(type(self).__name__,
                                      self._reprSource(self._source, replace),
                                      self.filterExpression, self.attributes)

    def __contains__(self, item, excludeMutating=False):

        if item is None:
            return False

        index = self._anIndex()
        if index is not None:
            return item.itsUUID in index

        if self._sourceContains(item, self._source, excludeMutating):
            return self.filter(self._view, item.itsUUID)

        return False

    def _iterkeys(self):

        view = self._view
        for uuid in self._iterSourceKeys(self._source):
            if self.filter(view, uuid):
                yield uuid

    def _itervalues(self):

        view = self._view
        for item in self._iterSource(self._source):
            if self.filter(view, item.itsUUID):
                yield item

    def _len(self):

        count = 0
        for key in self._iterkeys():
            count += 1

        return count

    def _setOwner(self, item, attribute):

        oldItem, oldAttribute = super(FilteredSet, self)._setOwner(item,
                                                                   attribute)
        
        if item is not oldItem:
            if not self._view.isLoading():
                attrs = self.attributes
                if oldItem is not None:
                    if attrs:
                        for name, op in attrs:
                            Monitors.detach(oldItem, '_filteredItemChanged',
                                            op, name, oldAttribute)
                if item is not None:
                    if attrs:
                        for name, op in attrs:
                            Monitors.attach(item, '_filteredItemChanged',
                                            op, name, attribute)

        return oldItem, oldAttribute

    def sourceChanged(self, op, change, sourceOwner, sourceName, inner, other):

        if change == 'collection':
            op = self._sourceChanged(self._source, op, change,
                                     sourceOwner, sourceName, other)

        elif change == 'notification':
            if other not in self:
                op = None

        if op is not None:
            if change == 'collection':
                if op != 'refresh':
                    if not (op is None or self.filter(self._view, other)):
                        op = None

            if not (inner is True or op is None):
                self._collectionChanged(op, change, other)

        return op

    def itemChanged(self, other, attribute):

        if self._sourceContains(other, self._source):
            matched = self.filter(self._view, other)

            if self._indexes:
                contains = other in self._indexes.itervalues().next()
            else:
                contains = None
                
            if matched and not contains is True:
                self._collectionChanged('add', 'collection', other)
            elif not matched and not contains is False:
                self._collectionChanged('remove', 'collection', other)

    def _inspect_(self, indent):

        return "\n%sfilter: %s\n%s attrs: %s\n%s" %('  ' * indent, self.filterExpression, '  ' * indent, ', '.join(str(a) for a in self.attributes), self._inspectSource(self._source, indent))
