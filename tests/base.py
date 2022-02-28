import datetime

from syncable.registry import syncables
from syncable.base import Collection, DictItem, Syncable
from syncable.mappers import Mapper, SyncableDataField


def make_source_collection():
    return Collection([
        {
            'user_id': 123,
            'name': {
                'first': 'Chris',
                'last': 'McKenzie'
            },
            'city': 'Washington',
            'state': 'DC',
            'last_updated': datetime.datetime(year=2014, month=11, day=1)
        },
        {
            'user_id': 124,
            'name': {
                'first': 'Double',
                'last': 'Trouble'
            },
            'city': 'Somewhere',
            'state': 'MD',
            'last_updated': datetime.datetime(year=2014, month=1, day=1)
        },
        {
            'user_id': 124,
            'name': {
                'first': 'Double',
                'last': 'Trouble'
            },
            'city': 'Somewhere',
            'state': 'MD',
            'last_updated': datetime.datetime(year=2014, month=1, day=1)
        },
    ], item_class=DictItem)


def make_target_collection():
    return Collection([{
        'user_id': 123,
        'name': 'Chris McKenzie',
        'city': 'New York',
        'state': 'NY',
        'last_updated': datetime.datetime(year=2014, month=12, day=1), }],
        item_class=DictItem)


source_collection = make_source_collection()
target_collection = make_target_collection()


def name_mapper(source):
    return "%s %s" % (source.get('name.first'), source.get('name.last'))


class UserMapper(Mapper):
    name = SyncableDataField(source=name_mapper)
    city = SyncableDataField(source='city')
    last_updated = SyncableDataField(source='last_updated')


def user_mapping(source):
    return {
        'name': "%s %s" % (source.get('name.first'), source.get('name.last')),
        'city': source.get('city'),
        'last_updated': source.get('last_updated')
    }


def user_mapping_2(source):
    return {
        'state': 'VT'
    }


class UserSyncable(Syncable):
    source = source_collection
    target = target_collection
    mapping = [user_mapping, ]
    unique_lookup_key = ('user_id', 'user_id')
    watch_key = 'last_updated'

syncables.register(UserSyncable, queues=['test_sync'])
