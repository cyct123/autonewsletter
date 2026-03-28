# app/admin/views/source.py
from sqladmin import ModelView
from app.models.source import Source


class SourceAdmin(ModelView, model=Source):
    name = "Source"
    name_plural = "Sources"
    icon = "fa-solid fa-rss"

    column_list = [Source.id, Source.name, Source.url, Source.type, Source.active, Source.max_items_per_run]
    column_searchable_list = [Source.name, Source.url]
    column_sortable_list = [Source.name, Source.active]
    column_default_sort = [(Source.name, False)]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
