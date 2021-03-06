# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-07-23 00:36
from __future__ import unicode_literals

from django.db import migrations, models
import picklefield.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='PklModels',
            fields=[
                ('user_fbid', models.BigIntegerField(primary_key=True, serialize=False)),
                ('pkl_model', picklefield.fields.PickledObjectField(editable=False)),
                ('user_keywords', models.TextField(null=True)),
                ('text_corpus', models.FileField(upload_to=b'training_data')),
            ],
        ),
        migrations.CreateModel(
            name='Users',
            fields=[
                ('user_fbid', models.BigIntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=45)),
                ('propic_link', models.URLField(max_length=400)),
                ('articles', models.TextField(null=True)),
            ],
        ),
    ]
