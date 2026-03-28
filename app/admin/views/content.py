# app/admin/views/content.py
from sqladmin import ModelView
from app.models.content import Content


class ContentAdmin(ModelView, model=Content):
    name = "Content"
    name_plural = "Contents"
    icon = "fa-solid fa-newspaper"

    column_list = [Content.id, Content.title, Content.quality_score, Content.status, Content.processed_at]
    column_searchable_list = [Content.title]
    column_sortable_list = [Content.quality_score, Content.processed_at]
    column_default_sort = [(Content.processed_at, True)]

    # Pipeline generates content — no manual creation or editing
    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True
