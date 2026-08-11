from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='General',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'permissions': (
                    ('basic_access', 'Can access this app (eigen koppelstatus)'),
                    ('auditor', 'Can view the link status of all members'),
                ),
                'managed': False,
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='Settings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('required_imports', models.TextField(blank=True, default='', help_text="Welke CharLink-koppelingen meetellen voor 'goed gekoppeld' — één id per regel, precies zoals op de pagina onder een kolomkop staat (bijv. memberaudit_default). Leeg = alles waar het lid recht op heeft.", verbose_name='Verplichte koppelingen')),
                ('member_states', models.TextField(blank=True, default='', help_text='Namen van AA-states die op het overzicht horen — één per regel of komma-gescheiden (bijv. Member). Leeg = elk account met een main, behalve Guest.', verbose_name='Alleen deze states')),
                ('include_guests', models.BooleanField(default=False, help_text='Aan: accounts in de state Guest ook op het overzicht zetten.', verbose_name='Guests meetellen')),
            ],
            options={
                'verbose_name': 'instellingen',
                'verbose_name_plural': 'instellingen',
                'permissions': (('manage_settings', 'Can manage Link Check settings'),),
                'default_permissions': (),
            },
        ),
    ]
