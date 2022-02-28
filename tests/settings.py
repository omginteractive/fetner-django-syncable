SECRET_KEY = 'SEKRIT'

INSTALLED_APPS = ('syncable', 'tests',)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': './test.db',
    }
}
