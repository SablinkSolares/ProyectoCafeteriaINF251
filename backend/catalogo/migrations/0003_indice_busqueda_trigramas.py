
from django.db import migrations


def instalar_trigramas(apps, schema_editor):

    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute(
        "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
    )

    schema_editor.execute("""
        CREATE INDEX IF NOT EXISTS producto_nombre_trgm_idx
        ON catalogo_producto
        USING GIN (nombre gin_trgm_ops);
    """)


def eliminar_trigramas(apps, schema_editor):

    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute("""
        DROP INDEX IF EXISTS producto_nombre_trgm_idx;
    """)


class Migration(migrations.Migration):

    dependencies = [
    ("catalogo", "0002_producto_producto_categoria_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(
            instalar_trigramas,
            eliminar_trigramas
        ),
    ]
