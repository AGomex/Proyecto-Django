# Generated by Django 5.1.2 on 2024-11-05 17:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Ticket', '0003_ticket_secuencia'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='aceptado',
            field=models.BooleanField(default=False),
        ),
    ]
