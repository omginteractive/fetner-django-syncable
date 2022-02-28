import pytest

from mock_django.signals import mock_signal_receiver
from mock import call
from syncable.base import Syncable
from syncable.signals import pre_item_sync, \
    post_item_sync, pre_collection_sync, post_collection_sync

from .base import make_source_collection, make_target_collection, user_mapping


source_collection = make_source_collection()
source_collection_2 = make_source_collection()
target_collection = make_target_collection()


class UserSyncable(Syncable):
    source = source_collection
    target = target_collection
    mapping = [user_mapping, ]
    unique_lookup_key = ('user_id', 'user_id')
    watch_key = 'last_updated'


@pytest.mark.django_db
def test_pre_collection_sync():
    syncable = UserSyncable()
    with mock_signal_receiver(pre_collection_sync) as \
            pre_collection_sync_receiver:
        syncable.sync()
        assert pre_collection_sync_receiver.call_args_list == \
            [call(signal=pre_collection_sync, sender=UserSyncable,
                  source=source_collection, target=target_collection)]
        assert pre_collection_sync_receiver.call_args_list != \
            [call(signal=pre_collection_sync, sender=UserSyncable,
                  source=source_collection_2, target=target_collection)]


@pytest.mark.django_db
def test_post_collection_sync():
    syncable = UserSyncable()
    with mock_signal_receiver(post_collection_sync) as \
            post_collection_sync_receiver:
        syncable.sync()
        assert post_collection_sync_receiver.call_args_list == \
            [call(signal=post_collection_sync, sender=UserSyncable,
                  source=source_collection, target=target_collection,
                  updated=syncable._updated)]
        assert post_collection_sync_receiver.call_args_list != \
            [call(signal=post_collection_sync, sender=UserSyncable,
                  source=source_collection_2, target=target_collection,
                  updated=syncable._updated)]


@pytest.mark.django_db
def test_pre_item_sync():
    syncable = UserSyncable()
    with mock_signal_receiver(pre_item_sync) as pre_item_sync_receiver:
        syncable.sync()
        source_item = source_collection.all()[0]
        target_item = target_collection.all()[0]
        target_item_2 = source_collection_2.all()[0]
        assert pre_item_sync_receiver.call_args_list[0] == \
            call(signal=pre_item_sync, sender=UserSyncable,
                 source=source_item, target=target_item)
        assert pre_item_sync_receiver.call_args_list[0] != \
            call(signal=pre_item_sync, sender=UserSyncable,
                 source=source_item, target=target_item_2)


@pytest.mark.django_db
def test_post_item_sync():
    syncable = UserSyncable()
    with mock_signal_receiver(post_item_sync) as post_item_sync_receiver:
        syncable.sync()
        source_item = source_collection.all()[0]
        target_item = target_collection.all()[0]
        target_item_2 = source_collection_2.all()[0]
        assert post_item_sync_receiver.call_args_list[0] == \
            call(signal=post_item_sync, sender=UserSyncable,
                 source=source_item, target=target_item)
        assert post_item_sync_receiver.call_args_list[0] != \
            call(signal=post_item_sync, sender=UserSyncable,
                 source=source_item, target=target_item_2)
