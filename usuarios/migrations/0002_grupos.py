from django.db import migrations


def criar_grupos(apps, schema_editor):
    Grupo = apps.get_model('auth', 'Group')
    for nome in ('Alunos', 'Professores', 'Coordenadores'):
        Grupo.objects.using(schema_editor.connection.alias).get_or_create(name=nome)


class Migration(migrations.Migration):
    dependencies = [('usuarios', '0001_initial')]
    operations = [migrations.RunPython(criar_grupos, migrations.RunPython.noop)]
