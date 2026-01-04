"""pg_trgm 확장 활성화 마이그레이션.

한글 부분 일치 검색을 위한 PostgreSQL pg_trgm 확장을 활성화한다.
"""

from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0001_initial"),
    ]

    operations = [
        TrigramExtension(),
    ]
