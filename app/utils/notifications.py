from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.models.user import User, UserRole
from typing import Optional


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    type: str = "info",
    link: Optional[str] = None,
):
    """
    Create a single notification for a specific user.
    Call this from any router after an important action.
    """
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        link=link,
    )
    db.add(notification)
    # don't commit here — let the calling router commit everything together


def notify_all_hr_and_admins(
    db: Session,
    title: str,
    message: str,
    type: str = "info",
    link: Optional[str] = None,
):
    """
    Send a notification to every HR and Admin user.
    Used for things like: new employee added, leave submitted.
    """
    hr_and_admins = db.query(User).filter(
        User.role.in_([UserRole.admin, UserRole.hr])
    ).all()

    for user in hr_and_admins:
        create_notification(
            db=db,
            user_id=user.id,
            title=title,
            message=message,
            type=type,
            link=link,
        )


def notify_user(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    type: str = "info",
    link: Optional[str] = None,
):
    """Convenience wrapper for single user notifications."""
    create_notification(db, user_id, title, message, type, link)