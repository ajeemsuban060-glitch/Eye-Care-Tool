from notify.interactive_notifier import InteractiveNotifier

notifier = InteractiveNotifier()
response = notifier.show()
print(f"Response from dialog: {response}")