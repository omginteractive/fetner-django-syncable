from django.db import models


class Record(models.Model):
    key = models.CharField(max_length=255)
    value = models.TextField(default='')

    def __unicode__(self):
        return "key: %s, value: %s" % (self.key, self.value)
