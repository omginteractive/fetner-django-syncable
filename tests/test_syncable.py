import pytest

from syncable.registry import syncables
from syncable.base import Syncable
from syncable.exceptions import MultipleItemsReturned
from syncable.mappers import ModelMapper

from .base import make_source_collection, make_target_collection, user_mapping, user_mapping_2


source_collection = make_source_collection()
target_collection = make_target_collection()


class UserSyncable(Syncable):
    source = source_collection
    target = target_collection
    mapping = [user_mapping, user_mapping_2, ]
    unique_lookup_key = ('user_id', 'user_id')
    watch_key = 'last_updated'

syncables.register(UserSyncable, queues=['test_sync'])


def test_model_mapper_required_model():
    with pytest.raises(ValueError):
        class TestModelMapper(ModelMapper):
            pass
        TestModelMapper()


def test_collection():
    source_collection = make_source_collection()
    item = source_collection.get('name.first', 'Chris')
    with pytest.raises(MultipleItemsReturned):
        source_collection.get('user_id', 124)
    assert len(source_collection) == 3
    new_item = source_collection.get('item_id', 124)
    assert new_item
    assert len(source_collection) == 4
    assert item.get('name.first') == 'Chris'
    assert source_collection.name


def test_item():
    source_collection = make_source_collection()
    item = source_collection.get('name.first', 'Chris')
    assert item.get('city') == 'Washington'
    item.update({'city': 'New York'})
    assert item.get('city') == 'New York'


@pytest.mark.django_db
def test_sync():
    target_item = target_collection.get('user_id', 123)
    assert target_item.get('city') == 'New York'
    assert target_item.get('state') == 'NY'
    syncables.run(['test_sync'])
    assert target_item.get('city') == 'Washington'
    assert target_item.get('state') == 'VT'
