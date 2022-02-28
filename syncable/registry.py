from .exceptions import NotRegistered, AlreadyRegistered
from .base import Syncable


class SyncableRegistry(object):
    """
    Registry for syncables. Provides a way to register, get, unregister and run
    syncables.

    The syncables are stored in a queue. `default` if not specified.

    Example:
    syncables.py
    >>> from syncable.registry import syncables
    >>> # define MySyncable
    >>> syncables.register(MySyncable, queues=['queue-name'])
    ---
    >>> syncables.run(queues=['queue-name'])

    """
    def __init__(self, *args, **kwargs):
        self._registry = {}

    def run(self, queues=['default'], force=False):
        for queue in queues:
            for updatable in self._get_queue(queue):
                u = updatable()
                target = u.sync(force=force)
                target.commit()

    def run_all(self, force=False):
        self.run(self._registry.keys(), force=force)

    def register(self, syncable_or_iterable, queues=['default']):
        if not isinstance(syncable_or_iterable, list):
            syncable_or_iterable = [syncable_or_iterable]

        for queue in queues:
            if queue not in self._registry:
                self._registry[queue] = []

            for syncable in syncable_or_iterable:
                if syncable in self._get_queue(queue):
                    raise AlreadyRegistered(
                        'The syncable %s is already registered in %s queue'
                        % (syncable.__name__, queue))

                if not issubclass(syncable, Syncable):
                    raise Exception('%s is not a syncable' % syncable)

                self._get_queue(queue).append(syncable)

    def unregister(self, syncable_or_iterable, queues=None):
        if not isinstance(syncable_or_iterable, list):
            syncable_or_iterable = [syncable_or_iterable]

        if queues is None:
            queues = self._registry.keys()

        for syncable in syncable_or_iterable:
            for queue in queues:
                if syncable not in self._get_queue(queue):
                    raise NotRegistered(
                        'The syncable %s is not registered in %s queue' %
                        (syncable.__name__, queue))
                self._get_queue(queue).remove(syncable)

    def get(self, queue):
        return self._get_queue(queue)

    def _get_queue(self, name):
        if name in self._registry:
            return self._registry[name]
        else:
            raise Exception('queue %s doesn\'t exist' % name)


syncables = SyncableRegistry()
