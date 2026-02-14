"""
Notification system for sending alerts via webhooks.
"""
import requests
from datetime import datetime
from typing import Dict, Optional
from config import Config


class Notifier:
    """Handles webhook notifications for change detection alerts."""
    
    def __init__(self, webhook_url: str = None):
        """
        Initialize notifier.
        
        Args:
            webhook_url: Slack or Discord webhook URL
        """
        self.webhook_url = webhook_url or Config.WEBHOOK_URL
        self.is_slack = 'slack.com' in self.webhook_url if self.webhook_url else False
        self.is_discord = 'discord.com' in self.webhook_url if self.webhook_url else False
    
    def send_change_alert(self, 
                         aoi_name: str,
                         analysis_results: Dict,
                         aoi_id: int) -> bool:
        """
        Send alert when changes are detected.
        
        Args:
            aoi_name: Name of the AOI
            analysis_results: Change detection results dict
            aoi_id: Database ID of the AOI
            
        Returns:
            True if notification sent successfully
        """
        if not self.webhook_url:
            print("Warning: No webhook URL configured, skipping notification")
            return False
        
        # Build message based on platform
        if self.is_slack:
            payload = self._build_slack_message(aoi_name, analysis_results, aoi_id)
        elif self.is_discord:
            payload = self._build_discord_message(aoi_name, analysis_results, aoi_id)
        else:
            # Generic webhook format
            payload = self._build_generic_message(aoi_name, analysis_results, aoi_id)
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            print(f"Notification sent for AOI: {aoi_name}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Failed to send notification: {e}")
            return False
    
    def _build_slack_message(self, aoi_name: str, results: Dict, aoi_id: int) -> Dict:
        """Build Slack-formatted message."""
        new_date = results.get('new_date_actual', datetime.utcnow())
        change_area = results.get('change_area_sqkm', 0)
        change_pct = results.get('change_percentage', 0)
        avg_change = results.get('avg_change_db', 0)
        
        # Format date
        date_str = new_date.strftime('%Y-%m-%d %H:%M UTC') if isinstance(new_date, datetime) else str(new_date)
        
        # Build rich message with blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Change Detected: {aoi_name}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Image Date:*\n{date_str}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Changed Area:*\n{change_area:.4f} km²"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Change %:*\n{change_pct:.2f}%"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Magnitude:*\n{avg_change:.2f} dB"
                    }
                ]
            }
        ]
        
        # Add image if available
        if results.get('change_map_url'):
            blocks.append({
                "type": "image",
                "image_url": results['change_map_url'],
                "alt_text": f"Change detection map for {aoi_name}"
            })
        
        # Add context
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"View details at {Config.BASE_URL}/results/{aoi_id}"
                }
            ]
        })
        
        return {"blocks": blocks}
    
    def _build_discord_message(self, aoi_name: str, results: Dict, aoi_id: int) -> Dict:
        """Build Discord-formatted message."""
        new_date = results.get('new_date_actual', datetime.utcnow())
        change_area = results.get('change_area_sqkm', 0)
        change_pct = results.get('change_percentage', 0)
        avg_change = results.get('avg_change_db', 0)
        
        date_str = new_date.strftime('%Y-%m-%d %H:%M UTC') if isinstance(new_date, datetime) else str(new_date)
        
        # Discord uses embeds
        embed = {
            "title": f"Change Detected: {aoi_name}",
            "color": 16744192,  # Orange color
            "fields": [
                {
                    "name": "Image Date",
                    "value": date_str,
                    "inline": True
                },
                {
                    "name": "Changed Area",
                    "value": f"{change_area:.4f} km²",
                    "inline": True
                },
                {
                    "name": "Change Percentage",
                    "value": f"{change_pct:.2f}%",
                    "inline": True
                },
                {
                    "name": "Magnitude",
                    "value": f"{avg_change:.2f} dB",
                    "inline": True
                }
            ],
            "footer": {
                "text": f"View details at {Config.BASE_URL}/results/{aoi_id}"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add image if available
        if results.get('change_map_url'):
            embed["image"] = {"url": results['change_map_url']}
        
        return {"embeds": [embed]}
    
    def _build_generic_message(self, aoi_name: str, results: Dict, aoi_id: int) -> Dict:
        """Build generic webhook message."""
        new_date = results.get('new_date_actual', datetime.utcnow())
        date_str = new_date.strftime('%Y-%m-%d %H:%M UTC') if isinstance(new_date, datetime) else str(new_date)
        
        return {
            "aoi_name": aoi_name,
            "aoi_id": aoi_id,
            "image_date": date_str,
            "changes_detected": True,
            "change_area_sqkm": results.get('change_area_sqkm', 0),
            "change_percentage": results.get('change_percentage', 0),
            "avg_change_db": results.get('avg_change_db', 0),
            "change_map_url": results.get('change_map_url', ''),
            "details_url": f"{Config.BASE_URL}/results/{aoi_id}"
        }
    
    def test_connection(self) -> bool:
        """
        Test webhook connection with a simple message.
        
        Returns:
            True if test successful
        """
        if not self.webhook_url:
            print("No webhook URL configured")
            return False
        
        test_payload = {
            "text": "Sentinel-1 Monitor Test - Connection Successful!"
        } if self.is_slack else {
            "content": "Sentinel-1 Monitor Test - Connection Successful!"
        }
        
        try:
            response = requests.post(self.webhook_url, json=test_payload, timeout=10)
            response.raise_for_status()
            print("Webhook test successful")
            return True
        except requests.exceptions.RequestException as e:
            print(f"✗ Webhook test failed: {e}")
            return False
