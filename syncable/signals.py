import django.dispatch

pre_item_sync = django.dispatch.Signal(providing_args=["source", "target"])
post_item_sync = django.dispatch.Signal(providing_args=["source", "target"])

pre_collection_sync = django.dispatch.Signal(providing_args=["source", "target"])
post_collection_sync = django.dispatch.Signal(providing_args=["source", "target", "updated"])
