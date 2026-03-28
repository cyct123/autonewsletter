# app/admin/views/subscriber.py
from sqladmin import ModelView
from app.models.subscriber import Subscriber


class SubscriberAdmin(ModelView, model=Subscriber):
    name = "Subscriber"
    name_plural = "Subscribers"
    icon = "fa-solid fa-users"

    column_list = [Subscriber.id, Subscriber.identifier, Subscriber.channel_type, Subscriber.active, Subscriber.created_at]
    column_searchable_list = [Subscriber.identifier, Subscriber.channel_type]
    column_sortable_list = [Subscriber.channel_type, Subscriber.active, Subscriber.created_at]
    column_default_sort = [(Subscriber.created_at, True)]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
