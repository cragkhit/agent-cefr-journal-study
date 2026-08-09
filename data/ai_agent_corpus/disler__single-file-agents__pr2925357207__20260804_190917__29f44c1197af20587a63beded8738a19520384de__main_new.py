#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
# ]
# ///

"""
Main application entry point for the Atomic/Composable Architecture example.
"""

from endpoints.user_api import UserAPI
from endpoints.alerts_api import AlertsAPI

def display_header(text):
    """Display a header with the given text."""
    print("\n" + "=" * 50)
    print(f" {text}")
    print("=" * 50)

def display_response(response):
    """Display an API response."""
    status = response["status"]
    message = response["message"]
    data = response["data"]
    
    if status == "success":
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")
    
    if data:
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "user":
                    print("\nUser:")
                    for user_key, user_value in value.items():
                        print(f"  {user_key}: {user_value}")
                elif key == "alerts":
                    print("\nAlerts:")
                    for i, alert in enumerate(value):
                        print(f"\nAlert {i+1}:")
                        print(f"  Message: {alert['message']}")
                        print(f"  Type: {alert['type']}")
                        print(f"  Level: {alert['data'].get('level', 'N/A')}")
                        print(f"  Read: {'Yes' if alert['is_read'] else 'No'}")
                else:
                    print(f"\n{key.capitalize()}:")
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            print(f"  {sub_key}: {sub_value}")
                    else:
                        print(f"  {value}")

def main():
    """Run the application."""
    display_header("Atomic/Composable Architecture Example")
    
    # Register users
    display_header("Registering Users")
    
    register_response = UserAPI.register(
        username="johndoe",
        password="Password123!",
        email="john@example.com"
    )
    display_response(register_response)
    
    register_response2 = UserAPI.register(
        username="janedoe",
        password="Secure456@",
        email="jane@example.com"
    )
    display_response(register_response2)
    
    # Try to register with invalid data
    invalid_register = UserAPI.register(
        username="user",
        password="weak",
        email="invalid-email"
    )
    display_response(invalid_register)
    
    # Login
    display_header("User Login")
    
    login_response = UserAPI.login(
        username="johndoe",
        password="Password123!"
    )
    display_response(login_response)
    
    # Store token for later use
    if login_response["status"] == "success" and login_response["data"]:
        token = login_response["data"]["token"]
        
        # Get user profile
        display_header("User Profile")
        
        profile_response = UserAPI.get_profile(token)
        display_response(profile_response)
        
        # Update profile
        display_header("Updating Profile")
        
        update_response = UserAPI.update_profile(
            token=token,
            profile_data={"name": "John Doe", "location": "New York"}
        )
        display_response(update_response)
        
        # Send alerts
        display_header("Sending Alerts")
        
        info_alert = AlertsAPI.send_alert(
            token=token,
            message="This is an informational alert",
            level="info"
        )
        display_response(info_alert)
        
        warning_alert = AlertsAPI.send_alert(
            token=token,
            message="This is a warning alert",
            level="warning",
            email="john@example.com"
        )
        display_response(warning_alert)
        
        error_alert = AlertsAPI.send_alert(
            token=token,
            message="This is an error alert",
            level="error",
            additional_data={"error_code": "E123", "source": "system"}
        )
        display_response(error_alert)
        
        # Get alerts
        display_header("Getting Alerts")
        
        alerts_response = AlertsAPI.get_alerts(token)
        display_response(alerts_response)
        
        # Filter alerts by level
        display_header("Filtering Alerts by Level")
        
        warning_alerts = AlertsAPI.get_alerts(token, level="warning")
        display_response(warning_alerts)
        
        # Mark an alert as read
        if alerts_response["status"] == "success" and alerts_response["data"]:
            alerts = alerts_response["data"]["alerts"]
            if alerts:
                alert_id = alerts[0]["id"]
                
                display_header("Marking Alert as Read")
                
                mark_response = AlertsAPI.mark_as_read(token, alert_id)
                display_response(mark_response)
                
                # Get unread alerts
                display_header("Getting Unread Alerts")
                
                unread_response = AlertsAPI.get_alerts(token, unread_only=True)
                display_response(unread_response)
                
                # Mark all as read
                display_header("Marking All Alerts as Read")
                
                mark_all_response = AlertsAPI.mark_all_as_read(token)
                display_response(mark_all_response)
                
                # Delete an alert
                display_header("Deleting an Alert")
                
                delete_response = AlertsAPI.delete_alert(token, alert_id)
                display_response(delete_response)
        
        # Send system notification
        display_header("Sending System Notification")
        
        system_response = AlertsAPI.send_system_alert(
            token=token,
            user_id=profile_response["data"]["user"]["id"],
            notification_type="welcome",
            data={"username": "johndoe"},
            email="john@example.com"
        )
        display_response(system_response)
        
        # Logout
        display_header("User Logout")
        
        logout_response = UserAPI.logout(token)
        display_response(logout_response)
        
        # Try to use expired token
        display_header("Using Expired Token")
        
        expired_response = UserAPI.get_profile(token)
        display_response(expired_response)

if __name__ == "__main__":
    main()
