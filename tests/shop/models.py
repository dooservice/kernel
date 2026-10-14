from tortoise import fields
from tortoise.models import Model


class NoteModel(Model):
    id = fields.IntField(primary_key=True)
    text = fields.CharField(max_length=200)
    pinned = fields.BooleanField(default=False, db_default=False)

    class Meta(Model.Meta):
        table = "notes"
