from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name="NoteModel",
            fields=[
                ("id", fields.IntField(primary_key=True)),
                ("text", fields.CharField(max_length=200)),
            ],
            options={"table": "notes", "app": "models", "pk_attr": "id"},
        ),
    ]
