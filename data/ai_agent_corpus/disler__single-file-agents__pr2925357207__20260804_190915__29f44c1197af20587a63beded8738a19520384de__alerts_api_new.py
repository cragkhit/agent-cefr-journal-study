#!/usr/bin/env python3

"""
Alerts API endpoints for the Atomic/Composable Architecture.
This module combines alerting capability with HTTP endpoints.
"""

from typing import Dict, List, Optional

from capabilities.alerting import (
    send_user_alert, get_user_alerts, mark_alert_as_read,
    mark_all_alerts_as_read, delete_user_alert, send_system_notification
)
from capabilities.user_management import validate_user_token

class AlertsAPI:
    """API endpoints for alerts management."""
    
    @staticmethod
    def send_alert(token: str, message: str, level: str = "info", 
                  email: Optional[str] = None, phone: Optional[str] = None,
                  additional_data: Optional[Dict] = None) -> Dict:
        """
        Send an alert to a user.
        
        Args:
            token: Authentication token
            message: The alert message
            level: Alert level (info, warning, error)
            email: Optional email address to send the alert to
            phone: Optional phone number to send the alert to
            additional_data: Additional data for the alert
            
        Returns:
            Response with success status and alert details or error message
        """
        # Validate token
        success, user_data = validate_user_token(token)
        if not success:
            return {
                "status": "error",
                "message": "Invalid or expired token",
                "data": None
            }
        
        # Send alert
        success, result = send_user_alert(
            user_id=user_data["id"],
            message=message,
            level=level,
            email=email,
            phone=phone,
            additional_data=additional_data
        )
        
        if success:
            return {
                "status": "success",
                "message": "Alert sent successfully",
                "data": result
            }
        else:
            return {
                "status": "error",
                "message": result.get("error", "Failed to send alert"),
                "data": None
            }
    
    @staticmethod
    def get_alerts(token: str, unread_only: bool = False, level: Optional[str] = None) -> Dict:
        """
        Get alerts for a user.
        
        Args:
            token: Authentication token
            unread_only: Whether to return only unread alerts
            level: Optional filter by alert level
            
        Returns:
            Response with success status and alerts or error message
        """
        # Validate token
        success, user_data = validate_user_token(token)
        if not success:
            return {
                "status": "error",
                "message": "Invalid or expired token",
                "data": None
            }
        
        # Get alerts
        alerts = get_user_alerts(
            user_id=user_data["id"],
            unread_only=unread_only,
            level=level
        )
        
        return {
            "status": "success",
            "message": f"Retrieved {len(alerts)} alerts",
            "data": {"alerts": alerts}
        }
    
    @staticmethod
    def mark_as_read(token: str, notification_id: str) -> Dict:
        """
        Mark an alert as read.
        
        Args:
            token: Authentication token
            notification_id: The ID of the notification
            
        Returns:
            Response with success status or error message
        """
        # Validate token
        success, user_data = validate_user_token(token)
        if not success:
            return {
                "status": "error",
                "message": "Invalid or expired token",
                "data": None
            }
        
        # Mark as read
        success = mark_alert_as_read(user_data["id"], notification_id)
        
        if success:
            return {
                "status": "success",
                "message": "Alert marked as read",
                "data": None
            }
        else:
            return {
                "status": "error",
                "message": "Alert not found",
                "data": None
            }
    
    @staticmethod
    def mark_all_as_read(token: str) -> Dict:
        """
        Mark all alerts as read.
        
        Args:
            token: Authentication token
            
        Returns:
            Response with success status and count of alerts marked as read
        """
        # Validate token
        success, user_data = validate_user_token(token)
        if not success:
            return {
                "status": "error",
                "message": "Invalid or expired token",
                "data": None
            }
        
        # Mark all as read
        count = mark_all_alerts_as_read(user_data["id"])
        
        return {
            "status": "success",
            "message": f"Marked {count} alerts as read",
            "data": {"count": count}
        }
    
    @staticmethod
    def delete_alert(token: str, notification_id: str) -> Dict:
        """
        Delete an alert.
        
        Args:
            token: Authentication token
            notification_id: The ID of the notification
            
        Returns:
            Response with success status or error message
        """
        # Validate token
        success, user_data = validate_user_token(token)
        if not success:
            return {
                "status": "error",
                "message": "Invalid or expired token",
                "data": None
            }
        
        # Delete alert
        success = delete_user_alert(user_data["id"], notification_id)
        
        if success:
            return {
                "status": "success",
                "message": "Alert deleted successfully",
                "data": None
            }
        else:
            return {
                "status": "error",
                "message": "Alert not found",
                "data": None
            }
    
    @staticmethod
    def send_system_alert(token: str, user_id: str, notification_type: str, 
                         data: Dict, email: Optional[str] = None) -> Dict:
        """
        Send a system notification to a user (admin function).
        
        Args:
            token: Authentication token (must be admin)
            user_id: The ID of the user to notify
            notification_type: The type of notification
            data: Data for the notification template
            email: Optional email address to send the notification to
            
        Returns:
            Response with success status and notification details or error message
        """
        # Validate token (in a real app, would check if user is admin)
        success, admin_data = validate_user_token(token)
        if not success:
            return {
                "status": "error",
                "message": "Invalid or expired token",
                "data": None
            }
        
        # Send system notification
        success, result = send_system_notification(
            user_id=user_id,
            notification_type=notification_type,
            data=data,
            email=email
        )
        
        if success:
            return {
                "status": "success",
                "message": "System notification sent successfully",
                "data": result
            }
        else:
            return {
                "status": "error",
                "message": result.get("error", "Failed to send system notification"),
                "data": None
            }
