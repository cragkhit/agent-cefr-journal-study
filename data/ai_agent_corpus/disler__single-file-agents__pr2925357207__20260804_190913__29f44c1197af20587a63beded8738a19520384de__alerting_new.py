#!/usr/bin/env python3

"""
Alerting capability for the Atomic/Composable Architecture.
This capability combines notifications and validation modules.
"""

from typing import Dict, List, Optional, Tuple

from modules.notifications import (
    create_notification, get_user_notifications, mark_notification_as_read,
    mark_all_notifications_as_read, delete_notification, send_email_notification,
    send_sms_notification, create_alert
)
from modules.validation import (
    validate_required_fields, validate_email, validate_string_length
)

def send_user_alert(user_id: str, message: str, level: str = "info", 
                   email: Optional[str] = None, phone: Optional[str] = None,
                   additional_data: Optional[Dict] = None) -> Tuple[bool, Dict]:
    """
    Send an alert to a user through multiple channels.
    
    Args:
        user_id: The ID of the user to alert
        message: The alert message
        level: Alert level (info, warning, error)
        email: Optional email address to send the alert to
        phone: Optional phone number to send the alert to
        additional_data: Additional data for the alert
        
    Returns:
        Tuple of (success, result) with notification details
    """
    # Validate required fields
    missing_fields = validate_required_fields(
        {"user_id": user_id, "message": message},
        ["user_id", "message"]
    )
    
    if missing_fields:
        return False, {"error": f"Missing required fields: {', '.join(missing_fields)}"}
    
    # Validate message length
    if not validate_string_length(message, min_length=1, max_length=500):
        return False, {"error": "Message must be between 1 and 500 characters"}
    
    # Validate level
    valid_levels = ["info", "warning", "error"]
    if level not in valid_levels:
        return False, {"error": f"Level must be one of: {', '.join(valid_levels)}"}
    
    # Create the alert notification
    notification = create_alert(
        user_id=user_id,
        message=message,
        level=level,
        data=additional_data
    )
    
    # Send email if provided
    email_sent = False
    if email:
        if validate_email(email):
            subject = f"Alert: {level.capitalize()}"
            email_sent = send_email_notification(email, subject, message)
        else:
            return False, {"error": "Invalid email format"}
    
    # Send SMS if provided
    sms_sent = False
    if phone:
        sms_sent = send_sms_notification(phone, message)
    
    return True, {
        "notification": notification,
        "channels": {
            "in_app": True,
            "email": email_sent,
            "sms": sms_sent
        }
    }

def get_user_alerts(user_id: str, unread_only: bool = False, 
                   level: Optional[str] = None) -> List[Dict]:
    """
    Get alerts for a user with optional filtering.
    
    Args:
        user_id: The ID of the user
        unread_only: Whether to return only unread alerts
        level: Optional filter by alert level
        
    Returns:
        List of alert notifications
    """
    # Get all notifications for the user
    notifications = get_user_notifications(user_id, unread_only)
    
    # Filter to only alert type notifications
    alerts = [n for n in notifications if n["type"] == "alert"]
    
    # Filter by level if specified
    if level:
        alerts = [a for a in alerts if a["data"].get("level") == level]
    
    return alerts

def mark_alert_as_read(user_id: str, notification_id: str) -> bool:
    """
    Mark an alert as read.
    
    Args:
        user_id: The ID of the user
        notification_id: The ID of the notification
        
    Returns:
        True if the alert was marked as read, False otherwise
    """
    return mark_notification_as_read(user_id, notification_id)

def mark_all_alerts_as_read(user_id: str) -> int:
    """
    Mark all alerts for a user as read.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        Number of alerts marked as read
    """
    return mark_all_notifications_as_read(user_id)

def delete_user_alert(user_id: str, notification_id: str) -> bool:
    """
    Delete an alert.
    
    Args:
        user_id: The ID of the user
        notification_id: The ID of the notification
        
    Returns:
        True if the alert was deleted, False otherwise
    """
    return delete_notification(user_id, notification_id)

def send_system_notification(user_id: str, notification_type: str, 
                            data: Dict, email: Optional[str] = None) -> Tuple[bool, Dict]:
    """
    Send a system notification to a user.
    
    Args:
        user_id: The ID of the user
        notification_type: The type of notification (welcome, password_reset, new_login)
        data: Data for the notification template
        email: Optional email address to send the notification to
        
    Returns:
        Tuple of (success, result) with notification details
    """
    # Validate required fields
    missing_fields = validate_required_fields(
        {"user_id": user_id, "notification_type": notification_type},
        ["user_id", "notification_type"]
    )
    
    if missing_fields:
        return False, {"error": f"Missing required fields: {', '.join(missing_fields)}"}
    
    # Validate notification type
    valid_types = ["welcome", "password_reset", "new_login"]
    if notification_type not in valid_types:
        return False, {"error": f"Notification type must be one of: {', '.join(valid_types)}"}
    
    # Create the notification
    notification = create_notification(
        user_id=user_id,
        notification_type=notification_type,
        data=data
    )
    
    # Send email if provided
    email_sent = False
    if email:
        if validate_email(email):
            # Get the notification message
            message = notification["message"]
            subject = f"Notification: {notification_type.replace('_', ' ').title()}"
            email_sent = send_email_notification(email, subject, message)
        else:
            return False, {"error": "Invalid email format"}
    
    return True, {
        "notification": notification,
        "channels": {
            "in_app": True,
            "email": email_sent
        }
    }
