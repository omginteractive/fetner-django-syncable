from .exceptions import LookupDoesNotExist


def resolve_lookup(value, context):
    """
    Based on _resolve_lookup django/template/loaders/base.py:~745
    """
    current = context
    lookups = value.split('.')
    try:  # catch-all for silent variable failures
        for bit in lookups:
            try:  # dictionary lookup
                current = current[bit]
            except (TypeError, AttributeError, KeyError, ValueError):
                try:  # attribute lookup
                    current = getattr(current, bit)
                except (TypeError, AttributeError):
                    try:  # list-index lookup
                        current = current[int(bit)]
                    except (IndexError,  # list index out of range
                            ValueError,  # invalid literal for int()
                            KeyError,    # current is a dict without `int(bit)` key
                            TypeError):  # unsubscriptable object
                        raise LookupDoesNotExist("Failed lookup for key "
                                                 "[%s] in %r",
                                                 (bit, current))  # missing attribute

            if callable(current):
                try: # method call (assuming no args required)
                    current = current()
                except TypeError: # arguments *were* required
                    # GOTCHA: This will also catch any TypeError
                    # raised in the function itself.
                    raise LookupDoesNotExist("Failed lookup for key "
                                             "[%s] in %r",
                                             (bit, current))  # missing attribute
    except Exception as e:
        raise e

    return current


def autodiscover():
    """
    Auto-discover INSTALLED_APPS admin.py modules and fail silently when
    not present. This forces an import on them to register any admin bits they
    may want.
    """

    import copy
    from django.conf import settings
    from importlib import import_module
    from django.utils.module_loading import module_has_submodule
    from .registry import syncables

    for app in settings.INSTALLED_APPS:
        mod = import_module(app)
        # Attempt to import the app's admin module.
        try:
            before_import_registry = copy.copy(syncables._registry)
            import_module('%s.syncables' % app)
        except:
            # Reset the model registry to the state before the last import as
            # this import will have to reoccur on the next request and this
            # could raise NotRegistered and AlreadyRegistered exceptions
            # (see #8245).
            syncables._registry = before_import_registry

            # Decide whether to bubble up this error. If the app just
            # doesn't have an admin module, we can ignore the error
            # attempting to import it, otherwise we want it to bubble up.
            if module_has_submodule(mod, 'syncables'):
                raise
