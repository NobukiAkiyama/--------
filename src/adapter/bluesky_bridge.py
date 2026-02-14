import time
import json
import os
from typing import Dict, Any, List
# try:
#     from atproto import Client, models
# except ImportError:
#     Client = None

class BlueskyBridge:
    """
    Bridge for Bluesky (atproto) notifications.
    Fetches replies and follows, then queues them for the Router.
    """
    def __init__(self, db_manager):
        self.db = db_manager
        self.handle = os.getenv("BLUESKY_HANDLE")
        self.password = os.getenv("BLUESKY_PASSWORD")
        self.client = None
        # if Client and self.handle and self.password:
        #     self.client = Client()
        #     self.client.login(self.handle, self.password)

    def fetch_notifications(self):
        """
        Polls for new notifications and adds them to the event queue.
        """
        if not self.client:
            # print("[Bluesky] Client not initialized. Skipping notification check.")
            return

        try:
            # Example logic for atproto
            # response = self.client.app.bsky.notification.list_notifications()
            # for notification in response.notifications:
            #     if not notification.is_read:
            #         self._process_notification(notification)
            pass
        except Exception as e:
            print(f"[Bluesky] Error fetching notifications: {e}")

    def _process_notification(self, notification):
        """
        Translates a Bluesky notification into a pending_event.
        """
        source_type = "dm" # Simplified for now
        if notification.reason == "reply":
            source_type = "mention"
        elif notification.reason == "follow":
            source_type = "follow"
            
        payload = {
            "platform": "bluesky",
            "at_uri": notification.uri,
            "cid": notification.cid,
            "username": notification.author.handle,
            "display_name": notification.author.display_name,
            "content": getattr(notification.record, 'text', ''),
        }
        
        self.db.add_pending_event(source_type, payload, priority=2 if source_type != "follow" else 1)
        # Mark as read in a real implementation
        # self.client.app.bsky.notification.update_seen({"seen_at": ...})

    def run_poll_loop(self, interval: int = 60):
        print("[Bluesky] Starting notification poll loop...")
        while True:
            self.fetch_notifications()
            # Also check outbox for pending posts
            self.process_outbox()
            time.sleep(interval)

    def process_outbox(self):
        """
        Checks for outgoing posts in the message_outbox.
        """
        messages = self.db.get_pending_outbox("bluesky")
        for msg in messages:
            try:
                print(f"[Bluesky] Sending {msg['message_type']}: {msg['content']}")
                # if msg['message_type'] == 'post':
                #     self.client.send_post(msg['content'])
                self.db.mark_outbox_sent(msg['id'])
            except Exception as e:
                print(f"[Bluesky] Failed to send to Bluesky: {e}")

if __name__ == "__main__":
    from src.core.database import DatabaseManager
    from dotenv import load_dotenv
    load_dotenv()
    
    db = DatabaseManager()
    bridge = BlueskyBridge(db)
    bridge.run_poll_loop()
