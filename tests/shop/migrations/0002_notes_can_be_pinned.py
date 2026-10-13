from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("models", "0001_initial")]

    operations = [
        ops.AddField(
            model_name="NoteModel",
            name="pinned",
            field=fields.BooleanField(default=False, db_default=False),
        ),
    ]
