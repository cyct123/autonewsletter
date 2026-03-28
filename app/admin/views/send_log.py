# app/admin/views/send_log.py
from sqladmin import ModelView
from app.models.send_log import SendLog


class SendLogAdmin(ModelView, model=SendLog):
    name = "Send Log"
    name_plural = "Send Logs"
    icon = "fa-solid fa-paper-plane"

    column_list = [SendLog.id, SendLog.subscriber_id, SendLog.channel_type, SendLog.success, SendLog.sent_at]
    column_sortable_list = [SendLog.success, SendLog.sent_at]
    column_default_sort = [(SendLog.sent_at, True)]

    # Audit log — fully read-only
    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
