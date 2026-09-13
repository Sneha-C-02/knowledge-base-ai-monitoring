"""Register all ORM models on the application's shared SQLAlchemy metadata."""

from .activity_model import SystemActivityModel
from .article_model import ArticleModel
from .group_permission_model import GroupPermissionModel
from .instrument_memory_model import InstrumentMemoryModel
from .instrument_model import InstrumentModel
from .monitored_log_file_model import MonitoredLogFileModel
from .monitoring_model import MonitoringIssueModel, MonitoringRunModel
from .notification_model import SystemNotificationModel
from .permission_model import PermissionModel
from .user_group_model import UserGroupModel
from .user_model import UserModel

__all__ = [
    "SystemActivityModel", "ArticleModel", "GroupPermissionModel", "InstrumentMemoryModel",
    "InstrumentModel", "MonitoredLogFileModel", "MonitoringIssueModel", "MonitoringRunModel",
    "SystemNotificationModel", "PermissionModel", "UserGroupModel", "UserModel",
]
