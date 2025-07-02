from datetime import datetime

now = datetime.now()
print("Raw datetime:", now)
print("Formatted:", now.strftime('%Y-%m-%d %H:%M:%S'))
