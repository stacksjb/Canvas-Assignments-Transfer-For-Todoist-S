from notifypy import Notify

class NotificationHelper:

    @staticmethod
    def send_notification(title, message):
        notification = Notify()

        notification.title = title
        notification.message = message
        notification.send()
