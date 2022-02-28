django-syncable
---------------

Installation
===============


``pip install -e git@github.com:hzdg/django-syncable.git#egg=django-syncable``


Syncable
===============

Extend ``Syncable``, and set class attributes.

.. code-block:: python

    from syncable.base import Syncable, ModelCollection
    from syncable.registry import syncables

    def my_map(source):
        name_bits = source.get('name').split(' ')
        return {
            'first_name': name_bits[0],
            'last_name': name_bits[1],
            ...
        }

    class ContactSyncable(Syncable):
        source = ModelCollection(SalesForceContact.objects.all())
        target = ModelCollection(Contact.objects.all())
        mapping = [my_map, ]
        unique_lookup_key = ('pk', 'salesforce_id')
        watch_key = 'last_updated'

    syncables.register(ContactSyncable)


Mapper
===============

A Mapper is any callable which takes a source item as the first parameter and
returns a dictionary. The dict keys are used to lookup target values and replace
them with the mapped value. In the following example, the target item's
`first_name` key will be looked up and it's value will be set to Chris.

.. code-block:: python

    >> my_mapper(source)
    >> {
           'first_name': 'Chris',
           'last_name': 'McKenzie'
       }

Should we Sync?
===============

Syncable decides whether is should sync a source item with a target item by
calling the method `should_sync` on `Syncable`.

The default behavior is to store the value of the watched field in the `Record`
model. To change this behavior override should_sync.
