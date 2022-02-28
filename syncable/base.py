import inspect

from django.core.exceptions import ImproperlyConfigured
from django.db import models

from .exceptions import MultipleItemsReturned, LookupDoesNotExist
from .models import Record
from .signals import pre_item_sync, \
    post_item_sync, pre_collection_sync, post_collection_sync
from .utils import resolve_lookup


class Item(object):
    """
    Item creates a standard api around the data synced. This allows for a
    uniform api so the Syncable class need to know nothing about the
    implementation of the data. It could be a model instance, a dictionary, a
    tuple, ect and syncable will treat it the same.

    Syncable supports dict items and model items out of the box but you can
    easily extend it to support other data types. Syncable Item must have a
    name, a way to get, set and update the data and a get_fields method
    """
    @property
    def name(self):
        # A naive implementation
        import md5
        return md5.md5(''.join(self.data.keys())).hexdigest()

    def get_fields(self):
        raise NotImplementedError

    def __init__(self, data_item):
        # TODO: should item have a `_updated` property?
        self.data = data_item

    def update(self, mapped):
        raise NotImplementedError

    def get(self, key, default=None, *args, **kwargs):
        try:
            return resolve_lookup(key, self.data)
        except LookupDoesNotExist as e:
            if default is not None:
                return default
            else:
                raise e

    def set(self, key, value):
        raise NotImplementedError


class Collection(object):
    """
    Collection assembles a list of Items.
    TODO: can Collection be generic too?
    """
    item_class = Item

    def __init__(self, data_collection, *args, **kwargs):
        """
        Args:
            data_collection: input data.
                example:

                [{'city': 'San Francisco', ...}, ...]

            kwargs:
                create_new: optional named param specifies if a new target item
                    should be created if it doesn't already exist. default True
        """
        self.create_new = kwargs.get('create_new', True)
        if 'item_class' in kwargs:
            self.item_class = kwargs.get('item_class')
        self.build_collection(data_collection)

    @property
    def name(self):
        # A naive implementation
        return '-'.join([str(data.__hash__()) for data in self.all()])

    def all(self):
        return self.data

    def get(self, lookup_key, unique_identifier, *args, **kwargs):
        results = list(filter(lambda x: x.get(lookup_key, '') == unique_identifier, self.data))
        if len(results) == 1:
            return results[0]
        elif len(results) > 1:
            raise MultipleItemsReturned('get() on %s collection returned more '
                'than one Item when filtering %s for %s. -- it returned %s!'
                % (self.name, lookup_key, unique_identifier, len(results)))
        # Result set is empty
        # Should we create a new item?
        if not self.create_new:
            return None

        lookups = {lookup_key: unique_identifier}
        item = self.create_item(lookups)
        self.data.append(item)
        return item

    def create_item(self, lookup):
        return self.item_class(lookup)

    def commit(self):
        pass

    def build_collection(self, data_collection):
        self._raw = data_collection
        self.data = [self.item_class(data_item)
                     for data_item in data_collection]

    def __len__(self):
        return len(self.data)


class DictItem(Item):
    def get_fields(self):
        return self.data.keys()

    def update(self, mapping):
        self.data.update(mapping)

    def set(self, key, value):
        self.data[key] = value


class ModelItem(Item):
    @property
    def name(self):
        return "%s-%s" % (self.data.__class__.__name__, self.data.id)

    def update(self, mapping):
        for key, value in mapping.items():
            self.set(key, value)

    def set(self, key, value):
        setattr(self.data, key, value)


class ModelCollection(Collection):
    """
    >>> model_collection = ModelCollection(MyModel)
    or
    >>> model_collection = ModelCollection(
            MyModel.objects.filter(first_name='Chris'))
    """
    item_class = ModelItem

    @property
    def name(self):
        model = self.get_model()
        return model.__name__

    def get_model(self):
        return self._model

    def commit(self):
        for item in self.data:
            try:
                item.data.save()
            except Exception as e:
                print('Error during sync, skipping.', e)

    def build_collection(self, data):
        if inspect.isclass(data) and issubclass(data, models.Model):
            queryset = data._default_manager.all()
            self._model = data
        elif isinstance(data, models.query.QuerySet):
            queryset = data
            self._model = data.model
            if hasattr(queryset, '_clone'):
                queryset = queryset._clone()
        else:
            raise ImproperlyConfigured("needs to be a model or queryset")

        return super(ModelCollection, self).build_collection(queryset)

    def create_item(self, lookup):
        return self.item_class(self._create_object(lookup))

    def _create_object(self, lookup):
        """
        create a new instance of a model. Note: that instance hasn't been saved
        yet.
        """
        model = self.get_model()
        obj = model(**lookup)
        return obj


class ModelSource(ModelCollection):
    """
    Almost pointless. Stops you from saving the source models on accident.
    """
    def commit(self):
        raise Exception('Unable to save source model.'
                        ' This is a safety precaution')


class ModelTarget(ModelCollection):
    pass


class RecordCheckMixin(object):
    """
    Simple comparison of the value of a target key.

    Args:
        watch_key: target key to watch for changes. example: last_updated
    Returns:
        Boolean
    value from a target item.
    """
    def should_sync(self, source_item, target_item):
        record, created = Record.objects.get_or_create(
            key=self._syncable_key(source_item))
        if record.value == str(source_item.get(self.watch_key)):
            return False
        else:
            return True

    def post_item_sync(self, source_item, target_item):
        self.update_record(source_item, target_item)

    def update_record(self, source_item, target_item):
        record = Record.objects.get(key=self._syncable_key(source_item))
        record.value = str(source_item.get(self.watch_key))
        record.save()


class BaseSyncable(object):

    def sync(self, *args, **kwargs):
        """
        gets the list of source items, iterates over to find analog in the
        target set and updates the target if needed. TODO: add complete sync
        transactional support? TODO: add signal
        """
        self._updated = []
        lookup_key = self.get_target_lookup_key()
        self._force = kwargs.get('force', False)

        # get the list of source items
        source = self.get_source()
        pre_collection_sync.send(
            sender=self.__class__, source=source, target=self.target)
        for source_item in source.all():
            # unique_identifier is a value which is common between the source
            # and target
            unique_identifier = self.get_unique_lookup_value(source_item)
            # get
            target_item = self.target.get(lookup_key, unique_identifier)
            if target_item is None:
                continue

            # determine if target should sync with source
            if self.should_sync(source_item, target_item) or self._force:
                # Hook: before sync
                pre_item_sync.send(sender=self.__class__,
                                   source=source_item, target=target_item)
                self.pre_item_sync(source_item, target_item)
                # Update the target
                updated_target_item = self.update_target(
                    source_item, target_item, *args, **kwargs)
                self._updated.append(updated_target_item)
                # Hook: after sync
                self.post_item_sync(source_item, target_item)
                post_item_sync.send(sender=self.__class__,
                                    source=source_item, target=target_item)

        post_collection_sync.send(
            sender=self.__class__, source=source, target=self.target,
            updated=self._updated)
        return self.target

    def update_target(self, source_item, target_item, *args, **kwargs):
        map_dict = {}
        for mapping in self.mapping:
            map_dict.update(mapping(source_item))

        target_item.update(map_dict)
        return target_item

    def get_source(self):
        """
        Return source collection of source items which will be iterated over
        and synced into analogous target items
        """
        return self.source

    def set_source(self, source):
        self.source = source

    def get_unique_lookup_value(self, source_item):
        """
        In order for the data to sync with the model we need a
        consistent unqiue identifier. This could be the pk,
        tweet id, istagram media id, guid, ect. It's this value
        that is used to query the source and determine whether
        to update or add a new item.
        """
        return source_item.get(self.get_source_lookup_key())

    def should_sync(self, source, target):
        """
        Called for each item before it's synced.

        If it returns True, the item is synced and if it returns False, the item
        won't be syncable and Sycnable will continue on to the next item.
        """
        raise NotImplementedError

    def get_source_lookup_key(self):
        return self._get_lookup_key(self.unique_lookup_key[0], 'source')

    def get_target_lookup_key(self):
        return self._get_lookup_key(self.unique_lookup_key[1], 'target')

    def serialize_unique_lookup(self, unique_lookup):
        return unique_lookup

    def pre_item_sync(self, source_item, target_item):
        """
        Hook called before sync

        TODO: Should I remove this? Feels redundant to have this and the signal.
        But it might be nice to have the ability to define this behavior on the
        Syncable class...
        """
        pass

    def post_item_sync(self, source_item, target_item):
        """
        Hook called after

        TODO: Should I remove this? Feels redundant to have this and the signal.
        But it might be nice to have the ability to define this behavior on the
        Syncable class...
        """
        pass

    def _syncable_key(self, source_item, *args, **kwargs):
        return "%s__%s__%s" % (
            self.source.name,
            self.target.name,
            self.serialize_unique_lookup(
                self.get_unique_lookup_value(source_item))
        )

    def _get_lookup_key(self, lookup_key, kind):
        if lookup_key == '':
            raise Exception('%s key can\'t be an empty string' % kind)
        return lookup_key


class Syncable(RecordCheckMixin, BaseSyncable):
    # unique_lookup_key = ('source_unique_key', 'target_unique_key')
    unique_lookup_key = ('id', 'id')
    watch_key = 'last_updated'
