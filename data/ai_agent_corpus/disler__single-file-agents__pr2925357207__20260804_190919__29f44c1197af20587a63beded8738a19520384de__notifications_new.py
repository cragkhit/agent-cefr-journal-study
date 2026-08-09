#!/usr/bin/env python3

"""
Notifications module for the Atomic/Composable Architecture.
This module provides atomic notification utilities.
"""

import time
from typing import Dict, List, Optional

# In-memory notification store for demonstration purposes
NOTIFICATION_STORE: Dict[str, List[Dict]] = {}

# Notification templates
TEMPLATES = {
    "welcome": "Welcome, {username}! Thank you for joining our platform.",
    "password_reset": "Your password has been reset. If you didn't request this, please contact support.",
    "new_login": "New login detected from {device} at {location}.",
    "alert": "{message}"
}

def create_notification(user_id: str, notification_type: str, data: Dict, 
                       is_read: bool = False) -> Dict:
    """
    Create a notification for a user.
    
    Args:
        user_id: The ID of the user to notify
        notification_type: The type of notification
        data: Data to include in the notification
        is_read: Whether the notification has been read
        
    Returns:
        The created notification
    """
    if user_id not in NOTIFICATION_STORE:
        NOTIFICATION_STORE[user_id] = []
    
    # Get template or use alert template as fallback
    template = TEMPLATES.get(notification_type, TEMPLATES["alert"])
    
    # Format message with provided data
    try:
        message = template.format(**data)
    except KeyError:
        # Fallback if template variables are missing
        message = f"Notification: {notification_type}"
    
    notification = {
        "id": str(len(NOTIFICATION_STORE[user_id]) + 1),
        "user_id": user_id,
        "type": notification_type,
        "message": message,
        "data": data,
        "is_read": is_read,
        "created_at": time.time()
    }
    
    NOTIFICATION_STORE[user_id].append(notification)
    return notification

def get_user_notifications(user_id: str, unread_only: bool = False) -> List[Dict]:
    """
    Get notifications for a user.
    
    Args:
        user_id: The ID of the user
        unread_only: Whether to return only unread notifications
        
    Returns:
        List of notifications
    """
    if user_id not in NOTIFICATION_STORE:
        return []
    
    if unread_only:
        return [n for n in NOTIFICATION_STORE[user_id] if not n["is_read"]]
    
    return NOTIFICATION_STORE[user_id]

def mark_notification_as_read(user_id: str, notification_id: str) -> bool:
    """
    Mark a notification as read.
    
    Args:
        user_id: The ID of the user
        notification_id: The ID of the notification
        
    Returns:
        True if the notification was marked as read, False otherwise
    """
    if user_id not in NOTIFICATION_STORE:
        return False
    
    for notification in NOTIFICATION_STORE[user_id]:
        if notification["id"] == notification_id:
            notification["is_read"] = True
            return True
    
    return False

def mark_all_notifications_as_read(user_id: str) -> int:
    """
    Mark all notifications for a user as read.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        Number of notifications marked as read
    """
    if user_id not in NOTIFICATION_STORE:
        return 0
    
    count = 0
    for notification in NOTIFICATION_STORE[user_id]:
        if not notification["is_read"]:
            notification["is_read"] = True
            count += 1
    
    return count

def delete_notification(user_id: str, notification_id: str) -> bool:
    """
    Delete a notification.
    
    Args:
        user_id: The ID of the user
        notification_id: The ID of the notification
        
    Returns:
        True if the notification was deleted, False otherwise
    """
    if user_id not in NOTIFICATION_STORE:
        return False
    
    for i, notification in enumerate(NOTIFICATION_STORE[user_id]):
        if notification["id"] == notification_id:
            del NOTIFICATION_STORE[user_id][i]
            return True
    
    return False

def send_email_notification(email: str, subject: str, message: str) -> bool:
    """
    Send an email notification (mock implementation).
    
    Args:
        email: The recipient's email address
        subject: The email subject
        message: The email message
        
    Returns:
        True if the email was sent successfully (always True in this mock)
    """
    # In a real application, this would send an actual email
    print(f"[EMAIL] To: {email}, Subject: {subject}")
    print(f"[EMAIL] Message: {message}")
    return True

def send_sms_notification(phone_number: str, message: str) -> bool:
    """
    Send an SMS notification (mock implementation).
    
    Args:
        phone_number: The recipient's phone number
        message: The SMS message
        
    Returns:
        True if the SMS was sent successfully (always True in this mock)
    """
    # In a real application, this would send an actual SMS
    print(f"[SMS] To: {phone_number}")
    print(f"[SMS] Message: {message}")
    return True

def create_alert(user_id: str, message: str, level: str = "info", 
                data: Optional[Dict] = None) -> Dict:
    """
    Create an alert notification.
    
    Args:
        user_id: The ID of the user to alert
        message: The alert message
        level: Alert level (info, warning, error)
        data: Additional data for the alert
        
    Returns:
        The created notification
    """
    if data is None:
        data = {}
    
    data["message"] = message
    
    notification = create_notification(
        user_id=user_id,
        notification_type="alert",
        data={
            **data,
            "level": level
        }
    )
    
    return notification
